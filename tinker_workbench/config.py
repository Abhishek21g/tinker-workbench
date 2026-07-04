from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from tinker_workbench.errors import ConfigError

VALID_MODES = ("mock", "local", "tinker")
VALID_METHODS = ("sft", "rl_terminal_reward", "rl_dense_reward")
VALID_SCHEDULES = ("constant", "linear", "cosine")
VALID_GRADERS = ("exact_match", "contains", "regex", "bits_recovered")


@dataclass
class ModelConfig:
    base_model: str = "meta-llama/Llama-3.2-1B"
    lora_rank: int = 32

    def validate(self) -> None:
        if not self.base_model:
            raise ConfigError("model.base_model must be set.")
        if self.lora_rank <= 0:
            raise ConfigError("model.lora_rank must be positive.")


@dataclass
class TrainingConfig:
    method: str = "sft"
    steps: int = 40
    batch_size: int = 8
    learning_rate: float = 1e-4
    lr_schedule: str = "constant"
    seed: int = 0

    def validate(self) -> None:
        if self.method not in VALID_METHODS:
            raise ConfigError(
                f"training.method must be one of {VALID_METHODS}, got {self.method!r}."
            )
        if self.steps <= 0:
            raise ConfigError("training.steps must be positive.")
        if self.batch_size <= 0:
            raise ConfigError("training.batch_size must be positive.")
        if self.learning_rate <= 0:
            raise ConfigError("training.learning_rate must be positive.")
        if self.lr_schedule not in VALID_SCHEDULES:
            raise ConfigError(
                f"training.lr_schedule must be one of {VALID_SCHEDULES}, got {self.lr_schedule!r}."
            )


@dataclass
class DataConfig:
    source: str = "builtin:memorization"
    train_examples: int = 128
    eval_examples: int = 64
    latent_bits: int = 10
    avg_tokens_per_example: int = 48

    def validate(self) -> None:
        if not self.source:
            raise ConfigError("data.source must be set.")
        if not self.source.startswith("builtin:") and not self.source.endswith(".jsonl"):
            raise ConfigError(
                "data.source must be 'builtin:<name>' or a path to a .jsonl file, "
                f"got {self.source!r}."
            )
        if self.train_examples <= 0:
            raise ConfigError("data.train_examples must be positive.")
        if self.eval_examples <= 0:
            raise ConfigError("data.eval_examples must be positive.")
        if self.latent_bits <= 0:
            raise ConfigError("data.latent_bits must be positive.")


@dataclass
class CheckpointConfig:
    every_steps: int = 10
    estimated_gb_each: float = 0.5

    def validate(self) -> None:
        if self.every_steps <= 0:
            raise ConfigError("checkpoints.every_steps must be positive.")
        if self.estimated_gb_each < 0:
            raise ConfigError("checkpoints.estimated_gb_each cannot be negative.")


@dataclass
class EvalConfig:
    name: str = "exact_match"
    grader: str = "exact_match"
    num_examples: int = 32
    max_sample_tokens: int = 64

    def validate(self) -> None:
        if self.grader not in VALID_GRADERS:
            raise ConfigError(
                f"evals[].grader must be one of {VALID_GRADERS}, got {self.grader!r}."
            )
        if self.num_examples <= 0:
            raise ConfigError("evals[].num_examples must be positive.")


@dataclass
class BudgetConfig:
    max_train_tokens: int = 0
    max_sample_tokens: int = 0
    usd_per_1m_train_tokens: float | None = None
    usd_per_1m_sample_tokens: float | None = None
    max_usd: float | None = None

    def validate(self) -> None:
        if self.max_train_tokens < 0 or self.max_sample_tokens < 0:
            raise ConfigError("budget token limits cannot be negative.")


@dataclass
class MockConfig:
    """Controls the deterministic training simulator. Ignored by real backends."""

    initial_loss: float = 4.0
    loss_floor: float = 0.2
    time_constant: float = 12.0
    noise: float = 0.03
    inject: dict[str, int] = field(default_factory=dict)

    VALID_INJECTIONS = ("nan_at_step", "diverge_at_step", "stall_at_step", "spike_at_step")

    def validate(self) -> None:
        if self.initial_loss <= self.loss_floor:
            raise ConfigError("mock.initial_loss must exceed mock.loss_floor.")
        for key in self.inject:
            if key not in self.VALID_INJECTIONS:
                raise ConfigError(
                    f"mock.inject key must be one of {self.VALID_INJECTIONS}, got {key!r}."
                )


@dataclass
class LocalConfig:
    """Architecture of the tiny char-level LM trained by the local backend."""

    context_window: int = 12
    embedding_dim: int = 16
    hidden_dim: int = 64

    def validate(self) -> None:
        if self.context_window <= 0:
            raise ConfigError("local.context_window must be positive.")
        if self.embedding_dim <= 0 or self.hidden_dim <= 0:
            raise ConfigError("local.embedding_dim and local.hidden_dim must be positive.")


