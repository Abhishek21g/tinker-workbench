from __future__ import annotations

from tinker_workbench.conformance import (
    PROBE_CORPUS,
    CallableRenderer,
    Conversation,
    compare_renderers,
    preflight_distillation,
)


def _chatml_like(conversation: Conversation) -> list[int]:
    text = ""
    for message in conversation:
        text += f"<|start|>{message['role']}\n{message['content']}<|end|>\n"
    return [ord(ch) for ch in text]


def _role_colon(conversation: Conversation) -> list[int]:
    text = ""
    for message in conversation:
        text += f"{message['role'].capitalize()}: {message['content']}\n\n"
    return [ord(ch) for ch in text]


def _decode(tokens: list[int]) -> str:
    return "".join(chr(token) for token in tokens)


def test_identical_renderers_conform() -> None:
    a = CallableRenderer("a", _chatml_like, _decode)
    b = CallableRenderer("b", _chatml_like, _decode)
    report = compare_renderers(a, b)
    assert report.conformant
    assert report.match_rate == 1.0
    assert len(report.cases) == len(PROBE_CORPUS)


def test_mismatched_renderers_fail_with_divergence_detail() -> None:
    # The tinker-cookbook#796 pairing: a chat-template renderer vs role_colon.
    student = CallableRenderer("student:role_colon", _role_colon, _decode)
    teacher = CallableRenderer("teacher:chatml", _chatml_like, _decode)
    report = preflight_distillation(student, teacher)

    assert not report.conformant
    failed = [case for case in report.cases if not case.match]
    assert failed
    assert all(case.first_divergence is not None for case in failed)
    assert any("vs" in case.detail for case in failed)


def test_role_marker_case_catches_content_collision() -> None:
    # role_colon cannot distinguish "User:" inside content from a real role
    # marker; the probe corpus must include a case exposing that ambiguity.
    names = [name for name, _ in PROBE_CORPUS]
    assert "role_marker_in_content" in names
    case = next(conv for name, conv in PROBE_CORPUS if name == "role_marker_in_content")
    assert "User:" in case[0]["content"]


def test_report_dict_shape() -> None:
    a = CallableRenderer("a", _chatml_like, _decode)
    b = CallableRenderer("b", _role_colon, _decode)
    payload = compare_renderers(a, b).to_dict()
    assert payload["renderer_a"] == "a"
    assert payload["conformant"] is False
    assert 0.0 <= payload["match_rate"] <= 1.0
    assert all({"case", "match"} <= set(case) for case in payload["cases"])
