from __future__ import annotations

from tests.conftest import make_config
from tinker_workbench.config import BudgetConfig, TrainingConfig
from tinker_workbench.planner import build_plan


def test_token_math() -> None:
    config = make_config()
    plan = build_plan(config)
    # 12 steps * 4 batch * 32 tokens
    assert plan["budget"]["planned_train_tokens"] == 12 * 4 * 32
    # 3 checkpoints * 2 evals * 8 examples * 16 tokens
    assert plan["budget"]["planned_sample_tokens"] == 3 * 2 * 8 * 16
    assert plan["budget"]["checkpoints"] == 3


def test_cost_estimate_requires_rates() -> None:
    config = make_config()
    assert build_plan(config)["budget"]["estimated_usd"] is None

    config = make_config(
        budget=BudgetConfig(usd_per_1m_train_tokens=10.0, usd_per_1m_sample_tokens=2.0)
    )
    plan = build_plan(config)
    train_tokens = plan["budget"]["planned_train_tokens"]
    sample_tokens = plan["budget"]["planned_sample_tokens"]
    expected = round(train_tokens / 1e6 * 10.0 + sample_tokens / 1e6 * 2.0, 4)
    assert plan["budget"]["estimated_usd"] == expected


def test_budget_overrun_risk_flagged() -> None:
    config = make_config(budget=BudgetConfig(max_train_tokens=100))
    plan = build_plan(config)
    assert any("exceed budget.max_train_tokens" in risk for risk in plan["risks"])


def test_max_usd_risk_flagged() -> None:
    config = make_config(
        budget=BudgetConfig(usd_per_1m_train_tokens=1_000_000.0, max_usd=0.01)
    )
    plan = build_plan(config)
    assert any("max_usd" in risk for risk in plan["risks"])


def test_high_lr_risk_flagged() -> None:
    config = make_config(training=TrainingConfig(steps=12, learning_rate=0.01))
    plan = build_plan(config)
    assert any("unusually high" in risk for risk in plan["risks"])


def test_no_evals_risk_flagged() -> None:
    config = make_config(evals=[])
    plan = build_plan(config)
    assert any("No evals" in risk for risk in plan["risks"])
