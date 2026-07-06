from __future__ import annotations

from typing import Any

from tinker_workbench.store import RunArtifacts


def probe_checkpoint(artifacts: RunArtifacts) -> dict[str, Any]:
    """Post-hoc checkpoint readiness from run artifacts (no API re-call).

    Uses checkpoint metadata plus eval sampling at the same step as evidence
    that the sampler actually served during the run.
    """
    if not artifacts.checkpoints:
        return {
            "checkpoint_path": None,
            "step": None,
            "sampler_ready": False,
            "adapter_applied": None,
            "native_sampling_ok": False,
            "openai_compatible_sampling_ok": None,
            "latency_ms": None,
            "eval_samples_at_step": 0,
            "error": "No checkpoints saved in this run.",
        }

    latest = max(artifacts.checkpoints, key=lambda row: row["step"])
    step = int(latest["step"])
    path = latest.get("path") or latest.get("checkpoint_path")
    sampler_ready = bool(latest.get("sampler_ready"))
    evals_at_step = [row for row in artifacts.evals if int(row["step"]) == step]
    native_ok = sampler_ready and len(evals_at_step) > 0

    method = (artifacts.summary or {}).get("method") or (
        (artifacts.config or {}).get("training", {}).get("method")
    )
    adapter_applied = method not in (None, "base", "none")

    error = None
    if not sampler_ready:
        error = "Checkpoint marked not sampler-ready."
    elif not evals_at_step:
        error = "No eval samples recorded at this checkpoint step."

    return {
        "checkpoint_path": path,
        "step": step,
        "sampler_ready": sampler_ready,
        "adapter_applied": adapter_applied,
        "native_sampling_ok": native_ok,
        "openai_compatible_sampling_ok": None,
        "latency_ms": None,
        "eval_samples_at_step": len(evals_at_step),
        "error": error,
    }
