from __future__ import annotations

import json
import shutil
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from tinker_workbench.errors import RunNotFoundError


@dataclass
class RunArtifacts:
    """Everything a finished (or interrupted) run left on disk."""

    run_dir: Path
    config: dict[str, Any] | None = None
    plan: dict[str, Any] | None = None
    summary: dict[str, Any] | None = None
    metrics: list[dict[str, Any]] = field(default_factory=list)
    checkpoints: list[dict[str, Any]] = field(default_factory=list)
    evals: list[dict[str, Any]] = field(default_factory=list)
    events: list[dict[str, Any]] = field(default_factory=list)


class RunStore:
    """Owns the runs/ directory: run creation, the index, and artifact access."""

    def __init__(self, root: Path = Path("runs")) -> None:
        self.root = root

    def create_run_dir(self, name: str) -> tuple[str, Path]:
        timestamp = datetime.now(tz=UTC).strftime("%Y%m%dT%H%M%SZ")
        run_id = f"{timestamp}-{name}"
        run_dir = self.root / run_id
        counter = 1
        while run_dir.exists():
            run_id = f"{timestamp}-{name}-{counter}"
            run_dir = self.root / run_id
            counter += 1
        run_dir.mkdir(parents=True)
        return run_id, run_dir

    def update_latest(self, run_dir: Path) -> None:
        latest = self.root / "latest"
        if latest.is_symlink():
            latest.unlink()
        elif latest.exists():
            shutil.rmtree(latest)
        latest.symlink_to(run_dir.resolve(), target_is_directory=True)

    def append_index(self, record: dict[str, Any]) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        with (self.root / "index.jsonl").open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record) + "\n")

    def list_runs(self) -> list[dict[str, Any]]:
        index_path = self.root / "index.jsonl"
        if not index_path.exists():
            return []
        records = read_jsonl(index_path)
        # The index row is written once at completion; prefer the live
        # summary.json when present so interrupted runs still show up honestly.
        for record in records:
            summary_path = self.root / record["run_id"] / "summary.json"
            if summary_path.exists():
                record.update(read_json(summary_path))
        return records

    def resolve(self, ref: str | Path) -> Path:
        candidates = [Path(ref), self.root / str(ref)]
        if str(ref) == "latest":
            candidates.insert(0, self.root / "latest")
        for candidate in candidates:
            if candidate.exists() and (candidate / "config.json").exists():
                return candidate.resolve()
        raise RunNotFoundError(
            f"Cannot resolve run {str(ref)!r}. Expected a run directory, a run id under "
            f"{self.root}/, or 'latest'."
        )

    def load(self, ref: str | Path) -> RunArtifacts:
        run_dir = self.resolve(ref)
        return RunArtifacts(
            run_dir=run_dir,
            config=_maybe_json(run_dir / "config.json"),
            plan=_maybe_json(run_dir / "plan.json"),
            summary=_maybe_json(run_dir / "summary.json"),
            metrics=_maybe_jsonl(run_dir / "metrics.jsonl"),
            checkpoints=_maybe_jsonl(run_dir / "checkpoints.jsonl"),
            evals=_maybe_jsonl(run_dir / "evals.jsonl"),
            events=_maybe_jsonl(run_dir / "events.jsonl"),
        )


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def append_jsonl(path: Path, row: dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row) + "\n")


def _maybe_json(path: Path) -> dict[str, Any] | None:
    return read_json(path) if path.exists() else None


def _maybe_jsonl(path: Path) -> list[dict[str, Any]]:
    return read_jsonl(path) if path.exists() else []
