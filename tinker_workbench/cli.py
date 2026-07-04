from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from tinker_workbench.collab import build_collab_proposal
from tinker_workbench.compare import build_comparison
from tinker_workbench.config import load_config
from tinker_workbench.doctor import diagnose
from tinker_workbench.errors import WorkbenchError
from tinker_workbench.planner import build_plan
from tinker_workbench.report import write_report
from tinker_workbench.runner import execute_run
from tinker_workbench.store import RunStore


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.handler(args)
    except WorkbenchError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="tinker-workbench",
        description=(
            "Plan, run, observe, debug, and evaluate Tinker post-training experiments."
        ),
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    plan_parser = subparsers.add_parser(
        "plan", help="Validate a config and print the pre-run plan (tokens, cost, risks)."
    )
    plan_parser.add_argument("config", type=Path)
    plan_parser.set_defaults(handler=_cmd_plan)

    run_parser = subparsers.add_parser(
        "run", help="Execute one or more experiment configs and record full artifacts."
    )
    run_parser.add_argument("configs", type=Path, nargs="+")
    run_parser.add_argument(
        "--backend",
        choices=["mock", "tinker"],
        default=None,
        help="Override the config's mode (default: use config.mode).",
    )
    run_parser.add_argument("--quiet", action="store_true", help="Suppress progress output.")
    run_parser.set_defaults(handler=_cmd_run)

    runs_parser = subparsers.add_parser("runs", help="List recorded runs.")
    runs_parser.add_argument("--limit", type=int, default=20)
    runs_parser.set_defaults(handler=_cmd_runs)

    status_parser = subparsers.add_parser(
        "status", help="Show the current state of a run (works on interrupted runs)."
    )
    status_parser.add_argument("run", help="Run directory, run id, or 'latest'.")
    status_parser.set_defaults(handler=_cmd_status)

    doctor_parser = subparsers.add_parser(
        "doctor", help="Diagnose a run: divergence, NaNs, stalls, checkpoint and budget issues."
    )
    doctor_parser.add_argument("run", help="Run directory, run id, or 'latest'.")
    doctor_parser.add_argument("--json", action="store_true", dest="as_json")
    doctor_parser.set_defaults(handler=_cmd_doctor)

    compare_parser = subparsers.add_parser(
        "compare", help="Compare multiple runs side by side (markdown table)."
    )
    compare_parser.add_argument("runs", nargs="+", help="Run directories, run ids, or 'latest'.")
    compare_parser.set_defaults(handler=_cmd_compare)

    report_parser = subparsers.add_parser(
        "report", help="Generate the full markdown experiment report for a run."
    )
    report_parser.add_argument("run", help="Run directory, run id, or 'latest'.")
    report_parser.add_argument("--out", type=Path, default=None)
    report_parser.set_defaults(handler=_cmd_report)

    collab_parser = subparsers.add_parser(
        "collab", help="Export an upstream-facing collaboration proposal."
    )
    collab_parser.add_argument(
        "--target",
        choices=["tinker-cookbook-cost", "tinker-checkpoint-probe"],
        required=True,
    )
    collab_parser.add_argument("--run-dir", type=Path, default=None)
    collab_parser.set_defaults(handler=_cmd_collab)

    return parser


def _cmd_plan(args) -> int:
    config = load_config(args.config)
    plan = build_plan(config)
    print(json.dumps(plan, indent=2))
    return 0


def _cmd_run(args) -> int:
    progress = None if args.quiet else print
    exit_code = 0
    for config_path in args.configs:
        config = load_config(config_path)
        run_dir = execute_run(config, backend_name=args.backend, progress=progress)
        print(run_dir)
        store = RunStore()
        summary = store.load(run_dir).summary or {}
        if summary.get("status") == "failed":
            exit_code = 2
    return exit_code


def _cmd_runs(args) -> int:
    records = RunStore().list_runs()
    if not records:
        print("No runs recorded yet. Start one with: tinker-workbench run <config.yaml>")
        return 0
    print(f"{'run id':<42} {'method':<20} {'status':<16} {'steps':<9} final loss")
    for record in records[-args.limit :]:
        steps = f"{record.get('steps_completed', '?')}/{record.get('steps_planned', '?')}"
        loss = record.get("final_loss")
        loss_text = f"{loss:.4f}" if isinstance(loss, (int, float)) else "-"
        print(
            f"{record.get('run_id', '?'):<42} {record.get('method', '?'):<20} "
            f"{record.get('status', '?'):<16} {steps:<9} {loss_text}"
        )
    return 0


def _cmd_status(args) -> int:
    artifacts = RunStore().load(args.run)
    summary = artifacts.summary
    if summary:
        print(f"run:      {summary.get('run_id')}")
        print(f"status:   {summary.get('status')}"
              + (f" ({summary['failure_reason']})" if summary.get("failure_reason") else ""))
        print(f"backend:  {summary.get('backend')}  method: {summary.get('method')}")
        print(f"steps:    {summary.get('steps_completed')}/{summary.get('steps_planned')}")
        print(f"loss:     {summary.get('final_loss')}")
        print(
            f"tokens:   {summary.get('total_train_tokens')} train / "
            f"{summary.get('total_sample_tokens')} sample"
        )
    else:
        print(f"run:      {artifacts.run_dir.name}")
        print("status:   in progress or interrupted (no summary.json)")
        if artifacts.metrics:
            last = artifacts.metrics[-1]
            print(f"last step: {last['step']}  loss: {last['loss']}")
    print(f"checkpoints: {len(artifacts.checkpoints)}")
    for row in artifacts.evals[-4:]:
        print(f"eval:     step {row['step']} {row['name']} = {row['score']}")
    return 0


def _cmd_doctor(args) -> int:
    artifacts = RunStore().load(args.run)
    findings = diagnose(artifacts)
    if args.as_json:
        print(json.dumps([finding.to_dict() for finding in findings], indent=2))
    elif not findings:
        print("No issues detected.")
    else:
        for finding in findings:
            print(f"[{finding.severity.upper()}] {finding.code}: {finding.message}")
            print(f"    -> {finding.suggestion}")
    has_critical = any(finding.severity == "critical" for finding in findings)
    return 2 if has_critical else 0


def _cmd_compare(args) -> int:
    store = RunStore()
    artifacts = [store.load(ref) for ref in args.runs]
    print(build_comparison(artifacts), end="")
    return 0


def _cmd_report(args) -> int:
    artifacts = RunStore().load(args.run)
    report_path = write_report(artifacts, args.out)
    print(report_path)
    return 0


def _cmd_collab(args) -> int:
    proposal = build_collab_proposal(args.target, args.run_dir)
    print(json.dumps(proposal, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
