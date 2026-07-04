from __future__ import annotations

import math
import random

from tinker_workbench.backends.base import Checkpoint, StepResult
from tinker_workbench.config import ExperimentConfig
from tinker_workbench.datasets import Example

REFERENCE_LEARNING_RATE = 1e-4

# Relative sample-efficiency of each training method in the simulator. These
# exist so the memorization-study workflow (sft vs RL variants) produces
# distinguishable curves to exercise compare/report/doctor against. They are
# simulator assumptions, not research claims.
METHOD_TIME_CONSTANT_SCALE = {
    "sft": 1.0,
    "rl_dense_reward": 1.6,
    "rl_terminal_reward": 2.5,
}


class MockBackend:
    """Deterministic training simulator.

    Loss follows an exponential decay toward a floor, perturbed by seeded
    noise, with optional injected failure modes (NaN, divergence, stall,
    spike) so `doctor` and the report pipeline can be developed and tested
    without spending real Tinker credits. Identical config + seed always
    produces identical artifacts.
    """

    name = "mock"

    def __init__(self, config: ExperimentConfig) -> None:
        self.config = config
        self.run_id = "unbound"
        self.last_trained_step = -1

    def start(self, run_id: str, run_dir=None) -> None:
        self.run_id = run_id

    def train_step(self, step: int, batch: list[Example], learning_rate: float) -> StepResult:
        loss = self._loss_at(step, learning_rate)
        tokens = len(batch) * self.config.data.avg_tokens_per_example
        self.last_trained_step = step
        return StepResult(step=step, loss=loss, tokens=tokens, learning_rate=learning_rate)

    def save_checkpoint(self, step: int) -> Checkpoint:
        return Checkpoint(
            step=step,
            path=f"mock://{self.run_id}/checkpoint-{step:05d}",
            sampler_ready=True,
        )

    def sample(self, prompt: str, max_tokens: int, checkpoint: Checkpoint | None = None) -> str:
        step = checkpoint.step if checkpoint is not None else max(self.last_trained_step, 0)
        expected = self._expected_completion(prompt)
        if expected is None:
            return "[mock sample: unknown prompt]"

        # Per-token recall probability rises with training progress. Exact
        # match then emerges naturally once per-token recall is high, which
        # gives graders like bits_recovered a smooth learning curve.
        progress = self._progress(step, self.config.training.learning_rate)
        recall = 0.5 + 0.5 * min(progress, 0.995)
        rng = random.Random(f"{self.config.training.seed}:sample:{step}:{prompt}")
        if set(expected) <= {"0", "1"}:
            return "".join(
                bit if rng.random() < recall else ("1" if bit == "0" else "0")
                for bit in expected
            )[:max_tokens]
        if rng.random() < progress:
            return expected[:max_tokens]
        return "[mock sample: not yet memorized]"

    def close(self) -> None:
        pass

    def _progress(self, step: int, learning_rate: float) -> float:
        """Fraction of learnable signal absorbed by `step`, in [0, 1)."""
        scale = METHOD_TIME_CONSTANT_SCALE.get(self.config.training.method, 1.0)
        lr_ratio = learning_rate / REFERENCE_LEARNING_RATE
        time_constant = self.config.mock.time_constant * scale / max(lr_ratio, 1e-6)
        time_constant = min(max(time_constant, 1.0), 1000.0)
        stall_at = self.config.mock.inject.get("stall_at_step")
        if stall_at is not None:
            step = min(step, stall_at)
        return 1.0 - math.exp(-step / time_constant)

    def _loss_at(self, step: int, learning_rate: float) -> float:
        mock = self.config.mock
        inject = mock.inject

        nan_at = inject.get("nan_at_step")
        if nan_at is not None and step >= nan_at:
            return float("nan")

        base = mock.loss_floor + (mock.initial_loss - mock.loss_floor) * (
            1.0 - self._progress(step, learning_rate)
        )

        diverge_at = inject.get("diverge_at_step")
        if diverge_at is not None and step >= diverge_at:
            base = self._loss_at_clean(diverge_at, learning_rate) * (1.15 ** (step - diverge_at))

        spike_at = inject.get("spike_at_step")
        if spike_at is not None and step == spike_at:
            base *= 3.0

        rng = random.Random(f"{self.config.training.seed}:loss:{step}")
        return max(base + rng.gauss(0.0, mock.noise), 0.0)

    def _loss_at_clean(self, step: int, learning_rate: float) -> float:
        mock = self.config.mock
        return mock.loss_floor + (mock.initial_loss - mock.loss_floor) * (
            1.0 - self._progress(step, learning_rate)
        )

    def _expected_completion(self, prompt: str) -> str | None:
        from tinker_workbench.datasets import load_train_examples

        for example in load_train_examples(self.config.data, self.config.training.seed):
            if example.prompt == prompt:
                return example.completion
        return None
