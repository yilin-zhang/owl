from __future__ import annotations

import json
import os
import signal
import socket
import subprocess
import sys
import time
import uuid
from pathlib import Path

import pytest

from owl_cli.constants import EVENT_MESSAGE
from owl_cli.messages import append_message_event
from owl_cli.store import Store
from owl_cli.utils import utc_now
from tests.helpers import CliRunner


@pytest.mark.skipif(
    not hasattr(socket, "AF_UNIX"), reason="event-driven watch requires Unix sockets"
)
def test_watch_and_status(cli: CliRunner) -> None:
    os.environ["OWL_NAME"] = "Sarah"
    code, stdout, stderr = cli.run(
        "messages",
        "watch",
        "--timeout",
        "0.01",
    )
    assert code == 0, stderr
    assert stdout == ""

    code, stdout, stderr = cli.run("messages", "status", "--format", "json")
    assert code == 0, stderr
    assert json.loads(stdout)[0]["status"] == "online"

    code, stdout, stderr = cli.run(
        "messages",
        "watch",
        "--timeout",
        "0",
    )
    assert code == 0, stderr
    assert stdout == ""


@pytest.mark.skipif(
    not hasattr(socket, "AF_UNIX"), reason="event-driven watch requires Unix sockets"
)
def test_watch_exits_on_message_without_waiting_for_pulse_interval(cli: CliRunner) -> None:
    env = os.environ.copy()
    env["OWL_HOME"] = str(cli.user_home)
    env["OWL_PROJECT_ROOT"] = str(cli.project_root)
    env["OWL_NAME"] = "Tom"
    env["PYTHONPATH"] = str(cli.repo_root / "src")
    started = time.monotonic()
    proc = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "owl_cli",
            "messages",
            "watch",
            "--timeout",
            "5",
        ],
        cwd=cli.repo_root,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    cli.wait_for_path(Path(cli.home) / "state" / "agents" / "tom.watch.sock")
    os.environ["OWL_NAME"] = "Sarah"
    code, _stdout, stderr = cli.run("messages", "send", "Tom", "wake up")
    assert code == 0, stderr
    stdout, stderr = proc.communicate(timeout=2)
    elapsed = time.monotonic() - started
    assert proc.returncode == 0
    assert stdout == ""
    assert "1 unread message" in stderr
    assert elapsed < 2.5


@pytest.mark.skipif(
    not hasattr(socket, "AF_UNIX"), reason="event-driven watch requires Unix sockets"
)
def test_watch_pulse_exits_when_notification_is_missed(cli: CliRunner) -> None:
    env = os.environ.copy()
    env["OWL_HOME"] = str(cli.user_home)
    env["OWL_PROJECT_ROOT"] = str(cli.project_root)
    env["OWL_NAME"] = "Tom"
    env["PYTHONPATH"] = str(cli.repo_root / "src")
    proc = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "owl_cli",
            "messages",
            "watch",
            "--interval",
            "0.1",
            "--timeout",
            "5",
            "--format",
            "json",
        ],
        cwd=cli.repo_root,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    cli.wait_for_path(Path(cli.home) / "state" / "agents" / "tom.watch.sock")
    append_message_event(
        Store(Path(cli.home)),
        {
            "type": EVENT_MESSAGE,
            "id": str(uuid.uuid4()),
            "from": "sarah",
            "from_name": "Sarah",
            "to": ["tom"],
            "cc": [],
            "created_at": utc_now(),
            "body": "missed notification",
        },
    )
    stdout, stderr = proc.communicate(timeout=2)
    assert proc.returncode == 0, stderr
    assert json.loads(stdout) == {"agent": "tom", "event": "message", "unread": 1}


@pytest.mark.skipif(
    not hasattr(socket, "AF_UNIX"), reason="event-driven watch requires Unix sockets"
)
def test_watch_replaces_existing_watcher_for_same_agent(cli: CliRunner) -> None:
    env = os.environ.copy()
    env["OWL_HOME"] = str(cli.user_home)
    env["OWL_PROJECT_ROOT"] = str(cli.project_root)
    env["OWL_NAME"] = "Tom"
    env["PYTHONPATH"] = str(cli.repo_root / "src")
    first = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "owl_cli",
            "messages",
            "watch",
            "--timeout",
            "30",
        ],
        cwd=cli.repo_root,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    cli.wait_for_path(Path(cli.home) / "state" / "agents" / "tom.watch.sock")

    second = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "owl_cli",
            "messages",
            "watch",
            "--timeout",
            "0.01",
        ],
        cwd=cli.repo_root,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    second_stdout, second_stderr = second.communicate(timeout=2)
    assert second.returncode == 0, second_stderr
    assert second_stdout == ""

    first_stdout, first_stderr = first.communicate(timeout=2)
    assert first_stdout == ""
    assert first_stderr == ""
    assert first.returncode == -signal.SIGTERM
