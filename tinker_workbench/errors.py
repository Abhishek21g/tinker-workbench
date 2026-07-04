from __future__ import annotations


class WorkbenchError(Exception):
    """Base error for user-facing workbench failures.

    The CLI catches this and prints the message without a traceback, so
    messages should be actionable on their own.
    """


class ConfigError(WorkbenchError):
    """Raised when an experiment config is missing or invalid."""


class BackendError(WorkbenchError):
    """Raised when a training backend cannot start or fails mid-run."""


class RunNotFoundError(WorkbenchError):
    """Raised when a run directory or run id cannot be resolved."""
