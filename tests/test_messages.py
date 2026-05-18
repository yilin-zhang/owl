from __future__ import annotations

import json
import os
from pathlib import Path

from tests.helpers import CliRunner


def test_message_send_inbox_read_sent(cli: CliRunner) -> None:
    os.environ["OWL_NAME"] = "Sarah"
    code, stdout, stderr = cli.run(
        "message",
        "send",
        "--to",
        "Tom",
        "--cc",
        "Lee",
        "--body",
        "hello from sarah",
        "--format",
        "json",
    )
    assert code == 0, stderr
    message_id = json.loads(stdout)["id"]

    os.environ["OWL_NAME"] = "Tom"
    code, stdout, stderr = cli.run("message", "inbox", "--format", "json")
    assert code == 0, stderr
    inbox = json.loads(stdout)
    assert inbox[0]["id"] == message_id
    assert inbox[0]["status"] == "unread"
    assert inbox[0]["role"] == "to"

    code, stdout, stderr = cli.run("message", "read", message_id)
    assert code == 0, stderr
    assert "hello from sarah" in stdout

    code, _stdout, stderr = cli.run("message", "read", message_id)
    assert code == 0, stderr

    os.environ["OWL_NAME"] = "Sarah"
    code, stdout, stderr = cli.run("message", "sent", "--format", "json")
    assert code == 0, stderr
    sent = json.loads(stdout)
    assert sent[0]["read_by"] == "tom"
    assert sent[0]["unread_by"] == "lee"

    events = (Path(cli.home) / "messages" / "messages.jsonl").read_text().splitlines()
    assert len(events) == 2
    assert json.loads(events[0])["type"] == "message"
    assert json.loads(events[1])["type"] == "read"

    os.environ["OWL_NAME"] = "Lee"
    code, _stdout, stderr = cli.run("message", "read", message_id)
    assert code == 0, stderr


def test_message_send_multiple_primary_recipients_and_body_sources(cli: CliRunner) -> None:
    os.environ["OWL_NAME"] = "Sarah"
    code, stdout, stderr = cli.run(
        "message",
        "send",
        "--to",
        "Tom",
        "--to",
        "Lee",
        "--body",
        "hello team",
        "--format",
        "json",
    )
    assert code == 0, stderr
    assert json.loads(stdout)["to"] == "tom,lee"

    os.environ["OWL_NAME"] = "Lee"
    code, stdout, stderr = cli.run("message", "inbox", "--format", "json")
    assert code == 0, stderr
    assert json.loads(stdout)[0]["preview"] == "hello team"

    body_file = Path(cli.home) / "body.txt"
    body_text = 'body from file\n$(owl message send Taylor "oops")\n"quoted"\n'
    body_file.write_text(body_text, encoding="utf-8")
    os.environ["OWL_NAME"] = "Sarah"
    code, stdout, stderr = cli.run(
        "message",
        "send",
        "--to",
        "Tom",
        "--body-file",
        str(body_file),
        "--format",
        "json",
    )
    assert code == 0, stderr
    body_message_id = json.loads(stdout)["id"]
    assert json.loads(stdout)["to"] == "tom"

    os.environ["OWL_NAME"] = "Tom"
    code, stdout, stderr = cli.run("message", "read", body_message_id, "--format", "json")
    assert code == 0, stderr
    assert json.loads(stdout)["body"] == body_text

    stdin_text = 'body from stdin\n$(owl message send Taylor "oops")\n'
    os.environ["OWL_NAME"] = "Sarah"
    code, stdout, stderr = cli.run(
        "message",
        "send",
        "--to",
        "Tom",
        "--stdin",
        "--format",
        "json",
        stdin=stdin_text,
    )
    assert code == 0, stderr
    stdin_message_id = json.loads(stdout)["id"]

    os.environ["OWL_NAME"] = "Tom"
    code, stdout, stderr = cli.run("message", "read", stdin_message_id, "--format", "json")
    assert code == 0, stderr
    assert json.loads(stdout)["body"] == stdin_text

    code, _stdout, stderr = cli.run(
        "message", "send", "--to", "Tom", "--body-file", str(body_file / "missing")
    )
    assert code == 1
    assert "failed to read message body file" in stderr

    code, _stdout, stderr = cli.run("message", "send", "Tom", "accidental", "--body", "real")
    assert code == 1
    assert "message send supports either" in stderr

    code, _stdout, stderr = cli.run("message", "send", "Tom", "hello", "--cc", "Lee")
    assert code == 1
    assert "message send supports either" in stderr

    code, _stdout, stderr = cli.run("message", "send", "Tom", "--to", "Lee", "--body", "real")
    assert code == 1
    assert "message send supports either" in stderr

    code, _stdout, stderr = cli.run(
        "message", "send", "--to", "Tom", "body without positional recipient"
    )
    assert code == 1
    assert "message send supports either" in stderr

    code, _stdout, stderr = cli.run(
        "message", "send", "--cc", "Lee", "--body", "cc without primary"
    )
    assert code == 1
    assert "explicit message form requires at least one --to recipient" in stderr

    code, _stdout, stderr = cli.run("message", "send", "--to", "Tom")
    assert code == 1
    assert "explicit message form requires --body" in stderr


