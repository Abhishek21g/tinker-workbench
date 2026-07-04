from __future__ import annotations

from typing import Any


def build_plan(config: dict[str, Any]) -> dict[str, Any]:
    budget = config.get("budget", {})
    train_tokens = int(budget.get("train_tokens", 0))
    sample_tokens = int(budget.get("sample_tokens", 0))
    checkpoints = int(budget.get("checkpoints", 0))
    checkpoint_gb_each = float(budget.get("checkpoint_gb_each", 0.0))
    total_tokens = train_tokens + sample_tokens
    checkpoint_storage_gb = checkpoints * checkpoint_gb_each

    risks: list[str] = []
    if config.get("mode") != "mock":
        risks.append("Real Tinker API usage requires explicit user approval before launch.")
    if checkpoint_storage_gb > 1.0:
        risks.append("Checkpoint storage is nontrivial; confirm cleanup and retention policy.")
    if total_tokens == 0:
        risks.append("Budget token counts are missing, so cost planning is incomplete.")

    return {
        "name": config["name"],
        "mode": config.get("mode", "mock"),
        "study_type": config.get("study", {}).get("type"),
        "model": config.get("model", {}),
        "methods": config.get("study", {}).get("methods", []),
        "evals": config.get("evals", []),
        "budget": {
            "train_tokens": train_tokens,
            "sample_tokens": sample_tokens,
            "total_tokens": total_tokens,
            "checkpoints": checkpoints,
            "checkpoint_storage_gb": checkpoint_storage_gb,
        },
        "risks": risks,
    }

