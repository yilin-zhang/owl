from __future__ import annotations

import os
import select
import signal
import socket
import subprocess
import time
import uuid
from pathlib import Path
from typing import Any

from .agents import AgentRef, make_ref, touch_state
from .constants import EVENT_MESSAGE, EVENT_READ, ROLE_CC, ROLE_TO
from .errors import OwlError
from .store import Store
from .utils import preview, utc_now


def message_events(store: Store) -> list[dict[str, Any]]:
    with store.lock("messages"):
        return store.read_jsonl(store.messages_path)


def append_message_event(store: Store, event: dict[str, Any]) -> None:
    with store.lock("messages"):
        store.append_jsonl(store.messages_path, event)


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
) -> tuple[list[dict[str, Any]], set[tuple[str, str]]]:
    messages = [event for event in events if event.get("type") == EVENT_MESSAGE]
    reads: set[tuple[str, str]] = set()
    for event in events:
        if event.get("type") != EVENT_READ:
            continue
        message_id = event.get("message_id")
        reader = event.get("reader")
        if isinstance(message_id, str) and isinstance(reader, str):
            reads.add((message_id, reader))
    return messages, reads


def inbox_rows(store: Store, ref: AgentRef) -> list[dict[str, Any]]:
    messages, reads = summarize_messages(message_events(store))
    rows: list[dict[str, Any]] = []
    for message in messages:
        to = message.get("to", [])
        cc = message.get("cc", [])
        if ref.key not in to and ref.key not in cc:
            continue
        role = ROLE_TO if ref.key in to else ROLE_CC
        is_read = (message.get("id"), ref.key) in reads
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
    messages, reads = summarize_messages(message_events(store))
    rows: list[dict[str, Any]] = []
    for message in messages:
        if message.get("from") != ref.key:
            continue
        recipients = list(dict.fromkeys(message.get("to", []) + message.get("cc", [])))
        read_by = [name for name in recipients if (message.get("id"), name) in reads]
        unread_by = [name for name in recipients if (message.get("id"), name) not in reads]
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
        message = None
        already_read = False
        for event in store.read_jsonl(store.messages_path):
            event_type = event.get("type")
            if event_type == EVENT_MESSAGE and event.get("id") == message_id:
                message = event
            elif (
                event_type == EVENT_READ
                and event.get("message_id") == message_id
                and event.get("reader") == ref.key
            ):
                already_read = True
        if not message:
            raise OwlError(f"unknown message id: {message_id}")
        if ref.key not in message.get("to", []) and ref.key not in message.get("cc", []):
            raise OwlError("message is not addressed to this agent")
        if not already_read:
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
    with store.lock("messages"):
        messages: set[str] = set()
        reads: set[str] = set()
        for event in store.read_jsonl(store.messages_path):
            event_type = event.get("type")
            if event_type == EVENT_MESSAGE and (
                ref.key in event.get("to", []) or ref.key in event.get("cc", [])
            ):
                message_id = event.get("id")
                if isinstance(message_id, str):
                    messages.add(message_id)
            elif event_type == EVENT_READ and event.get("reader") == ref.key:
                message_id = event.get("message_id")
                if isinstance(message_id, str):
                    reads.add(message_id)
        return len(messages - reads)


class MailboxWatcher:
    def __init__(self, store: Store, ref: AgentRef) -> None:
        self.store = store
        self.ref = ref
        self.path = watch_socket_path(store, ref.key)
        self._socket: socket.socket | None = None

    def __enter__(self) -> MailboxWatcher:
        if not hasattr(socket, "AF_UNIX"):
            raise OwlError("message watch requires Unix domain socket support")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        unlink_if_exists(self.path)
        try:
            self._socket = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
            self._socket.bind(str(self.path))
            self._socket.setblocking(False)
        except OSError as exc:
            if self._socket is not None:
                self._socket.close()
                self._socket = None
            raise OwlError(f"failed to start message watcher socket: {exc}") from exc
        return self

    def __exit__(self, _exc_type: object, _exc: object, _tb: object) -> None:
        if self._socket is not None:
            self._socket.close()
            self._socket = None
        unlink_if_exists(self.path)

    def wait(self, timeout: float | None) -> bool:
        if self._socket is None:
            raise OwlError("mailbox watcher is not active")
        ready, _, _ = select.select([self._socket], [], [], timeout)
        if not ready:
            return False
        while True:
            try:
                self._socket.recv(1024)
            except BlockingIOError:
                break
        return True


class WatchRegistration:
    def __init__(self, store: Store, ref: AgentRef) -> None:
        self.store = store
        self.ref = ref
        self.pid = os.getpid()
        self.path = store.home / "state" / "agents" / f"{ref.key}.watch.json"

    def __enter__(self) -> WatchRegistration:
        with self.store.lock(f"watch-{self.ref.key}"):
            prior = self.store.read_json(self.path, None)
            if isinstance(prior, dict):
                prior_pid = prior.get("pid")
                prior_command = prior.get("command")
                if (
                    isinstance(prior_pid, int)
                    and prior_pid != self.pid
                    and watcher_process_matches(prior_pid, prior_command)
                ):
                    stop_process(prior_pid, timeout=1.0)
            unlink_if_exists(watch_socket_path(self.store, self.ref.key))
            self.store.write_json(
                self.path,
                {
                    "agent": self.ref.key,
                    "command": process_command(self.pid),
                    "pid": self.pid,
                    "started_at": utc_now(),
                },
            )
        return self

    def __exit__(self, _exc_type: object, _exc: object, _tb: object) -> None:
        with self.store.lock(f"watch-{self.ref.key}"):
            current = self.store.read_json(self.path, None)
            if isinstance(current, dict) and current.get("pid") == self.pid:
                try:
                    self.path.unlink()
                except FileNotFoundError:
                    pass


def stop_process(pid: int, timeout: float = 0.0, force: bool = False) -> None:
    if pid <= 0:
        return
    if not process_alive(pid):
        return
    try:
        os.kill(pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    if timeout <= 0:
        return
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if not process_alive(pid):
            return
        time.sleep(0.05)
    if force and process_alive(pid):
        try:
            os.kill(pid, signal.SIGKILL)
        except ProcessLookupError:
            pass


def process_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def watcher_process_matches(pid: int, expected_command: object) -> bool:
    if not isinstance(expected_command, str):
        return False
    return process_command(pid) == expected_command


def process_command(pid: int) -> str | None:
    try:
        result = subprocess.run(
            ["ps", "-p", str(pid), "-o", "command="],
            capture_output=True,
            check=False,
            text=True,
            timeout=1.0,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if result.returncode != 0:
        return None
    command = result.stdout.strip()
    return command or None


def watch_socket_path(store: Store, key: str) -> Path:
    return store.home / "state" / "agents" / f"{key}.watch.sock"


def notify_watchers(store: Store, recipient_keys: list[str]) -> None:
    for key in set(recipient_keys):
        path = watch_socket_path(store, key)
        if not path.exists():
            continue
        try:
            with socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM) as notifier:
                notifier.sendto(b"message", str(path))
        except OSError:
            continue


def unlink_if_exists(path: Path) -> None:
    try:
        path.unlink()
    except FileNotFoundError:
        pass
