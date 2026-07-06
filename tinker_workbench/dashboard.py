from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from tinker_workbench.doctor import diagnose
from tinker_workbench.probe import probe_checkpoint
from tinker_workbench.store import RunStore, write_json

MAX_DASHBOARD_RUNS = 8


def build_run_panel(artifacts) -> dict[str, Any]:
    summary = artifacts.summary or {}
    plan = artifacts.plan or {}
    findings = [finding.to_dict() for finding in diagnose(artifacts)]
    losses = [
        {"step": row["step"], "loss": float(row["loss"])}
        for row in artifacts.metrics
        if "loss" in row
    ]
    return {
        "run_id": summary.get("run_id") or artifacts.run_dir.name,
        "run_dir": str(artifacts.run_dir),
        "status": summary.get("status", "in_progress"),
        "failure_reason": summary.get("failure_reason"),
        "backend": summary.get("backend"),
        "method": summary.get("method"),
        "steps_completed": summary.get("steps_completed"),
        "steps_planned": summary.get("steps_planned"),
        "final_loss": summary.get("final_loss"),
        "tokens": {
            "train": summary.get("total_train_tokens"),
            "sample": summary.get("total_sample_tokens"),
        },
        "plan": plan,
        "budget": plan.get("budget", {}),
        "findings": findings,
        "metrics": losses,
        "checkpoints": artifacts.checkpoints,
        "evals": artifacts.evals[-12:],
        "probe": probe_checkpoint(artifacts),
    }


def build_dashboard_payload(
    run_ref: str | Path = "latest",
    runs_root: Path = Path("runs"),
) -> dict[str, Any]:
    store = RunStore(runs_root)
    artifacts = store.load(run_ref)
    runs = []
    for record in reversed(store.list_runs()):
        runs.append(
            {
                "run_id": record.get("run_id"),
                "name": record.get("name"),
                "method": record.get("method"),
                "status": record.get("status"),
                "backend": record.get("backend"),
                "final_loss": record.get("final_loss"),
            }
        )
    run_panels: dict[str, Any] = {}
    for record in runs[:MAX_DASHBOARD_RUNS]:
        run_id = record.get("run_id")
        if not run_id:
            continue
        try:
            run_panels[run_id] = build_run_panel(store.load(run_id))
        except (FileNotFoundError, OSError, KeyError):
            continue
    selected_id = (artifacts.summary or {}).get("run_id") or artifacts.run_dir.name
    panel = run_panels.get(selected_id) or build_run_panel(artifacts)
    try:
        panel["run_dir"] = str(artifacts.run_dir.relative_to(Path.cwd()))
    except ValueError:
        panel["run_dir"] = str(artifacts.run_dir)
    for entry in run_panels.values():
        try:
            entry["run_dir"] = str(Path(entry["run_dir"]).relative_to(Path.cwd()))
        except ValueError:
            pass
    return {
        "generated_at": datetime.now(tz=UTC).isoformat(),
        "runs": runs,
        "selected_run_id": selected_id,
        "selected_run": panel,
        "run_panels": run_panels,
    }


def export_dashboard(
    run_ref: str | Path = "latest",
    runs_root: Path = Path("runs"),
    out: Path = Path("site/data/dashboard.json"),
) -> Path:
    payload = build_dashboard_payload(run_ref=run_ref, runs_root=runs_root)
    out.parent.mkdir(parents=True, exist_ok=True)
    write_json(out, payload)
    return out
