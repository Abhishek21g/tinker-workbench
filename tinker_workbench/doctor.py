from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from typing import Any

from tinker_workbench.store import RunArtifacts

SEVERITY_ORDER = {"critical": 0, "warning": 1, "info": 2}


@dataclass(frozen=True)
class Finding:
    severity: str  # critical | warning | info
    code: str
    message: str
    suggestion: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def diagnose(artifacts: RunArtifacts) -> list[Finding]:
    """Inspect a run's artifacts for the failure modes that burn time and money.

    Pure post-hoc analysis: reads artifacts only, never re-runs anything, so
    it is safe on live, interrupted, and failed runs alike.
    """
    findings: list[Finding] = []
    findings.extend(_check_run_state(artifacts))
    losses = [
        (row["step"], float(row["loss"]))
        for row in artifacts.metrics
        if "loss" in row
    ]
    findings.extend(_check_loss_curve(losses))
    findings.extend(_check_checkpoints(artifacts, losses))
    findings.extend(_check_budget(artifacts))
    findings.extend(_check_evals(artifacts))
    findings.sort(key=lambda f: SEVERITY_ORDER.get(f.severity, 9))
    return findings


def _check_run_state(artifacts: RunArtifacts) -> list[Finding]:
    summary = artifacts.summary
    if summary is None:
        return [
            Finding(
                "warning",
                "run_incomplete",
                "No summary.json found; the run was interrupted before finishing.",
                "Inspect events.jsonl for the last recorded event, then re-run or resume.",
            )
        ]
    findings = []
    if summary.get("status") == "failed":
        findings.append(
            Finding(
                "critical",
                "run_failed",
                f"Run failed: {summary.get('failure_reason', 'unknown reason')}.",
                "See the loss diagnostics below for the likely cause.",
            )
        )
    if summary.get("status") == "stopped_budget":
        findings.append(
            Finding(
                "warning",
                "budget_stop",
                f"Run stopped early on budget: {summary.get('failure_reason')}.",
                "Raise budget.max_train_tokens or reduce steps/batch size to fit the budget.",
            )
        )
    return findings


def _check_loss_curve(losses: list[tuple[int, float]]) -> list[Finding]:
    if not losses:
        return [
            Finding(
                "warning",
                "no_metrics",
                "No training metrics were recorded.",
                "Confirm the run started; check events.jsonl for a run.start event.",
            )
        ]
    findings = []

    non_finite = [step for step, loss in losses if not math.isfinite(loss)]
    if non_finite:
        findings.append(
            Finding(
                "critical",
                "non_finite_loss",
                f"Loss became NaN/inf at step {non_finite[0]}.",
                "Lower training.learning_rate (try 10x smaller) and check the dataset for "
                "malformed examples; resume from the last finite checkpoint.",
            )
        )

    finite = [(step, loss) for step, loss in losses if math.isfinite(loss)]
    if len(finite) < 6:
        return findings
    values = [loss for _, loss in finite]
    best = min(values)
    first_window = sum(values[:3]) / 3
    last_window = sum(values[-3:]) / 3
    prev_window = sum(values[-6:-3]) / 3

    # Diverging = the tail sits well above the best loss AND is still rising.
    if last_window > max(2.0 * best, best + 0.1) and last_window > prev_window * 1.05:
        step_at_best = min(finite, key=lambda pair: pair[1])[0]
        findings.append(
            Finding(
                "critical",
                "loss_divergence",
                f"Loss is diverging: best {best:.4f} around step {step_at_best}, "
                f"but the final window averages {last_window:.4f}.",
                "Lower training.learning_rate or switch lr_schedule to cosine/linear decay, "
                f"and restart (or resume) from the checkpoint nearest step {step_at_best}.",
            )
        )
    else:
        total_improvement = (first_window - last_window) / max(abs(first_window), 1e-9)
        if total_improvement < 0.15:
            findings.append(
                Finding(
                    "warning",
                    "insufficient_progress",
                    f"Loss only improved {total_improvement * 100:.1f}% over the run "
                    f"({first_window:.4f} -> {last_window:.4f}).",
                    "Training may be stalled: try a higher learning rate, more steps, or "
                    "verify the dataset actually contains learnable signal.",
                )
            )
        else:
            half = len(values) // 2
            second_half_improvement = (
                (sum(values[half : half + 3]) / 3 - last_window)
                / max(abs(sum(values[half : half + 3]) / 3), 1e-9)
            )
            if second_half_improvement < 0.02 and last_window > first_window * 0.5:
                findings.append(
                    Finding(
                        "info",
                        "plateau_second_half",
                        "Loss plateaued in the second half of training.",
                        "Later steps may be wasted budget; consider fewer steps or an LR decay "
                        "schedule.",
                    )
                )

    spikes = _find_spikes(finite)
    if spikes:
        findings.append(
            Finding(
                "info",
                "loss_spike",
                f"Transient loss spike(s) at step(s) {spikes[:5]}.",
                "Usually a bad batch or LR-instability blip; worth checking the data at those "
                "steps if spikes recur.",
            )
        )
    return findings


