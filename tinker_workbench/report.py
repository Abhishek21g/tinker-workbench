from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def write_report(run_dir: Path) -> Path:
    run_dir = run_dir.resolve()
    config = _read_json(run_dir / "config.json")
    plan = _read_json(run_dir / "plan.json")
    metrics = _read_jsonl(run_dir / "metrics.jsonl")
    checkpoints = _read_jsonl(run_dir / "checkpoints.jsonl")

    report_dir = Path("reports")
    report_dir.mkdir(exist_ok=True)
    report_path = report_dir / f"{run_dir.name}.md"

    best_by_method: dict[str, int] = {}
    for row in metrics:
        method = str(row["method"])
        best_by_method[method] = max(best_by_method.get(method, 0), int(row["bits_recovered"]))

    lines = [
        f"# {config['name']} Report",
        "",
        "## Plan",
        "",
        f"- Mode: `{plan['mode']}`",
        f"- Study: `{plan['study_type']}`",
        f"- Base model: `{plan['model'].get('base_model', 'unknown')}`",
        f"- Total planned tokens: `{plan['budget']['total_tokens']}`",
        f"- Checkpoint storage estimate: `{plan['budget']['checkpoint_storage_gb']} GB`",
        "",
        "## Results",
        "",
    ]
    for method, bits in sorted(best_by_method.items()):
        lines.append(f"- `{method}` recovered `{bits}` bits in mock mode.")

    lines.extend(["", "## Checkpoints", ""])
    for checkpoint in checkpoints:
        lines.append(
            "- step `{step}` path `{path}` sampler_ready=`{sampler}` adapter_applied=`{adapter}`".format(
                step=checkpoint["step"],
                path=checkpoint["path"],
                sampler=checkpoint["sampler_ready"],
                adapter=checkpoint["adapter_applied"],
            )
        )

    if plan["risks"]:
        lines.extend(["", "## Risks", ""])
        for risk in plan["risks"]:
            lines.append(f"- {risk}")

    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report_path


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]

