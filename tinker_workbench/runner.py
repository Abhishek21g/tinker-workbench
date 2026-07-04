from __future__ import annotations

import math
import time
from collections.abc import Callable
from pathlib import Path

from tinker_workbench.backends import create_backend
from tinker_workbench.config import ExperimentConfig
from tinker_workbench.datasets import Example, load_eval_examples, load_train_examples
from tinker_workbench.evals import evaluate_checkpoint
from tinker_workbench.events import EventLog
from tinker_workbench.planner import build_plan
from tinker_workbench.store import RunStore, append_jsonl, write_json

Progress = Callable[[str], None]


def execute_run(
    config: ExperimentConfig,
    backend_name: str | None = None,
    store: RunStore | None = None,
    progress: Progress | None = None,
) -> Path:
    """Run one experiment end to end and leave a complete artifact trail.

    Artifacts written to the run directory:
      config.json, plan.json  — what was intended
      events.jsonl            — what happened, in order
      metrics.jsonl           — per-step loss/tokens/lr
      checkpoints.jsonl       — saved checkpoints
      evals.jsonl             — eval scores per checkpoint
      summary.json            — final status and totals

    The loop stops early on non-finite loss (status "failed") or on hitting
    budget.max_train_tokens (status "stopped_budget"); everything already
    written stays valid for doctor/report.
    """
    store = store or RunStore()
    say = progress or (lambda _line: None)

    run_id, run_dir = store.create_run_dir(config.name)
    plan = build_plan(config)
    write_json(run_dir / "config.json", config.to_dict())
    write_json(run_dir / "plan.json", plan)
    events = EventLog(run_dir / "events.jsonl")

    training = config.training
    train_examples = load_train_examples(config.data, training.seed)
    eval_examples = load_eval_examples(config.data, training.seed)

    backend = create_backend(config, backend_name)
    started_at = time.monotonic()
    status = "completed"
    failure_reason: str | None = None
    total_train_tokens = 0
    total_sample_tokens = 0
    final_loss: float | None = None
    checkpoint_count = 0

    events.emit(
        "run.start",
        run_id=run_id,
        name=config.name,
        backend=backend_name or config.mode,
        method=training.method,
        base_model=config.model.base_model,
        steps=training.steps,
    )
    say(f"run {run_id}: {training.method} on {config.model.base_model} ({training.steps} steps)")

    backend.start(run_id, run_dir)
    try:
        for step in range(training.steps):
            learning_rate = _scheduled_lr(training.learning_rate, training.lr_schedule, step,
                                          training.steps)
            batch = _select_batch(train_examples, step, training.batch_size)
            result = backend.train_step(step, batch, learning_rate)
            total_train_tokens += result.tokens
            final_loss = result.loss

            append_jsonl(
                run_dir / "metrics.jsonl",
                {
                    "step": step,
                    "loss": result.loss,
                    "learning_rate": learning_rate,
                    "tokens": result.tokens,
                    "cumulative_train_tokens": total_train_tokens,
                },
            )
            events.emit("step.end", step=step, loss=result.loss, tokens=result.tokens)

            if not math.isfinite(result.loss):
                status = "failed"
                failure_reason = f"non-finite loss at step {step}"
                events.emit("run.failed", step=step, reason=failure_reason)
                say(f"  step {step}: non-finite loss, stopping")
                break

            if (step + 1) % config.checkpoints.every_steps == 0:
                checkpoint = backend.save_checkpoint(step)
                checkpoint_count += 1
                append_jsonl(
                    run_dir / "checkpoints.jsonl",
                    {
                        "step": checkpoint.step,
                        "path": checkpoint.path,
                        "sampler_ready": checkpoint.sampler_ready,
                    },
                )
                events.emit("checkpoint.saved", step=step, path=checkpoint.path)
                say(f"  step {step}: loss {result.loss:.4f}, checkpoint saved")

                for eval_config in config.evals:
                    row = evaluate_checkpoint(backend, checkpoint, eval_config, eval_examples)
                    total_sample_tokens += row["sample_tokens"]
                    append_jsonl(run_dir / "evals.jsonl", row)
                    events.emit(
                        "eval.completed", step=step, name=row["name"], score=row["score"]
                    )
                    say(f"  step {step}: eval {row['name']} = {row['score']}")

            budget = config.budget
            if budget.max_train_tokens and total_train_tokens >= budget.max_train_tokens:
                if step + 1 < training.steps:
                    status = "stopped_budget"
                    failure_reason = (
                        f"train token budget reached at step {step} "
                        f"({total_train_tokens}/{budget.max_train_tokens})"
                    )
                    events.emit("run.stopped", step=step, reason=failure_reason)
                    say(f"  step {step}: {failure_reason}")
                    break
    finally:
        backend.close()

    wall_time_s = round(time.monotonic() - started_at, 3)
    summary = {
        "run_id": run_id,
        "name": config.name,
        "status": status,
        "failure_reason": failure_reason,
        "backend": backend_name or config.mode,
        "method": training.method,
        "base_model": config.model.base_model,
        "steps_completed": _steps_completed(run_dir),
        "steps_planned": training.steps,
        "final_loss": final_loss,
        "checkpoints_saved": checkpoint_count,
        "total_train_tokens": total_train_tokens,
        "total_sample_tokens": total_sample_tokens,
        "wall_time_s": wall_time_s,
    }
    write_json(run_dir / "summary.json", summary)
    if status == "completed":
        events.emit("run.completed", steps=summary["steps_completed"])
    store.update_latest(run_dir)
    store.append_index(
        {
            "run_id": run_id,
            "name": config.name,
            "status": status,
            "method": training.method,
            "base_model": config.model.base_model,
        }
    )
    say(f"run {run_id}: {status}")
    return run_dir


def _scheduled_lr(base_lr: float, schedule: str, step: int, total_steps: int) -> float:
    if schedule == "constant":
        return base_lr
    fraction = step / max(total_steps, 1)
    if schedule == "linear":
        return base_lr * (1.0 - fraction)
    if schedule == "cosine":
        return base_lr * 0.5 * (1.0 + math.cos(math.pi * fraction))
    return base_lr


def _select_batch(examples: list[Example], step: int, batch_size: int) -> list[Example]:
    """Deterministic round-robin batching so runs are reproducible."""
    start = (step * batch_size) % len(examples)
    batch = []
    for offset in range(batch_size):
        batch.append(examples[(start + offset) % len(examples)])
    return batch


def _steps_completed(run_dir: Path) -> int:
    metrics_path = run_dir / "metrics.jsonl"
    if not metrics_path.exists():
        return 0
    with metrics_path.open("r", encoding="utf-8") as handle:
        return sum(1 for line in handle if line.strip())
