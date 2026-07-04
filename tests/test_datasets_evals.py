from __future__ import annotations

import json

import pytest

from tests.conftest import make_config
from tinker_workbench.config import DataConfig
from tinker_workbench.datasets import load_eval_examples, load_train_examples
from tinker_workbench.errors import ConfigError, WorkbenchError
from tinker_workbench.evals import grade


def test_memorization_dataset_deterministic() -> None:
    data = make_config().data
    first = load_train_examples(data, seed=11)
    second = load_train_examples(data, seed=11)
    assert first == second
    assert len(first) == data.train_examples
    assert all(set(example.completion) <= {"0", "1"} for example in first)


def test_eval_set_is_subset_of_train() -> None:
    data = make_config().data
    train = set(load_train_examples(data, seed=11))
    evals = load_eval_examples(data, seed=11)
    assert len(evals) == data.eval_examples
    assert all(example in train for example in evals)


def test_jsonl_dataset(tmp_path) -> None:
    path = tmp_path / "data.jsonl"
    rows = [{"prompt": f"q{i}", "completion": f"a{i}"} for i in range(6)]
    path.write_text("\n".join(json.dumps(row) for row in rows), encoding="utf-8")
    data = DataConfig(source=str(path), train_examples=4, eval_examples=2)
    train = load_train_examples(data, seed=0)
    assert [example.prompt for example in train] == ["q0", "q1", "q2", "q3"]


def test_jsonl_missing_keys_rejected(tmp_path) -> None:
    path = tmp_path / "bad.jsonl"
    path.write_text(json.dumps({"prompt": "q"}), encoding="utf-8")
    data = DataConfig(source=str(path))
    with pytest.raises(ConfigError, match="completion"):
        load_train_examples(data, seed=0)


def test_unknown_builtin_rejected() -> None:
    data = DataConfig(source="builtin:nope")
    with pytest.raises(ConfigError, match="Unknown builtin"):
        load_train_examples(data, seed=0)


def test_graders() -> None:
    assert grade("exact_match", " 0101 ", "0101") == 1.0
    assert grade("exact_match", "0100", "0101") == 0.0
    assert grade("contains", "the answer is 42.", "42") == 1.0
    assert grade("contains", "no idea", "42") == 0.0
    assert grade("regex", "final: 42", r"final:\s*\d+") == 1.0
    assert grade("bits_recovered", "0111", "0101") == 0.75
    assert grade("bits_recovered", "01", "0101") == 0.5


def test_unknown_grader_rejected() -> None:
    with pytest.raises(WorkbenchError, match="grader"):
        grade("vibes", "a", "b")
