from __future__ import annotations

import contextlib
import fcntl
import json
import os
from pathlib import Path
from typing import Any, Iterator

from .errors import OwlError

OWL_HOME_ENV_VAR = "OWL_HOME"
OWL_PROJECT_ROOT_ENV_VAR = "OWL_PROJECT_ROOT"


class Store:
    def __init__(self, home: Path | None = None) -> None:
        self.home = home or project_home()
        self._base_ready = False

    @property
    def agents_path(self) -> Path:
        return self.home / "agents.json"

    @property
    def messages_path(self) -> Path:
        return self.home / "messages" / "messages.jsonl"

    def memory_path(self, key: str) -> Path:
        return self.home / "memories" / f"{key}.jsonl"

    def state_path(self, key: str) -> Path:
        return self.home / "state" / "agents" / f"{key}.json"

    def lock_path(self, name: str) -> Path:
        return self.home / ".locks" / f"{name}.lock"

    def ensure_base(self) -> None:
        if self._base_ready:
            return
        for path in [
            self.home,
            self.home / ".locks",
            self.home / "memories",
            self.home / "messages",
            self.home / "state" / "agents",
            self.home / "spells",
        ]:
            path.mkdir(parents=True, exist_ok=True)
        self._base_ready = True

    @contextlib.contextmanager
    def lock(self, name: str) -> Iterator[None]:
        self.ensure_base()
        path = self.lock_path(name)
        with path.open("a", encoding="utf-8") as handle:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)

    def read_json(self, path: Path, default: Any) -> Any:
        try:
            with path.open("r", encoding="utf-8") as handle:
                return json.load(handle)
        except FileNotFoundError:
            return default

    def write_json(self, path: Path, data: Any) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".tmp")
        with tmp.open("w", encoding="utf-8") as handle:
            handle.write(json_text(data))
            handle.flush()
            os.fsync(handle.fileno())
        tmp.replace(path)

    def read_jsonl(self, path: Path) -> list[dict[str, Any]]:
        events: list[dict[str, Any]] = []
        try:
            handle = path.open("r", encoding="utf-8")
        except FileNotFoundError:
            return []
        with handle:
            for line_number, line in enumerate(handle, start=1):
                event = parse_jsonl_line(path, line_number, line)
                if event is not None:
                    events.append(event)
        return events

    def append_jsonl(self, path: Path, event: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json_line(event))
            handle.flush()
            os.fsync(handle.fileno())


def json_text(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def json_line(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, sort_keys=True) + "\n"


def project_root() -> Path:
    env_value = os.environ.get(OWL_PROJECT_ROOT_ENV_VAR)
    if env_value is None:
        return Path.cwd()
    return Path(env_value).expanduser()


def project_home() -> Path:
    return project_root() / ".owl"


def user_home() -> Path:
    env_value = os.environ.get(OWL_HOME_ENV_VAR)
    if env_value is None:
        return Path.home() / ".owl"
    return Path(env_value).expanduser()


def parse_jsonl_line(path: Path, line_number: int, line: str) -> dict[str, Any] | None:
    stripped = line.strip()
    if not stripped:
        return None
    try:
        event = json.loads(stripped)
    except json.JSONDecodeError as exc:
        raise OwlError(f"invalid JSONL in {path} line {line_number}: {exc}") from exc
    if not isinstance(event, dict):
        raise OwlError(f"invalid JSONL in {path} line {line_number}: expected object")
    return event
