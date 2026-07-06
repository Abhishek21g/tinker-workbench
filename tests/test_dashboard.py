from __future__ import annotations

from pathlib import Path

from tests.conftest import make_config
from tinker_workbench.dashboard import build_dashboard_payload, export_dashboard
from tinker_workbench.probe import probe_checkpoint
from tinker_workbench.runner import execute_run
from tinker_workbench.store import RunStore


def test_probe_ok_after_successful_run(workdir) -> None:
    run_dir = execute_run(make_config())
    artifacts = RunStore().load(run_dir)
    result = probe_checkpoint(artifacts)
    assert result["sampler_ready"] is True
    assert result["native_sampling_ok"] is True
    assert result["eval_samples_at_step"] > 0


def test_export_dashboard_writes_json(workdir, tmp_path: Path) -> None:
    run_dir = execute_run(make_config())
    out = tmp_path / "dashboard.json"
    export_dashboard(run_ref=run_dir.name, runs_root=Path("runs"), out=out)
    payload = build_dashboard_payload(run_ref=run_dir.name, runs_root=Path("runs"))
    assert payload["selected_run"]["run_id"]
    assert out.exists()
    assert "findings" in payload["selected_run"]
    assert "probe" in payload["selected_run"]
