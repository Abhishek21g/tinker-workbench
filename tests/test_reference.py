from __future__ import annotations

import pytest

from tests.conftest import make_config
from tinker_workbench.config import MockConfig, TrainingConfig
from tinker_workbench.errors import WorkbenchError
from tinker_workbench.reference import (
    build_baseline,
    detect_drift,
    load_baseline,
    save_baseline,
)
from tinker_workbench.runner import execute_run
from tinker_workbench.store import RunStore


def _codes(findings) -> set[str]:
    return {finding.code for finding in findings}


def _severities(findings) -> set[str]:
    return {finding.severity for finding in findings}


def test_baseline_roundtrip(workdir) -> None:
    run_dir = execute_run(make_config())
    artifacts = RunStore().load(run_dir)
    path = save_baseline(artifacts, name="ref")
    baseline = load_baseline("ref")
    assert path.name == "ref.json"
    assert baseline["final_loss"] == artifacts.summary["final_loss"]
    assert len(baseline["loss_curve"]) == 12
    assert baseline["best_evals"]["bits_recovered"] > 0


def test_baseline_rejects_failed_run(workdir) -> None:
    config = make_config(mock=MockConfig(inject={"nan_at_step": 4}))
    run_dir = execute_run(config)
    with pytest.raises(WorkbenchError, match="status"):
        build_baseline(RunStore().load(run_dir))


def test_identical_rerun_has_no_drift(workdir) -> None:
    config = make_config()
    baseline_run = execute_run(config)
    rerun = execute_run(config)
    store = RunStore()
    baseline = build_baseline(store.load(baseline_run))
    findings = detect_drift(store.load(rerun), baseline)
    assert "critical" not in _severities(findings)
    assert "final_loss_regression" not in _codes(findings)
    assert "config_changed" not in _codes(findings)


def test_detects_final_loss_regression(workdir) -> None:
    good = make_config()
    baseline_run = execute_run(good)
    # Same recipe re-run after "something changed": training now stalls early.
    bad = make_config(mock=MockConfig(time_constant=4.0, inject={"stall_at_step": 2}))
    bad_run = execute_run(bad)

    store = RunStore()
    baseline = build_baseline(store.load(baseline_run))
    findings = detect_drift(store.load(bad_run), baseline)
    codes = _codes(findings)
    assert "final_loss_regression" in codes
    assert "config_changed" in codes  # the injection changed the config fingerprint
    assert any(finding.severity == "critical" for finding in findings)


def test_detects_eval_regression_and_nan(workdir) -> None:
    baseline_run = execute_run(make_config())
    bad = make_config(mock=MockConfig(inject={"nan_at_step": 6}))
    bad_run = execute_run(bad)

    store = RunStore()
    baseline = build_baseline(store.load(baseline_run))
    findings = detect_drift(store.load(bad_run), baseline)
    codes = _codes(findings)
    assert "run_not_completed" in codes
    assert "loss_non_finite" in codes


def test_detects_base_model_and_step_changes(workdir) -> None:
    baseline_run = execute_run(make_config())
    changed = make_config(
        training=TrainingConfig(steps=8, batch_size=4, seed=11),
    )
    changed.model.base_model = "meta-llama/Llama-3.1-8B"
    changed_run = execute_run(changed)

    store = RunStore()
    baseline = build_baseline(store.load(baseline_run))
    findings = detect_drift(store.load(changed_run), baseline)
    codes = _codes(findings)
    assert "base_model_changed" in codes
    assert "step_count_changed" in codes


def test_improvement_suggests_repin(workdir) -> None:
    slow = make_config(mock=MockConfig(time_constant=40.0))
    baseline_run = execute_run(slow)
    fast = make_config(mock=MockConfig(time_constant=3.0))
    fast_run = execute_run(fast)

    store = RunStore()
    baseline = build_baseline(store.load(baseline_run))
    findings = detect_drift(store.load(fast_run), baseline)
    assert "final_loss_improved" in _codes(findings)
    assert not any(finding.severity == "critical" for finding in findings)


def test_missing_baseline_errors(workdir) -> None:
    with pytest.raises(WorkbenchError, match="Cannot find baseline"):
        load_baseline("does-not-exist")
