from __future__ import annotations

from typing import Any

from tinker_workbench.config import ExperimentConfig


def build_plan(config: ExperimentConfig) -> dict[str, Any]:
    """Produce the pre-run plan: token/checkpoint/cost estimates plus risks.

    The plan is written into the run directory verbatim so reports can
    reconcile planned vs. actual usage after the fact.
    """
    training = config.training
    data = config.data
    checkpoints = config.checkpoints
    budget = config.budget

    train_tokens = training.steps * training.batch_size * data.avg_tokens_per_example
    checkpoint_count = training.steps // checkpoints.every_steps
    sample_tokens = sum(
        e.num_examples * e.max_sample_tokens * checkpoint_count for e in config.evals
    )
    checkpoint_storage_gb = round(checkpoint_count * checkpoints.estimated_gb_each, 3)

    estimated_usd = _estimate_cost(budget, train_tokens, sample_tokens)

    risks: list[str] = []
    if config.mode == "tinker":
        risks.append("Real Tinker API usage requires explicit user approval before launch.")
    if budget.max_train_tokens and train_tokens > budget.max_train_tokens:
        risks.append(
            f"Planned train tokens ({train_tokens}) exceed budget.max_train_tokens "
            f"({budget.max_train_tokens})."
        )
    if budget.max_sample_tokens and sample_tokens > budget.max_sample_tokens:
        risks.append(
            f"Planned sample tokens ({sample_tokens}) exceed budget.max_sample_tokens "
            f"({budget.max_sample_tokens})."
        )
    if estimated_usd is None and config.mode == "tinker":
        risks.append(
            "No pricing rates provided (budget.usd_per_1m_train_tokens / "
            "usd_per_1m_sample_tokens), so cost cannot be estimated before launch."
        )
    if estimated_usd is not None and budget.max_usd is not None and estimated_usd > budget.max_usd:
        risks.append(
            f"Estimated cost (${estimated_usd:.2f}) exceeds budget.max_usd (${budget.max_usd:.2f})."
        )
    if checkpoint_storage_gb > 5.0:
        risks.append(
            f"Checkpoint storage estimate is {checkpoint_storage_gb} GB; "
            "confirm retention/cleanup policy."
        )
    if not config.evals:
        risks.append("No evals configured; the run will produce loss curves but no task scores.")
    if config.mode == "tinker" and training.learning_rate > 50 * 1e-4:
        risks.append(
            f"learning_rate={training.learning_rate} is unusually high for LoRA "
            "fine-tuning; check for divergence early with `doctor`."
        )

    return {
        "name": config.name,
        "mode": config.mode,
        "method": training.method,
        "model": {
            "base_model": config.model.base_model,
            "lora_rank": config.model.lora_rank,
        },
        "data": {
            "source": data.source,
            "train_examples": data.train_examples,
            "eval_examples": data.eval_examples,
        },
        "schedule": {
            "steps": training.steps,
            "batch_size": training.batch_size,
            "learning_rate": training.learning_rate,
            "lr_schedule": training.lr_schedule,
            "seed": training.seed,
        },
        "evals": [e.name for e in config.evals],
        "budget": {
            "planned_train_tokens": train_tokens,
            "planned_sample_tokens": sample_tokens,
            "planned_total_tokens": train_tokens + sample_tokens,
            "max_train_tokens": budget.max_train_tokens,
            "max_sample_tokens": budget.max_sample_tokens,
            "checkpoints": checkpoint_count,
            "checkpoint_storage_gb": checkpoint_storage_gb,
            "estimated_usd": estimated_usd,
            "max_usd": budget.max_usd,
        },
        "risks": risks,
    }


def _estimate_cost(budget, train_tokens: int, sample_tokens: int) -> float | None:
    """Cost estimate from user-supplied rates.

    Rates are deliberately not hardcoded: Tinker pricing is per-model and
    changes; the config owner supplies current numbers and the planner keeps
    the math honest.
    """
    if budget.usd_per_1m_train_tokens is None and budget.usd_per_1m_sample_tokens is None:
        return None
    total = 0.0
    if budget.usd_per_1m_train_tokens is not None:
        total += train_tokens / 1_000_000 * budget.usd_per_1m_train_tokens
    if budget.usd_per_1m_sample_tokens is not None:
        total += sample_tokens / 1_000_000 * budget.usd_per_1m_sample_tokens
    return round(total, 4)
