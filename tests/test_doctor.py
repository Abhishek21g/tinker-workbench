from __future__ import annotations

from pathlib import Path

from tests.conftest import make_config
from tinker_workbench.config import MockConfig, TrainingConfig
from tinker_workbench.doctor import diagnose
from tinker_workbench.runner import execute_run
from tinker_workbench.store import RunArtifacts, RunStore


def _codes(findings) -> set[str]:
    return {finding.code for finding in findings}


def _synthetic(metrics, **kwargs) -> RunArtifacts:
    return RunArtifacts(run_dir=Path("synthetic"), metrics=metrics, **kwargs)


def test_healthy_run_is_clean(workdir) -> None:
    run_dir = execute_run(make_config())
    findings = diagnose(RunStore().load(run_dir))
    assert not any(finding.severity == "critical" for finding in findings)
    assert "non_finite_loss" not in _codes(findings)
    assert "loss_divergence" not in _codes(findings)


def test_detects_nan_run(workdir) -> None:
    config = make_config(mock=MockConfig(inject={"nan_at_step": 6}))
    run_dir = execute_run(config)
    findings = diagnose(RunStore().load(run_dir))
    codes = _codes(findings)
    assert "run_failed" in codes
    assert "non_finite_loss" in codes


def test_detects_divergence(workdir) -> None:
    config = make_config(
        training=TrainingConfig(steps=16, batch_size=4, seed=11),
        mock=MockConfig(time_constant=3.0, inject={"diverge_at_step": 5}),
    )
    run_dir = execute_run(config)
    findings = diagnose(RunStore().load(run_dir))
    assert "loss_divergence" in _codes(findings)


def test_detects_stall(workdir) -> None:
    config = make_config(mock=MockConfig(time_constant=30.0, inject={"stall_at_step": 1}))
    run_dir = execute_run(config)
    findings = diagnose(RunStore().load(run_dir))
    assert "insufficient_progress" in _codes(findings)


def test_detects_missing_summary() -> None:
    artifacts = _synthetic([{"step": 0, "loss": 2.0}])
    assert "run_incomplete" in _codes(diagnose(artifacts))


def test_detects_no_checkpoints() -> None:
    metrics = [{"step": i, "loss": 2.0 - i * 0.1} for i in range(10)]
    artifacts = _synthetic(metrics, summary={"status": "completed"})
    assert "no_checkpoints" in _codes(diagnose(artifacts))


def test_detects_checkpoint_gap() -> None:
    metrics = [{"step": i, "loss": 2.0 - i * 0.05} for i in range(30)]
    artifacts = _synthetic(
        metrics,
        summary={"status": "completed"},
        checkpoints=[{"step": 9, "path": "x", "sampler_ready": True}],
        config={"checkpoints": {"every_steps": 10}},
    )
    assert "checkpoint_gap" in _codes(diagnose(artifacts))


def test_detects_token_overrun() -> None:
    metrics = [{"step": i, "loss": 2.0 - i * 0.1} for i in range(10)]
    artifacts = _synthetic(
        metrics,
        summary={"status": "completed", "total_train_tokens": 2000},
        checkpoints=[{"step": 9, "path": "x", "sampler_ready": True}],
        config={"checkpoints": {"every_steps": 10}},
        plan={"budget": {"planned_train_tokens": 1000}},
    )
    assert "token_overrun" in _codes(diagnose(artifacts))


def test_detects_eval_regression() -> None:
    metrics = [{"step": i, "loss": 2.0 - i * 0.1} for i in range(10)]
    artifacts = _synthetic(
        metrics,
        summary={"status": "completed"},
        checkpoints=[{"step": 9, "path": "x", "sampler_ready": True}],
        config={"checkpoints": {"every_steps": 10}},
        evals=[
            {"step": 4, "name": "exact_match", "score": 0.9},
            {"step": 9, "name": "exact_match", "score": 0.6},
        ],
    )
    findings = diagnose(artifacts)
    assert "eval_regression" in _codes(findings)
    regression = next(f for f in findings if f.code == "eval_regression")
    assert "step-4" in regression.suggestion


def test_findings_sorted_by_severity(workdir) -> None:
    config = make_config(mock=MockConfig(inject={"nan_at_step": 6}))
    run_dir = execute_run(config)
    findings = diagnose(RunStore().load(run_dir))
    severities = [finding.severity for finding in findings]
    assert severities == sorted(severities, key={"critical": 0, "warning": 1, "info": 2}.get)
