from __future__ import annotations

from pathlib import Path

import pytest

from tinker_workbench.config import (
    CheckpointConfig,
    DataConfig,
    EvalConfig,
    ExperimentConfig,
    MockConfig,
    TrainingConfig,
)

REPO_ROOT = Path(__file__).parents[1]
CONFIGS_DIR = REPO_ROOT / "configs"


@pytest.fixture
def workdir(tmp_path, monkeypatch) -> Path:
    """Run each test in an isolated cwd so runs/ and reports/ stay contained."""
    monkeypatch.chdir(tmp_path)
    return tmp_path


def make_config(**overrides) -> ExperimentConfig:
    """Small, fast experiment config for tests."""
    defaults = dict(
        name="test-run",
        mode="mock",
        training=TrainingConfig(steps=12, batch_size=4, learning_rate=1e-4, seed=11),
        data=DataConfig(
            source="builtin:memorization",
            train_examples=16,
            eval_examples=8,
            latent_bits=8,
            avg_tokens_per_example=32,
        ),
        checkpoints=CheckpointConfig(every_steps=4, estimated_gb_each=0.1),
        evals=[
            EvalConfig(name="exact_match", grader="exact_match", num_examples=8,
                       max_sample_tokens=16),
            EvalConfig(name="bits_recovered", grader="bits_recovered", num_examples=8,
                       max_sample_tokens=16),
        ],
        mock=MockConfig(time_constant=4.0),
    )
    defaults.update(overrides)
    config = ExperimentConfig(**defaults)
    config.validate()
    return config
