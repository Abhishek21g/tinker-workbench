from __future__ import annotations

import json
import math
from pathlib import Path

import pytest

from tests.conftest import make_config
from tinker_workbench.backends.local import LocalBackend
from tinker_workbench.config import LocalConfig, TrainingConfig
from tinker_workbench.datasets import load_train_examples
from tinker_workbench.errors import BackendError
from tinker_workbench.runner import execute_run
from tinker_workbench.store import RunStore

pytest.importorskip("numpy")


def _local_config(**training_overrides):
    training = dict(steps=120, batch_size=8, learning_rate=0.03, seed=7)
    training.update(training_overrides)
    return make_config(
        mode="local",
        training=TrainingConfig(**training),
        local=LocalConfig(context_window=16, embedding_dim=24, hidden_dim=128),
    )


def test_real_training_reduces_loss_and_memorizes(workdir) -> None:
    config = _local_config()
    backend = LocalBackend(config)
    backend.start("t", Path("ckpts_parent"))
    examples = load_train_examples(config.data, 7)

    first_loss = None
    last = None
    for step in range(config.training.steps):
        start = (step * 8) % len(examples)
        batch = [examples[(start + o) % len(examples)] for o in range(8)]
        last = backend.train_step(step, batch, 0.03)
        if first_loss is None:
            first_loss = last.loss

    assert last.loss < first_loss * 0.2, "real training must reduce loss substantially"
    # The model genuinely memorized: greedy sampling recovers trained strings.
    recovered = sum(
        1 for ex in examples[:8] if backend.sample(ex.prompt, 16) == ex.completion
    )
    assert recovered >= 6


def test_determinism_same_seed_same_losses(workdir) -> None:
    def losses() -> list[float]:
        config = _local_config(steps=20)
        backend = LocalBackend(config)
        backend.start("t")
        examples = load_train_examples(config.data, 7)
        out = []
        for step in range(20):
            batch = [examples[(step * 8 + o) % len(examples)] for o in range(8)]
            out.append(backend.train_step(step, batch, 0.03).loss)
        return out

    assert losses() == losses()


def test_high_lr_genuinely_diverges(workdir) -> None:
    config = _local_config(steps=40, learning_rate=5.0)
    backend = LocalBackend(config)
    backend.start("t")
    examples = load_train_examples(config.data, 7)
    losses = []
    for step in range(40):
        batch = [examples[(step * 8 + o) % len(examples)] for o in range(8)]
        losses.append(backend.train_step(step, batch, 5.0).loss)
    finite = [loss for loss in losses if math.isfinite(loss)]
    # Real divergence: the tail never recovers to anywhere near the start.
    assert sum(finite[-3:]) / 3 > finite[0] * 1.5


def test_checkpoints_are_real_weight_files(workdir) -> None:
    run_dir = execute_run(_local_config(steps=60))
    artifacts = RunStore().load(run_dir)
    summary = artifacts.summary
    assert summary["status"] == "completed"
    assert summary["backend"] == "local"

    assert artifacts.checkpoints, "local runs must save checkpoints"
    for row in artifacts.checkpoints:
        path = Path(row["path"])
        assert path.exists() and path.suffix == ".npz"
        assert path.stat().st_size > 1000

    # Sampling from an on-disk checkpoint works after training moved on.
    rows = [json.loads(line) for line in (run_dir / "evals.jsonl").read_text().splitlines()]
    bits = [row["score"] for row in rows if row["name"] == "bits_recovered"]
    assert bits[-1] > bits[0], "memorization must improve across checkpoints"


def test_local_backend_rejects_rl_methods() -> None:
    config = make_config(mode="local")
    config.training.method = "rl_terminal_reward"
    with pytest.raises(BackendError, match="sft"):
        LocalBackend(config)


def test_shipped_local_config_end_to_end(workdir, capsys) -> None:
    import shutil

    from tests.conftest import CONFIGS_DIR
    from tinker_workbench.cli import main

    config_path = workdir / "memorization_local.yaml"
    shutil.copy(CONFIGS_DIR / "memorization_local.yaml", config_path)
    assert main(["run", str(config_path), "--quiet"]) == 0
    capsys.readouterr()
    assert main(["doctor", "latest"]) == 0
    out = capsys.readouterr().out
    assert "CRITICAL" not in out