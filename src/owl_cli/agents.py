from __future__ import annotations

import os
import re
import time
from dataclasses import dataclass
from typing import Any

from .constants import STATUS_IDLE, STATUS_OFFLINE, STATUS_ONLINE, STATUS_UNKNOWN
from .errors import OwlError
from .store import Store
from .utils import parse_time, utc_now

OWL_NAME_ENV_VAR = "OWL_NAME"
GLOBAL_AGENT_NAME = "global"


@dataclass(frozen=True)
class AgentRef:
    name: str
    key: str


def normalize_name(name: str) -> str:
    key = re.sub(r"[^a-z0-9]+", "-", name.strip().lower()).strip("-")
    if not key:
        raise OwlError("invalid agent name")
    return key


def make_ref(name: str) -> AgentRef:
    display_name = name.strip()
    key = normalize_name(display_name)
    if key == GLOBAL_AGENT_NAME and display_name != GLOBAL_AGENT_NAME:
        raise OwlError("global is reserved; unset OWL_NAME or set OWL_NAME=global to use it")
    return AgentRef(name=display_name, key=key)


def resolve_name(explicit: str | None = None) -> AgentRef:
    if explicit is not None:
        value = explicit
    else:
        env_value = os.environ.get(OWL_NAME_ENV_VAR)
        if env_value is None:
            value = GLOBAL_AGENT_NAME
        elif not env_value.strip():
            raise OwlError("OWL_NAME cannot be empty; unset it to use global")
        else:
            value = env_value
    return make_ref(value)


def touch_state(store: Store, ref: AgentRef) -> dict[str, Any]:
    now = utc_now()
    state = {
        "name": ref.name,
        "key": ref.key,
        "last_seen_at": now,
        "updated_at": now,
    }
    with store.lock(f"state-{ref.key}"):
        store.write_json(store.state_path(ref.key), state)
    return state


def load_state(store: Store, ref: AgentRef) -> dict[str, Any] | None:
    with store.lock(f"state-{ref.key}"):
        return store.read_json(store.state_path(ref.key), None)


def list_states(store: Store) -> list[dict[str, Any]]:
    store.ensure_base()
    rows: list[dict[str, Any]] = []
    for path in sorted((store.home / "state" / "agents").glob("*.json")):
        if path.name.endswith(".watch.json"):
            continue
        state = store.read_json(path, None)
        key = path.stem
        if isinstance(state, dict):
            name = state.get("name")
            rows.append(
                {
                    "key": key,
                    "name": name if isinstance(name, str) else key,
                    "state": state,
                }
            )
        else:
            rows.append({"key": key, "name": key, "state": None})
    return rows


def status_for_state(state: dict[str, Any] | None, threshold: int) -> str:
    if not state:
        return STATUS_UNKNOWN
    last_seen = parse_time(state.get("last_seen_at"))
    if not last_seen:
        return STATUS_UNKNOWN
    age = time.time() - last_seen
    if age <= threshold:
        return STATUS_ONLINE
    if age <= threshold * 2:
        return STATUS_IDLE
    return STATUS_OFFLINE
