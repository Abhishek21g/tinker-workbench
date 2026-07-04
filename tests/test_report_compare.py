from __future__ import annotations

from tests.conftest import make_config
from tinker_workbench.compare import build_comparison
from tinker_workbench.config import MockConfig, TrainingConfig
from tinker_workbench.report import render_report, sparkline, write_report
from tinker_workbench.runner import execute_run
from tinker_workbench.store import RunStore


def test_report_sections_present(workdir) -> None:
    run_dir = execute_run(make_config())
    report = render_report(RunStore().load(run_dir))

    for heading in (
        "# test-run — Experiment Report",
        "## Summary",
        "## Training",
        "## Evals",
        "## Checkpoints",
        "## Budget Reconciliation",
        "## Diagnostics",
        "## Reproduce",
    ):
        assert heading in report
    assert "Status: **completed**" in report
    assert "| step | bits_recovered | exact_match |" in report


def test_report_for_failed_run(workdir) -> None:
    config = make_config(mock=MockConfig(inject={"nan_at_step": 6}))
    run_dir = execute_run(config)
    report = render_report(RunStore().load(run_dir))
    assert "Status: **failed**" in report
    assert "non_finite_loss" in report


def test_write_report_default_location(workdir) -> None:
    run_dir = execute_run(make_config())
    report_path = write_report(RunStore().load(run_dir))
    assert report_path.resolve() == (workdir / "reports" / f"{run_dir.name}.md").resolve()
    assert report_path.exists()


def test_sparkline() -> None:
    assert sparkline([]) == ""
    assert sparkline([1.0, 1.0]) == "▁▁"
    line = sparkline([4.0, 3.0, 2.0, 1.0])
    assert line[0] == "█"
    assert line[-1] == "▁"


def test_compare_runs(workdir) -> None:
    sft_dir = execute_run(make_config())
    rl_dir = execute_run(
        make_config(
            name="test-rl",
            training=TrainingConfig(steps=12, batch_size=4, method="rl_terminal_reward",
                                    seed=11),
        )
    )
    store = RunStore()
    table = build_comparison([store.load(sft_dir), store.load(rl_dir)])

    assert "| run | method | status |" in table.replace("  ", " ")
    assert "sft" in table
    assert "rl_terminal_reward" in table
    assert "## Leaders" in table
    assert "best exact_match" in table
