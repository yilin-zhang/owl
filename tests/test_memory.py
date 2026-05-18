from __future__ import annotations

import json
import os
from pathlib import Path

from tests.helpers import CliRunner


def test_memory_compact_is_append_only_effective_state(cli: CliRunner) -> None:
    os.environ["OWL_NAME"] = "Sarah"
    assert cli.run("memory", "write", "old")[0] == 0
    assert cli.run("memory", "compact", "summary")[0] == 0
    assert cli.run("memory", "write", "new")[0] == 0

    code, stdout, stderr = cli.run("memory", "show")
    assert code == 0, stderr
    assert stdout.strip().splitlines() == ["summary", "new"]

    events = (Path(cli.home) / "memories" / "sarah.jsonl").read_text().splitlines()
    assert [json.loads(line)["type"] for line in events] == ["memory", "compact", "memory"]


def test_memory_visibility_includes_global_scope(cli: CliRunner) -> None:
    assert cli.run("memory", "write", "global-old")[0] == 0
    assert cli.run("memory", "compact", "global-summary")[0] == 0
    assert cli.run("memory", "write", "global-new")[0] == 0

    os.environ["OWL_NAME"] = "Sarah"
    assert cli.run("memory", "write", "sarah-old")[0] == 0
    assert cli.run("memory", "compact", "sarah-summary")[0] == 0
    assert cli.run("memory", "write", "sarah-new")[0] == 0

    os.environ["OWL_NAME"] = "Tom"
    assert cli.run("memory", "write", "tom-note")[0] == 0

    os.environ["OWL_NAME"] = "Sarah"
    code, stdout, stderr = cli.run("memory", "show", "--format", "json")
    assert code == 0, stderr
    sarah_memory = json.loads(stdout)
    assert [event["text"] for event in sarah_memory["effective"]] == [
        "global-summary",
        "global-new",
        "sarah-summary",
        "sarah-new",
    ]
    assert {event["agent"] for event in sarah_memory["events"]} == {"global", "sarah"}

    os.environ.pop("OWL_NAME", None)
    code, stdout, stderr = cli.run("memory", "show", "--format", "json")
    assert code == 0, stderr
    global_memory = json.loads(stdout)
    assert global_memory["agent"] == "global"
    assert {event["text"] for event in global_memory["effective"]} == {
        "global-summary",
        "global-new",
        "sarah-summary",
        "sarah-new",
        "tom-note",
    }
