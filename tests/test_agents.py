from __future__ import annotations

import json
import os
from pathlib import Path

from tests.helpers import CliRunner


def test_owl_name_resolves_default_identity(cli: CliRunner) -> None:
    os.environ["OWL_NAME"] = "Sam"
    code, stdout, stderr = cli.run("whoami", "--format", "json")
    assert code == 0, stderr
    assert json.loads(stdout)["key"] == "sam"

    code, stdout, stderr = cli.run("messages", "send", "Tom", "hello", "--format", "json")
    assert code == 0, stderr
    assert json.loads(stdout)["from"] == "sam"


def test_missing_owl_name_defaults_to_root_identity(cli: CliRunner) -> None:
    code, stdout, stderr = cli.run("whoami", "--format", "json")
    assert code == 0, stderr
    assert json.loads(stdout) == {"key": "root", "name": "Root"}


def test_empty_owl_name_is_rejected(cli: CliRunner) -> None:
    os.environ["OWL_NAME"] = ""
    code, _stdout, stderr = cli.run("whoami")
    assert code == 1
    assert "OWL_NAME cannot be empty" in stderr


def test_root_key_is_reserved_for_literal_root(cli: CliRunner) -> None:
    os.environ["OWL_NAME"] = "root!"
    code, _stdout, stderr = cli.run("whoami")
    assert code == 1
    assert "root is reserved" in stderr

    os.environ["OWL_NAME"] = "root"
    code, stdout, stderr = cli.run("whoami", "--format", "json")
    assert code == 0, stderr
    assert json.loads(stdout) == {"key": "root", "name": "root"}

    os.environ["OWL_NAME"] = "Root"
    code, stdout, stderr = cli.run("whoami", "--format", "json")
    assert code == 0, stderr
    assert json.loads(stdout) == {"key": "root", "name": "Root"}


def test_whoami_without_owl_name_touches_root_state(cli: CliRunner) -> None:
    code, stdout, stderr = cli.run("whoami", "--format", "json")
    assert code == 0, stderr
    assert json.loads(stdout)["key"] == "root"
    assert (Path(cli.home) / "state" / "agents" / "root.json").exists()
