from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from tinker_workbench.datasets import Example


@dataclass(frozen=True)
class StepResult:
    step: int
    loss: float
    tokens: int
    learning_rate: float


@dataclass(frozen=True)
class Checkpoint:
    step: int
    path: str
    sampler_ready: bool


class TrainingBackend(Protocol):
    """The contract every training backend implements.

    The runner owns the loop, the schedule, budget accounting, and artifact
    writing; backends own only the state that training mutates. This keeps the
    mock simulator and the real Tinker adapter interchangeable.
    """

    name: str

    def start(self, run_id: str) -> None:
        """Acquire clients/state. Called once before the first step."""
        ...

    def train_step(self, step: int, batch: list[Example], learning_rate: float) -> StepResult:
        """Run one forward/backward + optimizer step over the batch."""
        ...

    def save_checkpoint(self, step: int) -> Checkpoint:
        """Persist weights and return a handle usable for sampling."""
        ...

    def sample(self, prompt: str, max_tokens: int, checkpoint: Checkpoint | None = None) -> str:
        """Sample a completion from the current (or given checkpoint's) weights."""
        ...

    def close(self) -> None:
        """Release clients. Called once, even on failure."""
        ...
