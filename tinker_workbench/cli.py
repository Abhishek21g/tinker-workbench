from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from tinker_workbench.collab import build_collab_proposal
from tinker_workbench.compare import build_comparison
from tinker_workbench.config import load_config
from tinker_workbench.conformance import compare_renderers
from tinker_workbench.dashboard import export_dashboard
from tinker_workbench.doctor import diagnose
from tinker_workbench.errors import WorkbenchError
from tinker_workbench.planner import build_plan
from tinker_workbench.probe import probe_checkpoint
from tinker_workbench.reference import detect_drift, load_baseline, save_baseline
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

    baseline_parser = subparsers.add_parser(
        "baseline", help="Pin a completed run as the reference baseline for drift checks."
    )
    baseline_parser.add_argument("run", help="Run directory, run id, or 'latest'.")
    baseline_parser.add_argument("--name", default=None, help="Baseline name (default: run name).")
    baseline_parser.set_defaults(handler=_cmd_baseline)

    drift_parser = subparsers.add_parser(
        "drift",
        help="Compare a run against a pinned baseline; exit 2 on critical regressions.",
    )
    drift_parser.add_argument("run", help="Run directory, run id, or 'latest'.")
    drift_parser.add_argument("--baseline", required=True, help="Baseline name or path.")
    drift_parser.add_argument("--json", action="store_true", dest="as_json")
    drift_parser.set_defaults(handler=_cmd_drift)

    conformance_parser = subparsers.add_parser(
        "conformance",
        help="Token-exact renderer comparison (e.g. hf:MODEL vs cookbook:RENDERER@MODEL).",
    )
    conformance_parser.add_argument("renderer_a", help="Renderer spec: hf:MODEL or "
                                    "cookbook:RENDERER@MODEL")
    conformance_parser.add_argument("renderer_b", help="Renderer spec to compare against.")
    conformance_parser.add_argument("--json", action="store_true", dest="as_json")
    conformance_parser.set_defaults(handler=_cmd_conformance)

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

    export_parser = subparsers.add_parser(
        "export-dashboard",
        help="Export run health, budget, and checkpoint data for the web dashboard.",
    )
    export_parser.add_argument("run", nargs="?", default="latest", help="Run id or 'latest'.")
    export_parser.add_argument(
        "--out",
        type=Path,
        default=Path("site/data/dashboard.json"),
        help="Output JSON path (default: site/data/dashboard.json).",
    )
    export_parser.add_argument(
        "--runs-root",
        type=Path,
        default=Path("runs"),
        help="Runs directory (default: runs/).",
    )
    export_parser.set_defaults(handler=_cmd_export_dashboard)

    probe_parser = subparsers.add_parser(
        "probe",
        help="Check checkpoint sampler readiness from run artifacts.",
    )
    probe_parser.add_argument("run", help="Run directory, run id, or 'latest'.")
    probe_parser.add_argument("--json", action="store_true", dest="as_json")
    probe_parser.set_defaults(handler=_cmd_probe)

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


def _cmd_baseline(args) -> int:
    artifacts = RunStore().load(args.run)
    path = save_baseline(artifacts, args.name)
    print(path)
    return 0


def _cmd_drift(args) -> int:
    artifacts = RunStore().load(args.run)
    baseline = load_baseline(args.baseline)
    findings = detect_drift(artifacts, baseline)
    if args.as_json:
        print(json.dumps([finding.to_dict() for finding in findings], indent=2))
    elif not findings:
        print(f"No drift vs baseline {baseline['name']!r}.")
    else:
        for finding in findings:
            print(f"[{finding.severity.upper()}] {finding.code}: {finding.message}")
    has_critical = any(finding.severity == "critical" for finding in findings)
    return 2 if has_critical else 0


def _cmd_conformance(args) -> int:
    renderer_a = _build_renderer(args.renderer_a)
    renderer_b = _build_renderer(args.renderer_b)
    report = compare_renderers(renderer_a, renderer_b)
    if args.as_json:
        print(json.dumps(report.to_dict(), indent=2))
    else:
        for case in report.cases:
            marker = "ok  " if case.match else "FAIL"
            line = f"{marker} {case.case}"
            if not case.match:
                line += f"  (diverges at token {case.first_divergence}: {case.detail})"
            print(line)
        print(f"match rate: {report.match_rate * 100:.0f}%"
              f" — {'CONFORMANT' if report.conformant else 'NOT CONFORMANT'}")
    return 0 if report.conformant else 2


def _build_renderer(spec: str):
    if spec.startswith("hf:"):
        from tinker_workbench.conformance import HFChatTemplateRenderer

        return HFChatTemplateRenderer(spec[3:])
    if spec.startswith("cookbook:"):
        from tinker_workbench.conformance import CookbookRenderer

        rest = spec[len("cookbook:") :]
        renderer_name, separator, model_name = rest.partition("@")
        if not separator:
            raise WorkbenchError(
                "cookbook renderer spec must be cookbook:RENDERER@MODEL, "
                f"got {spec!r}."
            )
        return CookbookRenderer(renderer_name, model_name)
    raise WorkbenchError(
        f"Unknown renderer spec {spec!r}. Use hf:MODEL or cookbook:RENDERER@MODEL."
    )


def _cmd_collab(args) -> int:
    proposal = build_collab_proposal(args.target, args.run_dir)
    print(json.dumps(proposal, indent=2))
    return 0


def _cmd_export_dashboard(args) -> int:
    out = export_dashboard(run_ref=args.run, runs_root=args.runs_root, out=args.out)
    print(out)
    return 0


def _cmd_probe(args) -> int:
    artifacts = RunStore().load(args.run)
    result = probe_checkpoint(artifacts)
    if args.as_json:
        print(json.dumps(result, indent=2))
    else:
        status = "ok" if result["native_sampling_ok"] else "fail"
        print(f"probe: {status}")
        print(f"checkpoint: step {result['step']}  sampler_ready={result['sampler_ready']}")
        if result.get("error"):
            print(f"error: {result['error']}")
    return 0 if result["native_sampling_ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