@dataclass
class ExperimentConfig:
    name: str
    description: str = ""
    mode: str = "mock"
    model: ModelConfig = field(default_factory=ModelConfig)
    training: TrainingConfig = field(default_factory=TrainingConfig)
    data: DataConfig = field(default_factory=DataConfig)
    checkpoints: CheckpointConfig = field(default_factory=CheckpointConfig)
    evals: list[EvalConfig] = field(default_factory=list)
    budget: BudgetConfig = field(default_factory=BudgetConfig)
    mock: MockConfig = field(default_factory=MockConfig)
    local: LocalConfig = field(default_factory=LocalConfig)

    def validate(self) -> None:
        if not self.name:
            raise ConfigError("Config must include a name.")
        if self.mode not in VALID_MODES:
            raise ConfigError(f"mode must be one of {VALID_MODES}, got {self.mode!r}.")
        self.model.validate()
        self.training.validate()
        self.data.validate()
        self.checkpoints.validate()
        self.budget.validate()
        self.mock.validate()
        self.local.validate()
        for eval_config in self.evals:
            eval_config.validate()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def load_config(path: Path) -> ExperimentConfig:
    if not path.exists():
        raise ConfigError(f"Config file not found: {path}")
    raw = load_raw_config(path)
    return parse_config(raw)


def load_raw_config(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    if path.suffix == ".json":
        loaded = json.loads(text)
    else:
        loaded = _load_yaml(text)
    if not isinstance(loaded, dict):
        raise ConfigError(f"Config must be a mapping: {path}")
    return loaded


def parse_config(raw: dict[str, Any]) -> ExperimentConfig:
    known_top_level = {
        "name",
        "description",
        "mode",
        "model",
        "training",
        "data",
        "checkpoints",
        "evals",
        "budget",
        "mock",
        "local",
    }
    unknown = set(raw) - known_top_level
    if unknown:
        raise ConfigError(f"Unknown top-level config keys: {sorted(unknown)}")
    if "name" not in raw:
        raise ConfigError("Config must include a name.")

    evals_raw = raw.get("evals", [])
    if not isinstance(evals_raw, list):
        raise ConfigError("evals must be a list.")
    evals = []
    for entry in evals_raw:
        if isinstance(entry, str):
            grader = entry if entry in VALID_GRADERS else "exact_match"
            evals.append(EvalConfig(name=entry, grader=grader))
        elif isinstance(entry, dict):
            evals.append(_build_section(EvalConfig, entry, "evals[]"))
        else:
            raise ConfigError(f"evals entries must be strings or mappings, got {entry!r}.")

    config = ExperimentConfig(
        name=str(raw["name"]),
        description=str(raw.get("description", "")),
        mode=str(raw.get("mode", "mock")),
        model=_build_section(ModelConfig, raw.get("model", {}), "model"),
        training=_build_section(TrainingConfig, raw.get("training", {}), "training"),
        data=_build_section(DataConfig, raw.get("data", {}), "data"),
        checkpoints=_build_section(CheckpointConfig, raw.get("checkpoints", {}), "checkpoints"),
        evals=evals,
        budget=_build_section(BudgetConfig, raw.get("budget", {}), "budget"),
        mock=_build_section(MockConfig, raw.get("mock", {}), "mock"),
        local=_build_section(LocalConfig, raw.get("local", {}), "local"),
    )
    config.validate()
    return config


def _build_section(cls: type, raw: Any, section: str):
    if not isinstance(raw, dict):
        raise ConfigError(f"{section} must be a mapping, got {raw!r}.")
    valid_fields = {f for f in cls.__dataclass_fields__}
    unknown = set(raw) - valid_fields
    if unknown:
        raise ConfigError(f"Unknown keys in {section}: {sorted(unknown)}")
    return cls(**raw)


def _load_yaml(text: str) -> Any:
    try:
        import yaml
    except ImportError:
        return _load_simple_yaml(text)
    return yaml.safe_load(text)


def _load_simple_yaml(text: str) -> dict[str, Any]:
    """Parse the small YAML subset used by workbench configs.

    Fallback for environments without PyYAML: nested mappings, lists of
    scalars, and scalar values only.
    """
    root: dict[str, Any] = {}
    stack: list[tuple[int, dict[str, Any] | list[Any]]] = [(-1, root)]
    pending_key: tuple[int, str, dict[str, Any]] | None = None

    for raw_line in text.splitlines():
        if not raw_line.strip() or raw_line.lstrip().startswith("#"):
            continue
        indent = len(raw_line) - len(raw_line.lstrip(" "))
        line = raw_line.strip()

        while stack and indent <= stack[-1][0]:
            stack.pop()

        if line.startswith("- "):
            if pending_key is None:
                raise ConfigError(f"List item without key: {raw_line}")
            pending_indent, key, parent = pending_key
            if indent <= pending_indent:
                raise ConfigError(f"List item has invalid indentation: {raw_line}")
            existing = parent.get(key)
            if existing is None or existing == {}:
                existing = []
                parent[key] = existing
                stack.append((indent, existing))
            if not isinstance(existing, list):
                raise ConfigError(f"Key is not a list: {key}")
            existing.append(_parse_scalar(line[2:].strip()))
            continue

        key, separator, value = line.partition(":")
        if not separator:
            raise ConfigError(f"Expected key/value line: {raw_line}")
        key = key.strip()
        value = value.strip()
        parent = stack[-1][1]
        if not isinstance(parent, dict):
            raise ConfigError(f"Cannot assign key under list: {raw_line}")

        if value:
            parent[key] = _parse_scalar(value)
            pending_key = None
            continue

        child: dict[str, Any] = {}
        parent[key] = child
        pending_key = (indent, key, parent)
        stack.append((indent, child))

    return root


def _parse_scalar(value: str) -> Any:
    lowered = value.lower()
    if lowered in {"true", "false"}:
        return lowered == "true"
    if lowered in {"null", "~"}:
        return None
    try:
        return int(value)
    except ValueError:
        pass
    try:
        return float(value)
    except ValueError:
        pass
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value
