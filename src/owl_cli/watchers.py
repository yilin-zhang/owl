from __future__ import annotations

import os
import select
import signal
import socket
import subprocess
import time
from pathlib import Path

from .agents import AgentRef
from .errors import OwlError
from .store import Store
from .utils import utc_now


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
                unlink_if_exists(self.path)


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
