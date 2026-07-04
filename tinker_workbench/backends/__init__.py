from __future__ import annotations

from tinker_workbench.backends.base import Checkpoint, StepResult, TrainingBackend
from tinker_workbench.config import ExperimentConfig
from tinker_workbench.errors import BackendError

__all__ = ["Checkpoint", "StepResult", "TrainingBackend", "create_backend"]


def create_backend(config: ExperimentConfig, backend_name: str | None = None) -> TrainingBackend:
    """Instantiate the backend for a run.

    `backend_name` overrides `config.mode` when provided (CLI --backend flag).
    """
    name = backend_name or config.mode
    if name == "mock":
        from tinker_workbench.backends.mock import MockBackend

        return MockBackend(config)
    if name == "tinker":
        from tinker_workbench.backends.tinker_api import TinkerBackend

        return TinkerBackend(config)
    raise BackendError(f"Unknown backend: {name!r}. Expected 'mock' or 'tinker'.")
