from __future__ import annotations

import math
from pathlib import Path

from tinker_workbench.doctor import diagnose
from tinker_workbench.store import RunArtifacts

SPARK_CHARS = "▁▂▃▄▅▆▇█"


def render_report(artifacts: RunArtifacts) -> str:
    """Render the full experiment report for one run as markdown."""
    config = artifacts.config or {}
    plan = artifacts.plan or {}
    summary = artifacts.summary or {}

    lines = [f"# {config.get('name', artifacts.run_dir.name)} — Experiment Report", ""]
    if config.get("description"):
        lines.extend([config["description"], ""])

    lines.extend(_summary_section(summary, plan))
    lines.extend(_training_section(artifacts))
    lines.extend(_eval_section(artifacts))
    lines.extend(_checkpoint_section(artifacts))
    lines.extend(_budget_section(plan, summary))
    lines.extend(_diagnostics_section(artifacts))
    lines.extend(_reproduce_section(artifacts, config))
    return "\n".join(lines) + "\n"


def write_report(artifacts: RunArtifacts, out_path: Path | None = None) -> Path:
    if out_path is None:
        report_dir = Path("reports")
        report_dir.mkdir(exist_ok=True)
        out_path = report_dir / f"{artifacts.run_dir.name}.md"
    out_path.write_text(render_report(artifacts), encoding="utf-8")
    return out_path


def _summary_section(summary: dict, plan: dict) -> list[str]:
    status = summary.get("status", "unknown")
    lines = [
        "## Summary",
        "",
        f"- Status: **{status}**"
        + (f" — {summary['failure_reason']}" if summary.get("failure_reason") else ""),
        f"- Backend: `{summary.get('backend', plan.get('mode', 'unknown'))}`",
        f"- Method: `{summary.get('method', plan.get('method', 'unknown'))}`",
        f"- Base model: `{summary.get('base_model', 'unknown')}`",
        f"- Steps: {summary.get('steps_completed', '?')}/{summary.get('steps_planned', '?')}",
        f"- Final loss: {_fmt(summary.get('final_loss'))}",
        f"- Wall time: {summary.get('wall_time_s', '?')}s",
        "",
    ]
    return lines


def _training_section(artifacts: RunArtifacts) -> list[str]:
    losses = [float(row["loss"]) for row in artifacts.metrics if "loss" in row]
    if not losses:
        return ["## Training", "", "No metrics recorded.", ""]
    finite = [loss for loss in losses if math.isfinite(loss)]
    lines = ["## Training", ""]
    if finite:
        best_step = min(
            range(len(losses)),
            key=lambda i: losses[i] if math.isfinite(losses[i]) else math.inf,
        )
        lines.extend(
            [
                "```",
                f"loss  {sparkline(finite)}",
                f"      step 0 {' ' * max(len(sparkline(finite)) - 14, 1)}step {len(losses) - 1}",
                "```",
                "",
                f"- First loss: {finite[0]:.4f}",
                f"- Best loss: {min(finite):.4f} (step {best_step})",
                f"- Last loss: {_fmt(losses[-1])}",
                "",
            ]
        )
    if len(finite) != len(losses):
        lines.extend([f"- **{len(losses) - len(finite)} non-finite loss value(s) recorded.**", ""])
    return lines


def _eval_section(artifacts: RunArtifacts) -> list[str]:
    if not artifacts.evals:
        return ["## Evals", "", "No evals were run.", ""]
    names = sorted({row["name"] for row in artifacts.evals})
    steps = sorted({row["step"] for row in artifacts.evals})
    lines = [
        "## Evals",
        "",
        "| step | " + " | ".join(names) + " |",
        "|---|" + "|".join("---" for _ in names) + "|",
    ]
    by_key = {(row["step"], row["name"]): row["score"] for row in artifacts.evals}
    for step in steps:
        cells = [str(step)]
        for name in names:
            score = by_key.get((step, name))
            cells.append(f"{score:.4f}" if score is not None else "-")
        lines.append("| " + " | ".join(cells) + " |")
    lines.append("")
    return lines


def _checkpoint_section(artifacts: RunArtifacts) -> list[str]:
    if not artifacts.checkpoints:
        return ["## Checkpoints", "", "No checkpoints saved.", ""]
    lines = ["## Checkpoints", ""]
    for row in artifacts.checkpoints:
        ready = "sampler-ready" if row.get("sampler_ready") else "not sampler-ready"
        lines.append(f"- step {row['step']}: `{row['path']}` ({ready})")
    lines.append("")
    return lines


def _budget_section(plan: dict, summary: dict) -> list[str]:
    budget = plan.get("budget", {})
    if not budget:
        return []
    planned_train = budget.get("planned_train_tokens")
    planned_sample = budget.get("planned_sample_tokens")
    actual_train = summary.get("total_train_tokens")
    actual_sample = summary.get("total_sample_tokens")
    actual_train_text = actual_train if actual_train is not None else "-"
    actual_sample_text = actual_sample if actual_sample is not None else "-"
    lines = [
        "## Budget Reconciliation",
        "",
        "| resource | planned | actual |",
        "|---|---|---|",
        f"| train tokens | {planned_train} | {actual_train_text} |",
        f"| sample tokens | {planned_sample} | {actual_sample_text} |",
        f"| checkpoints | {budget.get('checkpoints')} | {summary.get('checkpoints_saved', '-')} |",
    ]
    if budget.get("estimated_usd") is not None:
        lines.append(f"| estimated cost | ${budget['estimated_usd']} | - |")
    lines.extend(
        [
            "",
            f"- Checkpoint storage estimate: {budget.get('checkpoint_storage_gb', '?')} GB",
            "",
        ]
    )
    return lines


def _diagnostics_section(artifacts: RunArtifacts) -> list[str]:
    findings = diagnose(artifacts)
    if not findings:
        return ["## Diagnostics", "", "No issues detected.", ""]
    lines = ["## Diagnostics", ""]
    for finding in findings:
        lines.append(f"- **{finding.severity.upper()}** `{finding.code}`: {finding.message}")
        lines.append(f"  - Suggested action: {finding.suggestion}")
    lines.append("")
    return lines


def _reproduce_section(artifacts: RunArtifacts, config: dict) -> list[str]:
    seed = config.get("training", {}).get("seed", "?")
    return [
        "## Reproduce",
        "",
        "```bash",
        f"# artifacts: {artifacts.run_dir}",
        f"# seed: {seed}",
        "tinker-workbench run <config.yaml>   # config.json in the run dir is the resolved config",
        "```",
        "",
    ]


def sparkline(values: list[float]) -> str:
    if not values:
        return ""
    low = min(values)
    high = max(values)
    span = high - low
    if span <= 0:
        return SPARK_CHARS[0] * len(values)
    chars = []
    for value in values:
        index = int((value - low) / span * (len(SPARK_CHARS) - 1))
        chars.append(SPARK_CHARS[index])
    return "".join(chars)


def _fmt(value) -> str:
    if isinstance(value, (int, float)):
        if not math.isfinite(value):
            return "NaN"
        return f"{value:.4f}"
    return "-"
