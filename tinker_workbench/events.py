from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


class EventLog:
    """Append-only structured event log for a run.

    Every lifecycle transition (run start, step, checkpoint, eval, completion,
    failure) is recorded here so `status`, `doctor`, and `report` can
    reconstruct what happened without re-running anything.
    """

    def __init__(self, path: Path) -> None:
        self.path = path

    def emit(self, event_type: str, **payload: Any) -> dict[str, Any]:
        event = {
            "type": event_type,
            "timestamp": datetime.now(tz=UTC).isoformat(),
            **payload,
        }
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event) + "\n")
        return event

    def read(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        with self.path.open("r", encoding="utf-8") as handle:
            return [json.loads(line) for line in handle if line.strip()]
