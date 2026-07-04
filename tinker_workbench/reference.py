from __future__ import annotations

import hashlib
import json
import math
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from tinker_workbench.errors import WorkbenchError
from tinker_workbench.store import RunArtifacts, read_json, write_json

DEFAULT_BASELINE_DIR = Path("baselines")

# Drift tolerances. Chosen to ignore seed-level noise on the mock backend and
# sampling noise on small eval sets, while catching the failure classes that
# actually hit the Tinker cookbook: model/renderer changes shifting loss
# curves, eval regressions after SDK updates, and silent cost inflation.
DEFAULT_TOLERANCES = {
    "final_loss_rel": 0.15,       # |final - ref| / ref
    "curve_area_rel": 0.20,       # mean |loss_i - ref_i| / mean(ref)
    "eval_score_abs": 0.10,       # absolute drop in any eval's best score
    "train_tokens_rel": 0.05,     # token usage change (cost proxy)
}


@dataclass(frozen=True)
class DriftFinding:
    severity: str  # critical | warning | info
    code: str
    message: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def build_baseline(artifacts: RunArtifacts, name: str | None = None) -> dict[str, Any]:
    """Distill a run into the reference record future runs are judged against."""
    config = artifacts.config
    summary = artifacts.summary
    if config is None or summary is None:
        raise WorkbenchError(
            f"Run {artifacts.run_dir} is missing config.json or summary.json; "
            "only completed runs can become baselines."
        )
    if summary.get("status") != "completed":
        raise WorkbenchError(
            f"Run {artifacts.run_dir} has status {summary.get('status')!r}; "
            "baselines must come from completed runs."
        )
    losses = [float(row["loss"]) for row in artifacts.metrics]
    best_evals: dict[str, float] = {}
    for row in artifacts.evals:
        current = best_evals.get(row["name"])
        if current is None or row["score"] > current:
            best_evals[row["name"]] = row["score"]

    return {
        "name": name or config["name"],
        "created_at": datetime.now(tz=UTC).isoformat(),
        "source_run": summary.get("run_id"),
        "backend": summary.get("backend"),
        "base_model": summary.get("base_model"),
        "method": summary.get("method"),
        "config_fingerprint": config_fingerprint(config),
        "loss_curve": losses,
        "final_loss": summary.get("final_loss"),
        "best_evals": best_evals,
        "total_train_tokens": summary.get("total_train_tokens"),
        "total_sample_tokens": summary.get("total_sample_tokens"),
        "checkpoints_saved": summary.get("checkpoints_saved"),
    }


def save_baseline(
    artifacts: RunArtifacts,
    name: str | None = None,
    baseline_dir: Path = DEFAULT_BASELINE_DIR,
) -> Path:
    baseline = build_baseline(artifacts, name)
    baseline_dir.mkdir(parents=True, exist_ok=True)
    path = baseline_dir / f"{baseline['name']}.json"
    write_json(path, baseline)
    return path


def load_baseline(ref: str | Path, baseline_dir: Path = DEFAULT_BASELINE_DIR) -> dict[str, Any]:
    for candidate in (Path(ref), baseline_dir / f"{ref}.json", baseline_dir / str(ref)):
        if candidate.is_file():
            return read_json(candidate)
    raise WorkbenchError(
        f"Cannot find baseline {str(ref)!r}. Expected a path or a name under {baseline_dir}/."
    )


def detect_drift(
    artifacts: RunArtifacts,
    baseline: dict[str, Any],
    tolerances: dict[str, float] | None = None,
) -> list[DriftFinding]:
    """Compare a run against a baseline and report meaningful regressions.

    This is the recipe-CI primitive: pin a blessed run as the baseline, re-run
    the config on a schedule (new SDK, new model snapshot, new renderer), and
    let drift findings — not users filing issues — be how breakage surfaces.
    """
    tol = {**DEFAULT_TOLERANCES, **(tolerances or {})}
    findings: list[DriftFinding] = []
    summary = artifacts.summary or {}
    config = artifacts.config or {}

    if config and baseline.get("config_fingerprint") != config_fingerprint(config):
        findings.append(
            DriftFinding(
                "info",
                "config_changed",
                "Run config differs from the baseline config; loss/eval comparisons below "
                "reflect an intentional change, not silent drift.",
            )
        )
    if summary.get("base_model") != baseline.get("base_model"):
        findings.append(
            DriftFinding(
                "warning",
                "base_model_changed",
                f"Base model changed: baseline {baseline.get('base_model')!r} vs "
                f"run {summary.get('base_model')!r} (deprecation/migration?).",
            )
        )
    if summary.get("status") != "completed":
        findings.append(
            DriftFinding(
                "critical",
                "run_not_completed",
                f"Run status is {summary.get('status')!r} but the baseline run completed.",
            )
        )

    findings.extend(_loss_drift(artifacts, baseline, tol))
    findings.extend(_eval_drift(artifacts, baseline, tol))
    findings.extend(_usage_drift(summary, baseline, tol))

    order = {"critical": 0, "warning": 1, "info": 2}
    findings.sort(key=lambda f: order.get(f.severity, 9))
    return findings


