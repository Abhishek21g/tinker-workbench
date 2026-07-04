from __future__ import annotations

import json
import shutil

from tests.conftest import CONFIGS_DIR
from tinker_workbench.cli import main


def _copy_config(workdir, name: str) -> str:
    target = workdir / name
    shutil.copy(CONFIGS_DIR / name, target)
    return str(target)


def test_plan_command(workdir, capsys) -> None:
    config = _copy_config(workdir, "memorization_sft.yaml")
    assert main(["plan", config]) == 0
    plan = json.loads(capsys.readouterr().out)
    assert plan["name"] == "memorization-sft"
    assert plan["budget"]["planned_train_tokens"] > 0


def test_run_report_doctor_status_flow(workdir, capsys) -> None:
    config = _copy_config(workdir, "memorization_sft.yaml")

    assert main(["run", config, "--quiet"]) == 0
    run_dir = capsys.readouterr().out.strip().splitlines()[-1]
    assert (workdir / run_dir).exists() or run_dir.startswith("runs/")

    assert main(["status", "latest"]) == 0
    status_out = capsys.readouterr().out
    assert "status:   completed" in status_out

    assert main(["doctor", "latest"]) == 0
    capsys.readouterr()

    assert main(["report", "latest"]) == 0
    report_path = capsys.readouterr().out.strip()
    assert (workdir / report_path).exists()

    assert main(["runs"]) == 0
    assert "memorization-sft" in capsys.readouterr().out


def test_failed_run_exit_codes(workdir, capsys) -> None:
    config = _copy_config(workdir, "failure_nan.yaml")
    assert main(["run", config, "--quiet"]) == 2
    capsys.readouterr()
    # doctor exits 2 on critical findings
    assert main(["doctor", "latest", "--json"]) == 2
    findings = json.loads(capsys.readouterr().out)
    assert any(finding["code"] == "non_finite_loss" for finding in findings)


def test_compare_command(workdir, capsys) -> None:
    sft = _copy_config(workdir, "memorization_sft.yaml")
    rl = _copy_config(workdir, "memorization_rl_terminal.yaml")
    assert main(["run", sft, rl, "--quiet"]) == 0
    capsys.readouterr()
    assert main(["compare", "latest"]) == 0
    assert "Run Comparison" in capsys.readouterr().out


def test_unknown_run_reference(workdir, capsys) -> None:
    assert main(["status", "nope"]) == 1
    assert "Cannot resolve run" in capsys.readouterr().err
