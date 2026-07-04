from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from tinker_workbench.planner import build_plan


def run_mock_experiment(config: dict[str, Any]) -> Path:
    run_id = datetime.now(tz=UTC).strftime("%Y%m%dT%H%M%SZ")
    run_dir = Path("runs") / run_id
    run_dir.mkdir(parents=True, exist_ok=False)

    plan = build_plan(config)
    _write_json(run_dir / "config.json", config)
    _write_json(run_dir / "plan.json", plan)

    methods = plan["methods"] or ["mock_method"]
    events = []
    metrics = []
    checkpoints = []
    for step in range(0, 5):
        events.append(
            {
                "step": step,
                "type": "mock.progress",
                "message": f"completed mock step {step}",
                "timestamp": _now(),
            }
        )
        for method_index, method in enumerate(methods):
            bits_recovered = min(
                int(config.get("study", {}).get("latent_bits", 10)),
                step * (method_index + 1) + method_index,
            )
            metrics.append(
                {
                    "step": step,
                    "method": method,
                    "exact_match": bits_recovered >= config.get("study", {}).get("latent_bits", 10),
                    "bits_recovered": bits_recovered,
                }
            )
        if step in {0, 2, 4}:
            checkpoints.append(
                {
                    "step": step,
                    "path": f"mock://{run_id}/checkpoint-{step}",
                    "sampler_ready": step > 0,
                    "adapter_applied": step > 0,
                }
            )

    _write_jsonl(run_dir / "events.jsonl", events)
    _write_jsonl(run_dir / "metrics.jsonl", metrics)
    _write_jsonl(run_dir / "checkpoints.jsonl", checkpoints)
    return run_dir


def _now() -> str:
    return datetime.now(tz=UTC).isoformat()


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row) + "\n")