def config_fingerprint(config: dict[str, Any]) -> str:
    canonical = json.dumps(config, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]


def _loss_drift(
    artifacts: RunArtifacts, baseline: dict[str, Any], tol: dict[str, float]
) -> list[DriftFinding]:
    ref_curve = [float(v) for v in baseline.get("loss_curve", [])]
    run_curve = [float(row["loss"]) for row in artifacts.metrics]
    if not ref_curve or not run_curve:
        return []
    findings = []

    if any(not math.isfinite(v) for v in run_curve):
        findings.append(
            DriftFinding(
                "critical",
                "loss_non_finite",
                "Run produced non-finite losses; the baseline run did not.",
            )
        )
        return findings

    ref_final = ref_curve[-1]
    run_final = run_curve[-1]
    if ref_final > 0:
        rel = (run_final - ref_final) / ref_final
        if rel > tol["final_loss_rel"]:
            findings.append(
                DriftFinding(
                    "critical",
                    "final_loss_regression",
                    f"Final loss regressed {rel * 100:.1f}% vs baseline "
                    f"({run_final:.4f} vs {ref_final:.4f}, tolerance "
                    f"{tol['final_loss_rel'] * 100:.0f}%).",
                )
            )
        elif rel < -tol["final_loss_rel"]:
            findings.append(
                DriftFinding(
                    "info",
                    "final_loss_improved",
                    f"Final loss improved {-rel * 100:.1f}% vs baseline "
                    f"({run_final:.4f} vs {ref_final:.4f}); consider re-pinning the baseline.",
                )
            )

    overlap = min(len(ref_curve), len(run_curve))
    ref_mean = sum(ref_curve[:overlap]) / overlap
    if ref_mean > 0:
        area = (
            sum(abs(run_curve[i] - ref_curve[i]) for i in range(overlap)) / overlap / ref_mean
        )
        if area > tol["curve_area_rel"]:
            findings.append(
                DriftFinding(
                    "warning",
                    "loss_curve_shape_drift",
                    f"Loss curve deviates {area * 100:.1f}% from the baseline on average "
                    f"(tolerance {tol['curve_area_rel'] * 100:.0f}%): training dynamics "
                    "changed even if the endpoint is similar.",
                )
            )
    if len(ref_curve) != len(run_curve):
        findings.append(
            DriftFinding(
                "warning",
                "step_count_changed",
                f"Run recorded {len(run_curve)} steps vs baseline {len(ref_curve)}.",
            )
        )
    return findings


def _eval_drift(
    artifacts: RunArtifacts, baseline: dict[str, Any], tol: dict[str, float]
) -> list[DriftFinding]:
    ref_evals: dict[str, float] = baseline.get("best_evals", {})
    run_evals: dict[str, float] = {}
    for row in artifacts.evals:
        current = run_evals.get(row["name"])
        if current is None or row["score"] > current:
            run_evals[row["name"]] = row["score"]

    findings = []
    for name, ref_score in ref_evals.items():
        if name not in run_evals:
            findings.append(
                DriftFinding(
                    "warning",
                    "eval_missing",
                    f"Eval {name!r} present in the baseline was not run.",
                )
            )
            continue
        delta = run_evals[name] - ref_score
        if delta < -tol["eval_score_abs"]:
            findings.append(
                DriftFinding(
                    "critical",
                    "eval_regression",
                    f"Eval {name!r} dropped {-delta:.3f} vs baseline "
                    f"({run_evals[name]:.4f} vs {ref_score:.4f}, tolerance "
                    f"{tol['eval_score_abs']:.2f}).",
                )
            )
    return findings


def _usage_drift(
    summary: dict[str, Any], baseline: dict[str, Any], tol: dict[str, float]
) -> list[DriftFinding]:
    ref_tokens = baseline.get("total_train_tokens")
    run_tokens = summary.get("total_train_tokens")
    if not ref_tokens or not run_tokens:
        return []
    rel = (run_tokens - ref_tokens) / ref_tokens
    if rel > tol["train_tokens_rel"]:
        return [
            DriftFinding(
                "warning",
                "token_usage_increase",
                f"Train token usage grew {rel * 100:.1f}% vs baseline "
                f"({run_tokens} vs {ref_tokens}): cost drift.",
            )
        ]
    return []
