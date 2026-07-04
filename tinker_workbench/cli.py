from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

from tinker_workbench.config import load_config
from tinker_workbench.planner import build_plan
from tinker_workbench.report import write_report
from tinker_workbench.runner import run_mock_experiment


def main() -> None:
    parser = argparse.ArgumentParser(prog="tinker-workbench")
    subparsers = parser.add_subparsers(dest="command", required=True)

    plan_parser = subparsers.add_parser("plan", help="Create a pre-run experiment plan.")
    plan_parser.add_argument("config", type=Path)

    run_parser = subparsers.add_parser("run", help="Run an experiment.")
    run_parser.add_argument("config", type=Path)
    run_parser.add_argument("--mock", action="store_true", help="Run without calling Tinker APIs.")

    report_parser = subparsers.add_parser("report", help="Generate a markdown report for a run.")
    report_parser.add_argument("run_dir", type=Path)

    args = parser.parse_args()

    if args.command == "plan":
        config = load_config(args.config)
        plan = build_plan(config)
        print(json.dumps(plan, indent=2))
        return

    if args.command == "run":
        if not args.mock:
            raise SystemExit("Only --mock is implemented so far. Real Tinker runs need approval first.")
        config = load_config(args.config)
        run_dir = run_mock_experiment(config)
        latest = Path("runs/latest")
        if latest.exists() or latest.is_symlink():
            latest.unlink() if latest.is_symlink() else shutil.rmtree(latest)
        latest.symlink_to(run_dir.resolve(), target_is_directory=True)
        print(str(run_dir))
        return

    if args.command == "report":
        report_path = write_report(args.run_dir)
        print(str(report_path))
        return


if __name__ == "__main__":
    main()

