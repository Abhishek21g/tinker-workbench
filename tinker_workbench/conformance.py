from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, Protocol

from tinker_workbench.errors import WorkbenchError

Message = dict[str, str]  # {"role": ..., "content": ...}
Conversation = list[Message]


class Renderer(Protocol):
    """Anything that turns a conversation into token ids for a model."""

    name: str

    def render(self, conversation: Conversation) -> list[int]: ...

    def decode(self, tokens: list[int]) -> str: ...


# Probe conversations chosen to surface the renderer failure modes seen in the
# wild in the Tinker ecosystem: role markers leaking into content (the
# tinker-cookbook#796 class), unicode, whitespace sensitivity, control-token
# strings appearing inside user content, and multi-turn structure.
PROBE_CORPUS: list[tuple[str, Conversation]] = [
    (
        "basic_single_turn",
        [
            {"role": "user", "content": "What is 2+2?"},
            {"role": "assistant", "content": "4."},
        ],
    ),
    (
        "system_prompt",
        [
            {"role": "system", "content": "You are a terse math assistant."},
            {"role": "user", "content": "Compute 17*3."},
            {"role": "assistant", "content": "51"},
        ],
    ),
    (
        "multi_turn",
        [
            {"role": "user", "content": "Name a prime."},
            {"role": "assistant", "content": "7"},
            {"role": "user", "content": "Another one?"},
            {"role": "assistant", "content": "11"},
        ],
    ),
    (
        "role_marker_in_content",
        [
            {"role": "user", "content": "Translate this transcript:\nUser: hello\nAssistant: hi"},
            {"role": "assistant", "content": "Done."},
        ],
    ),
    (
        "control_tokens_in_content",
        [
            {"role": "user", "content": "What does <|im_end|> or </s> mean in a template?"},
            {"role": "assistant", "content": "They are end-of-segment markers."},
        ],
    ),
    (
        "unicode_and_emoji",
        [
            {"role": "user", "content": "Résumé — 数学 🙂 ¿cómo estás?"},
            {"role": "assistant", "content": "Bien, merci — 谢谢 🙂"},
        ],
    ),
    (
        "whitespace_sensitivity",
        [
            {"role": "user", "content": "  leading spaces\nand\n\nblank lines\ttabs  "},
            {"role": "assistant", "content": "Preserved."},
        ],
    ),
    (
        "empty_system",
        [
            {"role": "system", "content": ""},
            {"role": "user", "content": "Hi"},
            {"role": "assistant", "content": "Hello!"},
        ],
    ),
]


@dataclass(frozen=True)
class CaseResult:
    case: str
    match: bool
    first_divergence: int | None = None  # token index
    detail: str = ""


@dataclass
class ConformanceReport:
    renderer_a: str
    renderer_b: str
    cases: list[CaseResult] = field(default_factory=list)

    @property
    def match_rate(self) -> float:
        if not self.cases:
            return 0.0
        return sum(1 for case in self.cases if case.match) / len(self.cases)

    @property
    def conformant(self) -> bool:
        return all(case.match for case in self.cases)

    def to_dict(self) -> dict[str, Any]:
        return {
            "renderer_a": self.renderer_a,
            "renderer_b": self.renderer_b,
            "conformant": self.conformant,
            "match_rate": round(self.match_rate, 4),
            "cases": [
                {
                    "case": case.case,
                    "match": case.match,
                    "first_divergence": case.first_divergence,
                    "detail": case.detail,
                }
                for case in self.cases
            ],
        }


