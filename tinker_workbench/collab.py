from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def build_collab_proposal(target: str, run_dir: Path | None = None) -> dict[str, Any]:
    run_snapshot = _load_run_snapshot(run_dir) if run_dir else None
    if target == "tinker-cookbook-cost":
        return _cost_visibility_proposal(run_snapshot)
    if target == "tinker-checkpoint-probe":
        return _checkpoint_probe_proposal(run_snapshot)
    raise ValueError(f"Unknown collaboration target: {target}")


def _cost_visibility_proposal(run_snapshot: dict[str, Any] | None) -> dict[str, Any]:
    return {
        "target": "thinking-machines-lab/tinker-cookbook",
        "issues": [
            "https://github.com/thinking-machines-lab/tinker-cookbook/issues/551",
            "https://github.com/thinking-machines-lab/tinker-cookbook/issues/781",
            "https://github.com/thinking-machines-lab/tinker-cookbook/issues/298",
        ],
        "proposal": {
            "name": "run cost and usage report JSON",
            "goal": "Give local tools a stable shape for pre-run estimates and post-run reconciliation.",
            "why_now": (
                "Tinker users are already asking for cost, usage, balance, and checkpoint storage "
                "visibility. Tinker Workbench can prototype the client-side report shape before "
                "any server-side API exists."
            ),
            "not_duplicate_of": [
                "tinkpad can remain focused on terminal run/checkpoint management",
                "tinker-cost can remain focused on estimating prices from datums",
            ],
            "workbench_role": (
                "Collect estimates, run metadata, checkpoint observations, and eval outputs into "
                "one reproducible experiment report."
            ),
        },
        "suggested_json_shape": {
            "run_id": "string",
            "base_model": "string",
            "training_method": "sft|rl|dpo|distillation|custom",
            "token_usage": {
                "train_tokens": "integer",
                "sample_tokens": "integer",
                "total_tokens": "integer",
            },
            "cost": {
                "estimated_usd": "number|null",
                "actual_usd": "number|null",
                "source": "manual|pricing-table|api|unknown",
            },
            "checkpoint_storage": {
                "checkpoint_count": "integer",
                "estimated_gb": "number",
                "retention_policy": "string|null",
            },
            "evals": [
                {
                    "name": "string",
                    "score": "number|string|boolean",
                    "step": "integer|null",
                }
            ],
            "warnings": ["string"],
        },
        "prototype_snapshot": run_snapshot,
    }


def _checkpoint_probe_proposal(run_snapshot: dict[str, Any] | None) -> dict[str, Any]:
    return {
        "target": "thinking-machines-lab/tinker",
        "issues": [
            "https://github.com/thinking-machines-lab/tinker/issues/44",
            "https://github.com/thinking-machines-lab/tinker/issues/25",
            "https://github.com/thinking-machines-lab/tinker/issues/41",
        ],
        "proposal": {
            "name": "tinker checkpoint probe <path> --json",
            "goal": "Verify that a saved checkpoint can serve through a sampler before using it in evals.",
            "use_cases": [
                "CI smoke tests for training scripts",
                "pre-eval readiness checks",
                "detect base-model vs adapter-backed serving confusion",
                "make checkpoint health visible in generated experiment reports",
            ],
        },
        "suggested_json_shape": {
            "checkpoint_path": "string",
            "sampler_ready": "boolean",
            "adapter_applied": "boolean|null",
            "native_sampling_ok": "boolean",
            "openai_compatible_sampling_ok": "boolean|null",
            "latency_ms": "number|null",
            "error": "string|null",
        },
        "prototype_snapshot": run_snapshot,
    }


def _load_run_snapshot(run_dir: Path) -> dict[str, Any]:
    run_dir = run_dir.resolve()
    plan = _read_json(run_dir / "plan.json")
    checkpoints = _read_jsonl(run_dir / "checkpoints.jsonl")
    metrics = _read_jsonl(run_dir / "metrics.jsonl")
    return {
        "run_dir": str(run_dir),
        "plan": plan,
        "latest_checkpoint": checkpoints[-1] if checkpoints else None,
        "metric_rows": len(metrics),
        "checkpoint_rows": len(checkpoints),
    }


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]

