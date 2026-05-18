from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
from pathlib import Path

import pytest

from owl_cli.utils import utc_now
from tests.helpers import CliRunner


def test_perch_status_is_read_only_when_no_agents_exist(cli: CliRunner) -> None:
    code, stdout, stderr = cli.run("perch", "status", "--format", "json")
    assert code == 0, stderr
    assert json.loads(stdout) == []
    assert not Path(cli.home).exists()


@pytest.mark.skipif(
    not hasattr(socket, "AF_UNIX"), reason="event-driven watch requires Unix sockets"
)
def test_perch_status_combines_state_messages_and_watch(cli: CliRunner) -> None:
    os.environ["OWL_NAME"] = "Sarah"
    code, _stdout, stderr = cli.run("whoami")
    assert code == 0, stderr
    os.environ["OWL_NAME"] = "Lee"
    code, _stdout, stderr = cli.run("whoami")
    assert code == 0, stderr
    os.environ["OWL_NAME"] = "Sarah"
    code, _stdout, stderr = cli.run("message", "send", "Lee", "hello lee")
    assert code == 0, stderr

    memory_path = Path(cli.home) / "memories" / "memory-only.jsonl"
    memory_path.parent.mkdir(parents=True, exist_ok=True)
    memory_path.write_text(
        json.dumps(
            {
                "type": "memory",
                "id": "memory-event",
                "agent": "memory-only",
                "created_at": utc_now(),
                "text": "memory only",
            }
        )
        + "\n",
        encoding="utf-8",
    )

    stale_watch = Path(cli.home) / "state" / "agents" / "ghost.watch.json"
    stale_watch.parent.mkdir(parents=True, exist_ok=True)
    stale_watch.write_text(
        json.dumps(
            {
                "agent": "ghost",
                "command": "missing watcher",
                "pid": 999999,
                "started_at": utc_now(),
            }
        )
        + "\n",
        encoding="utf-8",
    )
    broken_watch = Path(cli.home) / "state" / "agents" / "broken.watch.json"
    broken_watch.write_text("{not-json", encoding="utf-8")

    env = os.environ.copy()
    env["OWL_HOME"] = str(cli.user_home)
    env["OWL_PROJECT_ROOT"] = str(cli.project_root)
    env["OWL_NAME"] = "Tom"
    env["PYTHONPATH"] = str(cli.repo_root / "src")
    watcher = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "owl_cli",
            "message",
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
    try:
        cli.wait_for_path(Path(cli.home) / "state" / "agents" / "tom.watch.sock")
        code, stdout, stderr = cli.run("perch", "status", "--format", "json")
        assert code == 0, stderr
        rows = {row["key"]: row for row in json.loads(stdout)}
        assert rows["sarah"]["presence"] == "online"
        assert rows["lee"]["unread"] == 1
        assert rows["lee"]["newest_unread_from"] == "sarah"
        assert rows["lee"]["newest_unread_preview"] == "hello lee"
        assert rows["tom"]["watch"] == "watching"
        assert rows["tom"]["unread"] == 0
        assert rows["ghost"]["watch"] == "stale"
        assert rows["ghost"]["presence"] == "unknown"
        assert rows["broken"]["watch"] == "stale"
        assert "memory-only" not in rows
    finally:
        watcher.terminate()
        try:
            watcher.communicate(timeout=2)
        except subprocess.TimeoutExpired:
            watcher.kill()
            watcher.communicate(timeout=2)