def compare_renderers(
    renderer_a: Renderer,
    renderer_b: Renderer,
    corpus: list[tuple[str, Conversation]] | None = None,
) -> ConformanceReport:
    """Token-exact comparison of two renderers over the probe corpus.

    The check is deliberately exact: 'close enough' tokenization is precisely
    the failure mode that silently corrupts distillation (teacher logprobs are
    computed on tokens the student never sees) and makes recipes
    unreproducible.
    """
    report = ConformanceReport(renderer_a=renderer_a.name, renderer_b=renderer_b.name)
    for case_name, conversation in corpus or PROBE_CORPUS:
        tokens_a = renderer_a.render(conversation)
        tokens_b = renderer_b.render(conversation)
        if tokens_a == tokens_b:
            report.cases.append(CaseResult(case=case_name, match=True))
            continue
        divergence = _first_divergence(tokens_a, tokens_b)
        context_a = renderer_a.decode(tokens_a[max(divergence - 8, 0) : divergence + 8])
        context_b = renderer_b.decode(tokens_b[max(divergence - 8, 0) : divergence + 8])
        report.cases.append(
            CaseResult(
                case=case_name,
                match=False,
                first_divergence=divergence,
                detail=(
                    f"lengths {len(tokens_a)} vs {len(tokens_b)}; "
                    f"around divergence: {context_a!r} vs {context_b!r}"
                ),
            )
        )
    return report


def preflight_distillation(student: Renderer, teacher: Renderer) -> ConformanceReport:
    """Student/teacher renderer compatibility gate for distillation runs.

    Run this before spending tokens: a non-conformant pair reproduces the
    tinker-cookbook#796 failure (loss looks plausible, results are garbage).
    """
    return compare_renderers(student, teacher)


def _first_divergence(tokens_a: list[int], tokens_b: list[int]) -> int:
    for index, (a, b) in enumerate(zip(tokens_a, tokens_b, strict=False)):
        if a != b:
            return index
    return min(len(tokens_a), len(tokens_b))


class CallableRenderer:
    """Adapter for plain functions; used in tests and custom pipelines."""

    def __init__(
        self,
        name: str,
        render_fn: Callable[[Conversation], list[int]],
        decode_fn: Callable[[list[int]], str] | None = None,
    ) -> None:
        self.name = name
        self._render_fn = render_fn
        self._decode_fn = decode_fn or (lambda tokens: str(tokens))

    def render(self, conversation: Conversation) -> list[int]:
        return self._render_fn(conversation)

    def decode(self, tokens: list[int]) -> str:
        return self._decode_fn(tokens)


class HFChatTemplateRenderer:
    """Renderer backed by a HuggingFace tokenizer's chat template.

    Requires `transformers`; loaded lazily so the core package stays
    dependency-free.
    """

    def __init__(self, model_name: str) -> None:
        try:
            from transformers import AutoTokenizer
        except ImportError as error:
            raise WorkbenchError(
                "HFChatTemplateRenderer requires transformers: pip install transformers"
            ) from error
        self.name = f"hf:{model_name}"
        self._tokenizer = AutoTokenizer.from_pretrained(model_name)

    def render(self, conversation: Conversation) -> list[int]:
        return self._tokenizer.apply_chat_template(conversation, tokenize=True)

    def decode(self, tokens: list[int]) -> str:
        return self._tokenizer.decode(tokens)


class CookbookRenderer:
    """Renderer backed by tinker_cookbook.renderers, when installed.

    This is the pairing that matters for real Tinker runs: compare the
    cookbook renderer used in training against the HF chat template used
    everywhere else.
    """

    def __init__(self, renderer_name: str, model_name: str) -> None:
        try:
            from tinker_cookbook import renderers
            from tinker_cookbook.tokenizer_utils import get_tokenizer
        except ImportError as error:
            raise WorkbenchError(
                "CookbookRenderer requires tinker-cookbook: "
                "pip install git+https://github.com/thinking-machines-lab/tinker-cookbook"
            ) from error
        self.name = f"cookbook:{renderer_name}"
        self._tokenizer = get_tokenizer(model_name)
        self._renderer = renderers.get_renderer(renderer_name, self._tokenizer)

    def render(self, conversation: Conversation) -> list[int]:
        tokens, _weights = self._renderer.build_supervised_example(
            [dict(message) for message in conversation]
        )
        return list(tokens)

    def decode(self, tokens: list[int]) -> str:
        return self._tokenizer.decode(tokens)
