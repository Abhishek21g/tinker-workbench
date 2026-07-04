from __future__ import annotations

from pathlib import Path
from typing import Any


def load_config(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    if path.suffix == ".json":
        import json

        loaded = json.loads(text)
    else:
        loaded = _load_simple_yaml(text)
    if not isinstance(loaded, dict):
        raise ValueError(f"Config must be a mapping: {path}")
    if "name" not in loaded:
        raise ValueError("Config must include a name.")
    return loaded


def _load_simple_yaml(text: str) -> dict[str, Any]:
    """Parse the small YAML subset used by workbench configs.

    This keeps the first CLI slice runnable on a bare Python install. If the
    config format grows, we can switch back to PyYAML behind the same function.
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
                raise ValueError(f"List item without key: {raw_line}")
            pending_indent, key, parent = pending_key
            if indent <= pending_indent:
                raise ValueError(f"List item has invalid indentation: {raw_line}")
            existing = parent.get(key)
            if existing is None or existing == {}:
                existing = []
                parent[key] = existing
                stack.append((indent, existing))
            if not isinstance(existing, list):
                raise ValueError(f"Key is not a list: {key}")
            existing.append(_parse_scalar(line[2:].strip()))
            continue

        key, separator, value = line.partition(":")
        if not separator:
            raise ValueError(f"Expected key/value line: {raw_line}")
        key = key.strip()
        value = value.strip()
        parent = stack[-1][1]
        if not isinstance(parent, dict):
            raise ValueError(f"Cannot assign key under list: {raw_line}")

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
    try:
        return int(value)
    except ValueError:
        pass
    try:
        return float(value)
    except ValueError:
        pass
    return value
