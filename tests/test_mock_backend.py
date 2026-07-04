from __future__ import annotations

import math

from tests.conftest import make_config
from tinker_workbench.backends.mock import MockBackend
from tinker_workbench.config import MockConfig, TrainingConfig
from tinker_workbench.datasets import load_train_examples


def _losses(config, steps: int = 12) -> list[float]:
    backend = MockBackend(config)
    backend.start("test")
    examples = load_train_examples(config.data, config.training.seed)
    batch = examples[: config.training.batch_size]
    return [
        backend.train_step(step, batch, config.training.learning_rate).loss
        for step in range(steps)
    ]


def test_deterministic_across_instances() -> None:
    config = make_config()
    assert _losses(config) == _losses(config)


def test_loss_decreases() -> None:
    losses = _losses(make_config(), steps=20)
    assert losses[-1] < losses[0]
    assert min(losses) < 1.0


def test_seed_changes_curve() -> None:
    base = make_config()
    other = make_config(training=TrainingConfig(steps=12, seed=99))
    assert _losses(base) != _losses(other)


def test_nan_injection() -> None:
    config = make_config(mock=MockConfig(inject={"nan_at_step": 5}))
    losses = _losses(config, steps=8)
    assert all(math.isfinite(loss) for loss in losses[:5])
    assert math.isnan(losses[5])


def test_divergence_injection() -> None:
    config = make_config(mock=MockConfig(time_constant=4.0, inject={"diverge_at_step": 6}))
    losses = _losses(config, steps=20)
    assert losses[-1] > losses[5] * 2


def test_stall_injection() -> None:
    config = make_config(mock=MockConfig(time_constant=4.0, inject={"stall_at_step": 3}))
    losses = _losses(config, steps=20)
    # After the stall step, loss stops improving beyond noise.
    assert abs(losses[-1] - losses[4]) < 0.3


def test_rl_terminal_slower_than_sft() -> None:
    sft = make_config(training=TrainingConfig(steps=12, method="sft", seed=1))
    rl = make_config(training=TrainingConfig(steps=12, method="rl_terminal_reward", seed=1))
    assert _losses(rl)[-1] > _losses(sft)[-1]


def test_sampling_improves_with_training() -> None:
    config = make_config()
    backend = MockBackend(config)
    backend.start("test")
    examples = load_train_examples(config.data, config.training.seed)
    example = examples[0]

    early = backend.save_checkpoint(0)
    late = backend.save_checkpoint(200)

    def recovered(checkpoint) -> int:
        sample = backend.sample(example.prompt, max_tokens=16, checkpoint=checkpoint)
        pairs = zip(sample, example.completion, strict=False)
        return sum(1 for got, want in pairs if got == want)

    assert recovered(late) >= recovered(early)
    late_sample = backend.sample(example.prompt, max_tokens=16, checkpoint=late)
    assert late_sample == example.completion