def _find_spikes(finite: list[tuple[int, float]]) -> list[int]:
    spikes = []
    for index in range(1, len(finite) - 1):
        step, loss = finite[index]
        neighbors = (finite[index - 1][1] + finite[index + 1][1]) / 2
        if neighbors > 0 and loss > 2.5 * neighbors:
            spikes.append(step)
    return spikes


def _check_checkpoints(
    artifacts: RunArtifacts, losses: list[tuple[int, float]]
) -> list[Finding]:
    if not losses:
        return []
    last_step = losses[-1][0]
    if not artifacts.checkpoints:
        return [
            Finding(
                "warning",
                "no_checkpoints",
                f"No checkpoints were saved across {last_step + 1} steps.",
                "Set checkpoints.every_steps low enough that the run saves at least once; "
                "without checkpoints nothing can be sampled or resumed.",
            )
        ]
    last_checkpoint_step = max(row["step"] for row in artifacts.checkpoints)
    config = artifacts.config or {}
    every = int(config.get("checkpoints", {}).get("every_steps", 10))
    if last_step - last_checkpoint_step >= every:
        return [
            Finding(
                "warning",
                "checkpoint_gap",
                f"Last checkpoint is at step {last_checkpoint_step} but training reached "
                f"step {last_step}; the final {last_step - last_checkpoint_step} steps of "
                "progress are unsaved.",
                "Save a final checkpoint (or align training.steps to a multiple of "
                "checkpoints.every_steps).",
            )
        ]
    return []


def _check_budget(artifacts: RunArtifacts) -> list[Finding]:
    plan = artifacts.plan or {}
    summary = artifacts.summary or {}
    planned = plan.get("budget", {}).get("planned_train_tokens")
    actual = summary.get("total_train_tokens")
    if not planned or not actual:
        return []
    if actual > planned * 1.05:
        return [
            Finding(
                "warning",
                "token_overrun",
                f"Actual train tokens ({actual}) exceeded the plan ({planned}) by "
                f"{(actual / planned - 1) * 100:.1f}%.",
                "Re-check data.avg_tokens_per_example against the real dataset so plans "
                "stay trustworthy.",
            )
        ]
    return []


def _check_evals(artifacts: RunArtifacts) -> list[Finding]:
    findings = []
    by_name: dict[str, list[dict[str, Any]]] = {}
    for row in artifacts.evals:
        by_name.setdefault(row["name"], []).append(row)
    for name, rows in by_name.items():
        rows = sorted(rows, key=lambda r: r["step"])
        best = max(rows, key=lambda r: r["score"])
        final = rows[-1]
        if best["step"] != final["step"] and best["score"] - final["score"] > 0.05:
            findings.append(
                Finding(
                    "warning",
                    "eval_regression",
                    f"Eval {name!r} peaked at {best['score']} (step {best['step']}) but "
                    f"ended at {final['score']} (step {final['step']}).",
                    f"Prefer the step-{best['step']} checkpoint over the final one; this "
                    "often accompanies overfitting or LR instability late in training.",
                )
            )
    return findings
