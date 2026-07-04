from __future__ import annotations

import pytest

from tests.conftest import make_config
from tinker_workbench.backends import create_backend
from tinker_workbench.backends.tinker_api import TinkerBackend
from tinker_workbench.collab import build_collab_proposal
from tinker_workbench.errors import BackendError


def test_collab_proposal_targets_cost_issues() -> None:
    proposal = build_collab_proposal("tinker-cookbook-cost")

    assert proposal["target"] == "thinking-machines-lab/tinker-cookbook"
    assert any("issues/551" in issue for issue in proposal["issues"])
    assert "suggested_json_shape" in proposal


def test_collab_proposal_targets_checkpoint_probe() -> None:
    proposal = build_collab_proposal("tinker-checkpoint-probe")

    assert proposal["target"] == "thinking-machines-lab/tinker"
    assert any("issues/44" in issue for issue in proposal["issues"])
    assert proposal["suggested_json_shape"]["sampler_ready"] == "boolean"


def test_create_backend_rejects_unknown() -> None:
    with pytest.raises(BackendError, match="Unknown backend"):
        create_backend(make_config(), "gpu-under-the-desk")


def test_tinker_backend_requires_api_key(monkeypatch) -> None:
    monkeypatch.delenv("TINKER_API_KEY", raising=False)
    backend = TinkerBackend(make_config(mode="tinker"))
    with pytest.raises(BackendError, match="TINKER_API_KEY"):
        backend.start("test")


def test_tinker_backend_fails_fast_when_not_started() -> None:
    backend = TinkerBackend(make_config(mode="tinker"))
    with pytest.raises(BackendError, match="not started"):
        backend.sample("prompt", max_tokens=8)
