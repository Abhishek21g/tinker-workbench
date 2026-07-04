from __future__ import annotations

from pathlib import Path

from tinker_workbench.config import load_config
from tinker_workbench.collab import build_collab_proposal
from tinker_workbench.planner import build_plan


def test_plan_includes_budget() -> None:
    config = load_config(Path("configs/memorization_mock.yaml"))
    plan = build_plan(config)

    assert plan["name"] == "memorization-mock"
    assert plan["study_type"] == "memorization"
    assert plan["budget"]["total_tokens"] == 300000
    assert "rl_terminal_reward" in plan["methods"]


def test_collab_proposal_targets_cost_issues() -> None:
    proposal = build_collab_proposal("tinker-cookbook-cost")

    assert proposal["target"] == "thinking-machines-lab/tinker-cookbook"
    assert any("issues/551" in issue for issue in proposal["issues"])
    assert "suggested_json_shape" in proposal


def test_collab_proposal_targets_checkpoint_probe() -> None:
    proposal = build_collab_proposal("tinker-checkpoint-probe")

    assert proposal["target"] == "thinking-machines-lab/tinker"
    assert any("issues/44" in issue for issue in proposal["issues"])
    assert proposal["suggested_json_shape"]["sampler_ready"] == "boolean"
