from __future__ import annotations

import json

from tests.conftest import make_config
from tinker_workbench.config import BudgetConfig, MockConfig
from tinker_workbench.runner import execute_run
from tinker_workbench.store import RunStore


def test_completed_run_writes_all_artifacts(workdir) -> None:
    run_dir = execute_run(make_config())

    for name in ("config.json", "plan.json", "summary.json", "events.jsonl",
                 "metrics.jsonl", "checkpoints.jsonl", "evals.jsonl"):
        assert (run_dir / name).exists(), f"missing artifact: {name}"

    summary = json.loads((run_dir / "summary.json").read_text())
    assert summary["status"] == "completed"
    assert summary["steps_completed"] == 12
    assert summary["checkpoints_saved"] == 3
    assert summary["total_train_tokens"] == 12 * 4 * 32
    assert summary["total_sample_tokens"] > 0


def test_run_registered_and_latest_updated(workdir) -> None:
    run_dir = execute_run(make_config())
    store = RunStore()
    assert store.resolve("latest") == run_dir.resolve()
    runs = store.list_runs()
    assert len(runs) == 1
    assert runs[0]["status"] == "completed"


def test_evals_improve_over_training(workdir) -> None:
    run_dir = execute_run(make_config())
    store = RunStore()
    rows = [row for row in store.load(run_dir).evals if row["name"] == "bits_recovered"]
    assert len(rows) == 3
    assert rows[-1]["score"] > rows[0]["score"]
    assert rows[-1]["score"] > 0.9


def test_nan_loss_fails_run(workdir) -> None:
    config = make_config(mock=MockConfig(inject={"nan_at_step": 6}))
    run_dir = execute_run(config)
    summary = json.loads((run_dir / "summary.json").read_text())
    assert summary["status"] == "failed"
    assert "non-finite" in summary["failure_reason"]
    assert summary["steps_completed"] == 7  # steps 0..6 recorded, stop after the NaN

    events = [json.loads(line) for line in (run_dir / "events.jsonl").read_text().splitlines()]
    assert any(event["type"] == "run.failed" for event in events)
    assert not any(event["type"] == "run.completed" for event in events)


def test_budget_stop(workdir) -> None:
    # 4 examples/batch * 32 tokens = 128 tokens/step; cap at 300 => stop at step 2.
    config = make_config(budget=BudgetConfig(max_train_tokens=300))
    run_dir = execute_run(config)
    summary = json.loads((run_dir / "summary.json").read_text())
    assert summary["status"] == "stopped_budget"
    assert summary["steps_completed"] == 3
    assert summary["total_train_tokens"] >= 300


def test_identical_configs_reproduce_metrics(workdir) -> None:
    config = make_config()
    first = execute_run(config)
    second = execute_run(config)

    def losses(run_dir):
        return [
            json.loads(line)["loss"]
            for line in (run_dir / "metrics.jsonl").read_text().splitlines()
        ]

    assert losses(first) == losses(second)
