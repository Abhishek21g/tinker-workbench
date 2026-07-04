from __future__ import annotations

import pytest

from tests.conftest import CONFIGS_DIR
from tinker_workbench.config import ConfigError, load_config, parse_config


def test_loads_all_shipped_configs() -> None:
    configs = sorted(CONFIGS_DIR.glob("*.yaml"))
    assert configs, "expected example configs to ship with the repo"
    for path in configs:
        config = load_config(path)
        assert config.name


def test_memorization_sft_config_values() -> None:
    config = load_config(CONFIGS_DIR / "memorization_sft.yaml")
    assert config.training.method == "sft"
    assert config.data.latent_bits == 10
    assert config.budget.max_train_tokens == 250000
    assert [e.grader for e in config.evals] == ["exact_match", "bits_recovered"]


def test_missing_name_rejected() -> None:
    with pytest.raises(ConfigError, match="name"):
        parse_config({"mode": "mock"})


def test_unknown_top_level_key_rejected() -> None:
    with pytest.raises(ConfigError, match="Unknown top-level"):
        parse_config({"name": "x", "surprise": 1})


def test_unknown_section_key_rejected() -> None:
    with pytest.raises(ConfigError, match="training"):
        parse_config({"name": "x", "training": {"stepz": 10}})


def test_invalid_method_rejected() -> None:
    with pytest.raises(ConfigError, match="training.method"):
        parse_config({"name": "x", "training": {"method": "dpo"}})


def test_invalid_injection_rejected() -> None:
    with pytest.raises(ConfigError, match="mock.inject"):
        parse_config({"name": "x", "mock": {"inject": {"explode_at_step": 3}}})


def test_string_eval_shorthand() -> None:
    config = parse_config({"name": "x", "evals": ["exact_match"]})
    assert config.evals[0].grader == "exact_match"


def test_config_missing_file(tmp_path) -> None:
    with pytest.raises(ConfigError, match="not found"):
        load_config(tmp_path / "nope.yaml")
