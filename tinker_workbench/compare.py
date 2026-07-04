from __future__ import annotations

from tinker_workbench.store import RunArtifacts


def build_comparison(runs: list[RunArtifacts]) -> str:
    """Render a markdown comparison across runs (the study-level view).

    Designed for the memorization-study workflow: run sft / rl_dense /
    rl_terminal as separate runs, then compare final loss and eval scores
    side by side.
    """
    eval_names = sorted({row["name"] for run in runs for row in run.evals})

    header = ["run", "method", "status", "steps", "final loss", "train tokens"]
    header.extend(f"best {name}" for name in eval_names)

    lines = [
        "# Run Comparison",
        "",
        "| " + " | ".join(header) + " |",
        "|" + "|".join("---" for _ in header) + "|",
    ]

    best_by_eval: dict[str, tuple[float, str]] = {}
    for run in runs:
        summary = run.summary or {}
        run_id = summary.get("run_id", run.run_dir.name)
        row = [
            run_id,
            summary.get("method", "?"),
            summary.get("status", "unknown"),
            f"{summary.get('steps_completed', '?')}/{summary.get('steps_planned', '?')}",
            _fmt(summary.get("final_loss")),
            str(summary.get("total_train_tokens", "?")),
        ]
        for name in eval_names:
            scores = [r["score"] for r in run.evals if r["name"] == name]
            if scores:
                best = max(scores)
                row.append(f"{best:.4f}")
                if name not in best_by_eval or best > best_by_eval[name][0]:
                    best_by_eval[name] = (best, run_id)
            else:
                row.append("-")
        lines.append("| " + " | ".join(row) + " |")

    if best_by_eval:
        lines.extend(["", "## Leaders", ""])
        for name, (score, run_id) in sorted(best_by_eval.items()):
            lines.append(f"- `{name}`: **{score:.4f}** ({run_id})")

    return "\n".join(lines) + "\n"


def _fmt(value) -> str:
    if isinstance(value, (int, float)):
        return f"{value:.4f}"
    return "-"
