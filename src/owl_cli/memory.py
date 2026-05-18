from __future__ import annotations

import uuid
from typing import Any

from .agents import GLOBAL_AGENT_NAME, AgentRef, make_ref, touch_state
from .constants import EVENT_COMPACT, EVENT_MEMORY
from .errors import OwlError
from .store import Store
from .utils import utc_now


def memory_events(store: Store, ref: AgentRef) -> list[dict[str, Any]]:
    with store.lock(f"memory-{ref.key}"):
        return store.read_jsonl(store.memory_path(ref.key))


def visible_memory_events(store: Store, ref: AgentRef) -> list[dict[str, Any]]:
    visible_refs = memory_scope_refs(store, ref)
    events: list[dict[str, Any]] = []
    for visible_ref in visible_refs:
        events.extend(memory_events(store, visible_ref))
    return sorted(events, key=lambda event: event.get("created_at", ""))


def visible_effective_memory(store: Store, ref: AgentRef) -> list[dict[str, Any]]:
    visible_refs = memory_scope_refs(store, ref)
    events: list[dict[str, Any]] = []
    for visible_ref in visible_refs:
        events.extend(effective_memory(memory_events(store, visible_ref)))
    return sorted(events, key=lambda event: event.get("created_at", ""))


def memory_scope_refs(store: Store, ref: AgentRef) -> list[AgentRef]:
    global_ref = make_ref(GLOBAL_AGENT_NAME)
    if ref.key == global_ref.key:
        refs = [make_ref(path.stem) for path in sorted(store.home.glob("memories/*.jsonl"))]
        if all(existing.key != global_ref.key for existing in refs):
            refs.insert(0, global_ref)
        return refs
    return [global_ref, ref]


def append_memory(store: Store, ref: AgentRef, event_type: str, text: str) -> dict[str, Any]:
    if event_type not in {EVENT_MEMORY, EVENT_COMPACT}:
        raise OwlError(f"invalid memory event type: {event_type}")
    event = {
        "type": event_type,
        "id": str(uuid.uuid4()),
        "agent": ref.key,
        "created_at": utc_now(),
        "text": text,
    }
    with store.lock(f"memory-{ref.key}"):
        store.append_jsonl(store.memory_path(ref.key), event)
    touch_state(store, ref)
    return event


def effective_memory(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    start = 0
    for index, event in enumerate(events):
        if event.get("type") == EVENT_COMPACT:
            start = index
    return [event for event in events[start:] if event.get("type") in {EVENT_MEMORY, EVENT_COMPACT}]