def test_commands_piggyback_unread_notification_on_stderr(cli: CliRunner) -> None:
    os.environ["OWL_NAME"] = "Tom"
    code, stdout, stderr = cli.run("message", "send", "Sarah", "hello", "--format", "json")
    assert code == 0, stderr
    message_id = json.loads(stdout)["id"]

    os.environ["OWL_NAME"] = "Sarah"
    code, stdout, stderr = cli.run("whoami", "--format", "json")
    assert code == 0
    assert json.loads(stdout)["key"] == "sarah"
    assert "1 unread message" in stderr

    code, stdout, stderr = cli.run("message", "inbox", "--format", "json")
    assert code == 0, stderr
    assert stderr == ""
    assert json.loads(stdout)[0]["id"] == message_id

    code, _stdout, stderr = cli.run("message", "sent", "--format", "json")
    assert code == 0, stderr
    assert stderr == ""

    code, _stdout, stderr = cli.run("message", "status", "--format", "json")
    assert code == 0, stderr
    assert "1 unread message" in stderr

    code, stdout, stderr = cli.run("message", "read", message_id, "--format", "json")
    assert code == 0, stderr
    assert stderr == ""
    assert json.loads(stdout)["id"] == message_id


def test_message_defaults_to_root_sender_and_rejects_empty_recipient(cli: CliRunner) -> None:
    code, stdout, stderr = cli.run("message", "send", "Tom", "body", "--format", "json")
    assert code == 0, stderr
    assert json.loads(stdout)["from"] == "root"

    os.environ["OWL_NAME"] = "Sarah"
    code, _stdout, stderr = cli.run("message", "send", "", "body")
    assert code == 1
    assert "recipient" in stderr


def test_message_primary_recipient_is_not_comma_split(cli: CliRunner) -> None:
    os.environ["OWL_NAME"] = "Sarah"
    code, stdout, stderr = cli.run(
        "message",
        "send",
        "Tom,Lee",
        "body",
        "--format",
        "json",
    )
    assert code == 0, stderr
    assert json.loads(stdout)["to"] == "tom-lee"

    os.environ["OWL_NAME"] = "Tom"
    code, stdout, stderr = cli.run("message", "inbox", "--format", "json")
    assert code == 0, stderr
    assert json.loads(stdout) == []

    os.environ["OWL_NAME"] = "Tom,Lee"
    code, stdout, stderr = cli.run("message", "inbox", "--format", "json")
    assert code == 0, stderr
    assert len(json.loads(stdout)) == 1


def test_unauthorized_message_read_is_rejected(cli: CliRunner) -> None:
    os.environ["OWL_NAME"] = "Sarah"
    code, stdout, stderr = cli.run(
        "message",
        "send",
        "Tom",
        "secret",
        "--format",
        "json",
    )
    assert code == 0, stderr
    message_id = json.loads(stdout)["id"]

    os.environ["OWL_NAME"] = "Lee"
    code, _stdout, stderr = cli.run("message", "read", message_id)
    assert code == 1
    assert "not addressed" in stderr
