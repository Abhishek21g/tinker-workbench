from __future__ import annotations

import json
import random
from dataclasses import dataclass
from pathlib import Path

from tinker_workbench.config import DataConfig
from tinker_workbench.errors import ConfigError


@dataclass(frozen=True)
class Example:
    prompt: str
    completion: str


def load_train_examples(data: DataConfig, seed: int) -> list[Example]:
    if data.source == "builtin:memorization":
        return _memorization_examples(data.train_examples, data.latent_bits, seed)
    if data.source.startswith("builtin:"):
        raise ConfigError(f"Unknown builtin dataset: {data.source}")
    return _jsonl_examples(Path(data.source))[: data.train_examples]


def load_eval_examples(data: DataConfig, seed: int) -> list[Example]:
    """Return the held-in eval set.

    For the memorization study the eval set is a deterministic subset of the
    training set: the question is whether the model can recall what it was
    trained on, not whether it generalizes.
    """
    if data.source == "builtin:memorization":
        train = _memorization_examples(data.train_examples, data.latent_bits, seed)
        rng = random.Random(seed + 1)
        count = min(data.eval_examples, len(train))
        return rng.sample(train, count)
    if data.source.startswith("builtin:"):
        raise ConfigError(f"Unknown builtin dataset: {data.source}")
    examples = _jsonl_examples(Path(data.source))
    return examples[-data.eval_examples :]


def _memorization_examples(count: int, latent_bits: int, seed: int) -> list[Example]:
    """Generate key -> secret-bitstring pairs for the memorization study.

    Mirrors the tinker-project-ideas memorization setup: each example carries
    `latent_bits` bits of irreducible information the model must store.
    """
    rng = random.Random(seed)
    examples = []
    for index in range(count):
        secret = "".join(rng.choice("01") for _ in range(latent_bits))
        examples.append(
            Example(
                prompt=f"Recall the secret bitstring for key-{index:04d}:",
                completion=secret,
            )
        )
    return examples


def _jsonl_examples(path: Path) -> list[Example]:
    if not path.exists():
        raise ConfigError(f"Dataset file not found: {path}")
    examples = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as error:
                raise ConfigError(f"{path}:{line_number} is not valid JSON: {error}") from error
            if "prompt" not in row or "completion" not in row:
                raise ConfigError(
                    f"{path}:{line_number} must contain 'prompt' and 'completion' keys."
                )
            examples.append(Example(prompt=str(row["prompt"]), completion=str(row["completion"])))
    if not examples:
        raise ConfigError(f"Dataset file is empty: {path}")
    return examples
