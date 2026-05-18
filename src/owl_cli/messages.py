from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any

from .agents import AgentRef, make_ref, touch_state
from .constants import EVENT_MESSAGE, EVENT_READ, ROLE_CC, ROLE_TO
from .errors import OwlError
from .store import Store
from .utils import preview, utc_now
from .watchers import notify_watchers


def message_events(store: Store) -> list[dict[str, Any]]:
    with store.lock("messages"):
        return store.read_jsonl(store.messages_path)


def append_message_event(store: Store, event: dict[str, Any]) -> None:
    with store.lock("messages"):
        store.append_jsonl(store.messages_path, event)


@dataclass(frozen=True)
class MailboxSummary:
    messages: list[dict[str, Any]]
    reads: set[tuple[str, str]]

    def message_by_id(self, message_id: str) -> dict[str, Any] | None:
        for message in reversed(self.messages):
            if message.get("id") == message_id:
                return message
        return None

    def is_read(self, message_id: object, reader: str) -> bool:
        return isinstance(message_id, str) and (message_id, reader) in self.reads

    def unread_count(self, ref: AgentRef) -> int:
        messages: set[str] = set()
        for message in self.messages:
            if ref.key not in message.get("to", []) and ref.key not in message.get("cc", []):
                continue
            message_id = message.get("id")
            if isinstance(message_id, str):
                messages.add(message_id)
        reads = {message_id for message_id, reader in self.reads if reader == ref.key}
        return len(messages - reads)


def mailbox_summary(store: Store) -> MailboxSummary:
    return summarize_messages(message_events(store))


def send_message(
    store: Store,
    sender: AgentRef,
    recipients: list[str],
    cc: list[str],
    body: str,
) -> dict[str, Any]:
    if not any(name.strip() for name in recipients):
        raise OwlError("message requires at least one recipient")
    to_refs = [make_ref(name) for name in recipients]
    cc_refs = [make_ref(name) for name in cc]
    if not body.strip():
        raise OwlError("message body cannot be empty")
    event = {
        "type": EVENT_MESSAGE,
        "id": str(uuid.uuid4()),
        "from": sender.key,
        "from_name": sender.name,
        "to": [ref.key for ref in to_refs],
        "cc": [ref.key for ref in cc_refs],
        "created_at": utc_now(),
        "body": body,
    }
    append_message_event(store, event)
    touch_state(store, sender)
    notify_watchers(store, [ref.key for ref in to_refs + cc_refs])
    return event


def summarize_messages(
    events: list[dict[str, Any]],
) -> MailboxSummary:
    messages = [event for event in events if event.get("type") == EVENT_MESSAGE]
    reads: set[tuple[str, str]] = set()
    for event in events:
        if event.get("type") != EVENT_READ:
            continue
        message_id = event.get("message_id")
        reader = event.get("reader")
        if isinstance(message_id, str) and isinstance(reader, str):
            reads.add((message_id, reader))
    return MailboxSummary(messages, reads)


def inbox_rows(store: Store, ref: AgentRef) -> list[dict[str, Any]]:
    summary = mailbox_summary(store)
    rows: list[dict[str, Any]] = []
    for message in summary.messages:
        to = message.get("to", [])
        cc = message.get("cc", [])
        if ref.key not in to and ref.key not in cc:
            continue
        role = ROLE_TO if ref.key in to else ROLE_CC
        is_read = summary.is_read(message.get("id"), ref.key)
        rows.append(
            {
                "id": message.get("id", ""),
                "status": "read" if is_read else "unread",
                "role": role,
                "from": message.get("from_name") or message.get("from", ""),
                "from_key": message.get("from", ""),
                "created_at": message.get("created_at", ""),
                "preview": preview(message.get("body", "")),
            }
        )
    unread = [row for row in rows if row["status"] == "unread"]
    read = [row for row in rows if row["status"] == "read"]
    unread.sort(key=lambda row: row["created_at"], reverse=True)
    read.sort(key=lambda row: row["created_at"], reverse=True)
    return unread + read


def sent_rows(store: Store, ref: AgentRef) -> list[dict[str, Any]]:
    summary = mailbox_summary(store)
    rows: list[dict[str, Any]] = []
    for message in summary.messages:
        if message.get("from") != ref.key:
            continue
        recipients = list(dict.fromkeys(message.get("to", []) + message.get("cc", [])))
        read_by = [name for name in recipients if summary.is_read(message.get("id"), name)]
        unread_by = [name for name in recipients if not summary.is_read(message.get("id"), name)]
        rows.append(
            {
                "id": message.get("id", ""),
                "to": ",".join(message.get("to", [])),
                "cc": ",".join(message.get("cc", [])),
                "created_at": message.get("created_at", ""),
                "read_by": ",".join(read_by),
                "unread_by": ",".join(unread_by),
                "preview": preview(message.get("body", "")),
                "body": message.get("body", ""),
            }
        )
    rows.sort(key=lambda row: row["created_at"], reverse=True)
    return rows


def read_message(store: Store, ref: AgentRef, message_id: str) -> dict[str, Any]:
    with store.lock("messages"):
        summary = summarize_messages(store.read_jsonl(store.messages_path))
        message = summary.message_by_id(message_id)
        if not message:
            raise OwlError(f"unknown message id: {message_id}")
        if ref.key not in message.get("to", []) and ref.key not in message.get("cc", []):
            raise OwlError("message is not addressed to this agent")
        if not summary.is_read(message_id, ref.key):
            store.append_jsonl(
                store.messages_path,
                {
                    "type": EVENT_READ,
                    "id": str(uuid.uuid4()),
                    "message_id": message_id,
                    "reader": ref.key,
                    "read_at": utc_now(),
                },
            )
    touch_state(store, ref)
    return message


def unread_count(store: Store, ref: AgentRef) -> int:
    return mailbox_summary(store).unread_count(ref)
