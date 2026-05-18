from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .agents import list_states, status_for_state
from .messages import mailbox_summary
from .store import Store
from .utils import preview
from .watchers import process_alive, watch_socket_path, watcher_process_matches

WATCH_NONE = "no-watch"
WATCH_STALE = "stale"
WATCH_WATCHING = "watching"


def perch_rows(store: Store, threshold: int) -> list[dict[str, Any]]:
    inventory = agent_inventory(store)
    message_summaries = summarize_agent_messages(store)
    for key in watch_registration_keys(store):
        inventory.setdefault(key, {"key": key, "name": key, "state": None})

    rows: list[dict[str, Any]] = []
    for key in sorted(inventory):
        agent = inventory[key]
        state = agent.get("state") if isinstance(agent.get("state"), dict) else None
        summary = message_summaries.get(key, {})
        registration = watch_registration(store, key)
        rows.append(
            {
                "key": key,
                "name": agent.get("name") or key,
                "presence": status_for_state(state, threshold),
                "watch": watch_status(store, key, registration),
                "unread": summary.get("unread", 0),
                "last_seen_at": "" if not state else state.get("last_seen_at", ""),
                "watch_started_at": watch_started_at(registration),
                "watcher_pid": watcher_pid(registration),
                "watcher_command": watcher_command(registration),
                "newest_unread_id": summary.get("newest_unread_id", ""),
                "newest_unread_from": summary.get("newest_unread_from", ""),
                "newest_unread_at": summary.get("newest_unread_at", ""),
                "newest_unread_preview": summary.get("newest_unread_preview", ""),
                "latest_inbound_at": summary.get("latest_inbound_at", ""),
                "latest_outbound_at": summary.get("latest_outbound_at", ""),
            }
        )
    return rows


def agent_inventory(store: Store) -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    for state_row in list_states(store):
        rows[state_row["key"]] = state_row
    return rows


def watch_registration_keys(store: Store) -> set[str]:
    store.ensure_base()
    suffix = ".watch.json"
    keys: set[str] = set()
    for path in (store.home / "state" / "agents").glob(f"*{suffix}"):
        keys.add(path.name[: -len(suffix)])
    return keys


def summarize_agent_messages(store: Store) -> dict[str, dict[str, Any]]:
    mailbox = mailbox_summary(store)
    summaries: dict[str, dict[str, Any]] = {}
    for message in mailbox.messages:
        message_id = message.get("id")
        created_at = string_value(message.get("created_at"))
        sender = string_value(message.get("from"))
        if sender:
            summary = agent_message_summary(summaries, sender)
            summary["latest_outbound_at"] = latest_time(
                summary.get("latest_outbound_at", ""), created_at
            )
        recipients = message_recipients(message)
        for recipient in recipients:
            summary = agent_message_summary(summaries, recipient)
            summary["latest_inbound_at"] = latest_time(
                summary.get("latest_inbound_at", ""), created_at
            )
            if isinstance(message_id, str) and not mailbox.is_read(message_id, recipient):
                summary["unread"] = int(summary.get("unread", 0)) + 1
                if created_at >= string_value(summary.get("newest_unread_at")):
                    summary["newest_unread_id"] = message_id
                    summary["newest_unread_from"] = sender
                    summary["newest_unread_at"] = created_at
                    summary["newest_unread_preview"] = preview(string_value(message.get("body")))
    return summaries


def agent_message_summary(summaries: dict[str, dict[str, Any]], key: str) -> dict[str, Any]:
    return summaries.setdefault(
        key,
        {
            "unread": 0,
            "newest_unread_id": "",
            "newest_unread_from": "",
            "newest_unread_at": "",
            "newest_unread_preview": "",
            "latest_inbound_at": "",
            "latest_outbound_at": "",
        },
    )


def message_recipients(message: dict[str, Any]) -> list[str]:
    recipients: list[str] = []
    for field in ["to", "cc"]:
        values = message.get(field, [])
        if isinstance(values, list):
            recipients.extend(value for value in values if isinstance(value, str))
    return list(dict.fromkeys(recipients))


def watch_status(store: Store, key: str, registration: dict[str, Any] | None) -> str:
    if not registration:
        return WATCH_STALE if watch_registration_path(store, key).exists() else WATCH_NONE
    pid = registration.get("pid")
    command = registration.get("command")
    if (
        isinstance(pid, int)
        and process_alive(pid)
        and watcher_process_matches(pid, command)
        and watch_socket_path(store, key).exists()
    ):
        return WATCH_WATCHING
    return WATCH_STALE


def watcher_pid(registration: dict[str, Any] | None) -> int | str:
    if not registration:
        return ""
    pid = registration.get("pid")
    return pid if isinstance(pid, int) else ""


def watcher_command(registration: dict[str, Any] | None) -> str:
    if not registration:
        return ""
    return string_value(registration.get("command"))


def watch_started_at(registration: dict[str, Any] | None) -> str:
    if not registration:
        return ""
    return string_value(registration.get("started_at"))


def watch_registration(store: Store, key: str) -> dict[str, Any] | None:
    try:
        registration = store.read_json(watch_registration_path(store, key), None)
    except json.JSONDecodeError:
        return None
    return registration if isinstance(registration, dict) else None


def watch_registration_path(store: Store, key: str) -> Path:
    return store.home / "state" / "agents" / f"{key}.watch.json"


def latest_time(current: str, candidate: str) -> str:
    if not current:
        return candidate
    return candidate if candidate > current else current


def string_value(value: object) -> str:
    return value if isinstance(value, str) else ""
