from __future__ import annotations

from pathlib import Path

from tinker_workbench.config import load_config
from tinker_workbench.planner import build_plan


def test_plan_includes_budget() -> None:
    config = load_config(Path("configs/memorization_mock.yaml"))
    plan = build_plan(config)

    assert plan["name"] == "memorization-mock"
    assert plan["study_type"] == "memorization"
    assert plan["budget"]["total_tokens"] == 300000
    assert "rl_terminal_reward" in plan["methods"]

