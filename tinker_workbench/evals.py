from __future__ import annotations

import re
from typing import Any

from tinker_workbench.backends.base import Checkpoint, TrainingBackend
from tinker_workbench.config import EvalConfig
from tinker_workbench.datasets import Example
from tinker_workbench.errors import WorkbenchError


def evaluate_checkpoint(
    backend: TrainingBackend,
    checkpoint: Checkpoint,
    eval_config: EvalConfig,
    examples: list[Example],
) -> dict[str, Any]:
    """Sample the checkpoint on each eval example and grade the outputs.

    Returns one evals.jsonl row: aggregate score plus the token count spent,
    so budget reconciliation can include eval sampling.
    """
    subset = examples[: eval_config.num_examples]
    if not subset:
        raise WorkbenchError(f"Eval {eval_config.name!r} has no examples to grade.")

    scores = []
    sample_tokens = 0
    for example in subset:
        completion = backend.sample(
            example.prompt, max_tokens=eval_config.max_sample_tokens, checkpoint=checkpoint
        )
        sample_tokens += eval_config.max_sample_tokens
        scores.append(grade(eval_config.grader, completion, example.completion))

    return {
        "step": checkpoint.step,
        "name": eval_config.name,
        "grader": eval_config.grader,
        "score": round(sum(scores) / len(scores), 4),
        "num_examples": len(subset),
        "sample_tokens": sample_tokens,
    }


def grade(grader: str, completion: str, expected: str) -> float:
    if grader == "exact_match":
        return 1.0 if completion.strip() == expected.strip() else 0.0
    if grader == "contains":
        return 1.0 if expected.strip() in completion else 0.0
    if grader == "regex":
        return 1.0 if re.search(expected, completion) else 0.0
    if grader == "bits_recovered":
        return _bits_recovered(completion, expected)
    raise WorkbenchError(f"Unknown grader: {grader!r}")


def _bits_recovered(completion: str, expected: str) -> float:
    """Fraction of bit positions recovered, for the memorization study.

    A random guesser scores ~0.5 here; use the excess over 0.5 when reasoning
    about how many latent bits the model actually stored.
    """
    completion = completion.strip()
    expected = expected.strip()
    if not expected:
        return 0.0
    matched = sum(
        1 for got, want in zip(completion, expected, strict=False) if got == want
    )
    return matched / len(expected)
