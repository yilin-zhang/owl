from __future__ import annotations

import json
import os
from pathlib import Path

from tests.helpers import CliRunner


def test_malformed_jsonl_and_state_are_controlled(cli: CliRunner) -> None:
    messages = Path(cli.home) / "messages" / "messages.jsonl"
    messages.parent.mkdir(parents=True)
    messages.write_text('"not an object"\n')

    os.environ["OWL_NAME"] = "Sarah"
    code, _stdout, stderr = cli.run("message", "inbox")
    assert code == 1
    assert "expected object" in stderr

    state = Path(cli.home) / "state" / "agents" / "sarah.json"
    state.parent.mkdir(parents=True, exist_ok=True)
    state.write_text('{"last_seen_at": "not-a-date"}\n')

    code, stdout, stderr = cli.run("message", "status", "--format", "json")
    assert code == 0, stderr
    assert json.loads(stdout)[0]["status"] == "unknown"
