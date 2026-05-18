from __future__ import annotations

import contextlib
import io
import json
import os
import signal
import socket
import subprocess
import sys
import tempfile
import time
import unittest
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from owl_cli.cli import main
from owl_cli.constants import EVENT_MESSAGE
from owl_cli.messages import append_message_event
from owl_cli.store import Store
from owl_cli.utils import utc_now


class CliTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.old_home = os.environ.get("OWL_HOME")
        self.old_name = os.environ.get("OWL_NAME")
        os.environ["OWL_HOME"] = self.tmp.name
        os.environ.pop("OWL_NAME", None)

    def tearDown(self) -> None:
        if self.old_home is None:
            os.environ.pop("OWL_HOME", None)
        else:
            os.environ["OWL_HOME"] = self.old_home
        if self.old_name is None:
            os.environ.pop("OWL_NAME", None)
        else:
            os.environ["OWL_NAME"] = self.old_name
        self.tmp.cleanup()

    def run_cli(self, *args: str, stdin: str | None = None) -> tuple[int, str, str]:
        stdout = io.StringIO()
        stderr = io.StringIO()
        old_stdin = sys.stdin
        if stdin is not None:
            sys.stdin = io.StringIO(stdin)
        try:
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                code = main(list(args))
            return code, stdout.getvalue(), stderr.getvalue()
        finally:
            sys.stdin = old_stdin

    def wait_for_path(self, path: Path) -> None:
        deadline = time.monotonic() + 2
        while time.monotonic() < deadline:
            if path.exists():
                return
            time.sleep(0.02)
        self.fail(f"timed out waiting for {path}")

    def test_owl_name_resolves_default_identity(self) -> None:
        os.environ["OWL_NAME"] = "Sam"
        code, stdout, stderr = self.run_cli("whoami", "--format", "json")
        self.assertEqual(code, 0, stderr)
        self.assertEqual(json.loads(stdout)["key"], "sam")

        code, stdout, stderr = self.run_cli("message", "send", "Tom", "hello", "--format", "json")
        self.assertEqual(code, 0, stderr)
        self.assertEqual(json.loads(stdout)["from"], "sam")

    def test_missing_owl_name_defaults_to_global_identity(self) -> None:
        code, stdout, stderr = self.run_cli("whoami", "--format", "json")
        self.assertEqual(code, 0, stderr)
        self.assertEqual(json.loads(stdout)["key"], "global")

    def test_empty_owl_name_is_rejected(self) -> None:
        os.environ["OWL_NAME"] = ""
        code, _stdout, stderr = self.run_cli("whoami")
        self.assertEqual(code, 1)
        self.assertIn("OWL_NAME cannot be empty", stderr)

    def test_global_key_is_reserved_for_literal_global(self) -> None:
        os.environ["OWL_NAME"] = "Global"
        code, _stdout, stderr = self.run_cli("whoami")
        self.assertEqual(code, 1)
        self.assertIn("global is reserved", stderr)

        os.environ["OWL_NAME"] = "global"
        code, stdout, stderr = self.run_cli("whoami", "--format", "json")
        self.assertEqual(code, 0, stderr)
        self.assertEqual(json.loads(stdout)["key"], "global")

    def test_message_send_inbox_read_sent(self) -> None:
        os.environ["OWL_NAME"] = "Sarah"
        code, stdout, stderr = self.run_cli(
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
        self.assertEqual(code, 0, stderr)
        message_id = json.loads(stdout)["id"]

        os.environ["OWL_NAME"] = "Tom"
        code, stdout, stderr = self.run_cli("message", "inbox", "--format", "json")
        self.assertEqual(code, 0, stderr)
        inbox = json.loads(stdout)
        self.assertEqual(inbox[0]["id"], message_id)
        self.assertEqual(inbox[0]["status"], "unread")
        self.assertEqual(inbox[0]["role"], "to")

        code, stdout, stderr = self.run_cli("message", "read", message_id)
        self.assertEqual(code, 0, stderr)
        self.assertIn("hello from sarah", stdout)

        code, _stdout, stderr = self.run_cli("message", "read", message_id)
        self.assertEqual(code, 0, stderr)

        os.environ["OWL_NAME"] = "Sarah"
        code, stdout, stderr = self.run_cli("message", "sent", "--format", "json")
        self.assertEqual(code, 0, stderr)
        sent = json.loads(stdout)
        self.assertEqual(sent[0]["read_by"], "tom")
        self.assertEqual(sent[0]["unread_by"], "lee")

        events = (Path(self.tmp.name) / "messages" / "messages.jsonl").read_text().splitlines()
        self.assertEqual(len(events), 2)
        self.assertEqual(json.loads(events[0])["type"], "message")
        self.assertEqual(json.loads(events[1])["type"], "read")

        os.environ["OWL_NAME"] = "Lee"
        code, _stdout, stderr = self.run_cli("message", "read", message_id)
        self.assertEqual(code, 0, stderr)

    def test_message_send_multiple_primary_recipients_and_body_sources(self) -> None:
        os.environ["OWL_NAME"] = "Sarah"
        code, stdout, stderr = self.run_cli(
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
        self.assertEqual(code, 0, stderr)
        sent = json.loads(stdout)
        self.assertEqual(sent["to"], "tom,lee")

        os.environ["OWL_NAME"] = "Lee"
        code, stdout, stderr = self.run_cli("message", "inbox", "--format", "json")
        self.assertEqual(code, 0, stderr)
        self.assertEqual(json.loads(stdout)[0]["preview"], "hello team")

        body_file = Path(self.tmp.name) / "body.txt"
        body_text = 'body from file\n$(owl message send Taylor "oops")\n"quoted"\n'
        body_file.write_text(body_text, encoding="utf-8")
        os.environ["OWL_NAME"] = "Sarah"
        code, stdout, stderr = self.run_cli(
            "message",
            "send",
            "--to",
            "Tom",
            "--body-file",
            str(body_file),
            "--format",
            "json",
        )
        self.assertEqual(code, 0, stderr)
        body_message_id = json.loads(stdout)["id"]
        self.assertEqual(json.loads(stdout)["to"], "tom")

        os.environ["OWL_NAME"] = "Tom"
        code, stdout, stderr = self.run_cli("message", "read", body_message_id, "--format", "json")
        self.assertEqual(code, 0, stderr)
        self.assertEqual(json.loads(stdout)["body"], body_text)

        stdin_text = 'body from stdin\n$(owl message send Taylor "oops")\n'
        os.environ["OWL_NAME"] = "Sarah"
        code, stdout, stderr = self.run_cli(
            "message",
            "send",
            "--to",
            "Tom",
            "--stdin",
            "--format",
            "json",
            stdin=stdin_text,
        )
        self.assertEqual(code, 0, stderr)
        stdin_message_id = json.loads(stdout)["id"]

        os.environ["OWL_NAME"] = "Tom"
        code, stdout, stderr = self.run_cli("message", "read", stdin_message_id, "--format", "json")
        self.assertEqual(code, 0, stderr)
        self.assertEqual(json.loads(stdout)["body"], stdin_text)

        code, _stdout, stderr = self.run_cli("message", "send", "--to", "Tom", "--body-file", str(body_file / "missing"))
        self.assertEqual(code, 1)
        self.assertIn("failed to read message body file", stderr)

        code, _stdout, stderr = self.run_cli("message", "send", "Tom", "accidental", "--body", "real")
        self.assertEqual(code, 1)
        self.assertIn("message send supports either", stderr)

        code, _stdout, stderr = self.run_cli("message", "send", "Tom", "hello", "--cc", "Lee")
        self.assertEqual(code, 1)
        self.assertIn("message send supports either", stderr)

        code, _stdout, stderr = self.run_cli("message", "send", "Tom", "--to", "Lee", "--body", "real")
        self.assertEqual(code, 1)
        self.assertIn("message send supports either", stderr)

        code, _stdout, stderr = self.run_cli("message", "send", "--to", "Tom", "body without positional recipient")
        self.assertEqual(code, 1)
        self.assertIn("message send supports either", stderr)

        code, _stdout, stderr = self.run_cli("message", "send", "--cc", "Lee", "--body", "cc without primary")
        self.assertEqual(code, 1)
        self.assertIn("explicit message form requires at least one --to recipient", stderr)

        code, _stdout, stderr = self.run_cli("message", "send", "--to", "Tom")
        self.assertEqual(code, 1)
        self.assertIn("explicit message form requires --body", stderr)

    def test_commands_piggyback_unread_notification_on_stderr(self) -> None:
        os.environ["OWL_NAME"] = "Tom"
        code, _stdout, stderr = self.run_cli("message", "send", "Sarah", "hello")
        self.assertEqual(code, 0, stderr)

        os.environ["OWL_NAME"] = "Sarah"
        code, stdout, stderr = self.run_cli("whoami", "--format", "json")
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(stdout)["key"], "sarah")
        self.assertIn("1 unread message", stderr)

    def test_message_defaults_to_global_sender_and_rejects_empty_recipient(self) -> None:
        code, stdout, stderr = self.run_cli("message", "send", "Tom", "body", "--format", "json")
        self.assertEqual(code, 0, stderr)
        self.assertEqual(json.loads(stdout)["from"], "global")

        os.environ["OWL_NAME"] = "Sarah"
        code, _stdout, stderr = self.run_cli("message", "send", "", "body")
        self.assertEqual(code, 1)
        self.assertIn("recipient", stderr)

    def test_message_primary_recipient_is_not_comma_split(self) -> None:
        os.environ["OWL_NAME"] = "Sarah"
        code, stdout, stderr = self.run_cli(
            "message",
            "send",
            "Tom,Lee",
            "body",
            "--format",
            "json",
        )
        self.assertEqual(code, 0, stderr)
        self.assertEqual(json.loads(stdout)["to"], "tom-lee")

        os.environ["OWL_NAME"] = "Tom"
        code, stdout, stderr = self.run_cli("message", "inbox", "--format", "json")
        self.assertEqual(code, 0, stderr)
        self.assertEqual(json.loads(stdout), [])

        os.environ["OWL_NAME"] = "Tom,Lee"
        code, stdout, stderr = self.run_cli("message", "inbox", "--format", "json")
        self.assertEqual(code, 0, stderr)
        self.assertEqual(len(json.loads(stdout)), 1)

    def test_unauthorized_message_read_is_rejected(self) -> None:
        os.environ["OWL_NAME"] = "Sarah"
        code, stdout, stderr = self.run_cli(
            "message",
            "send",
            "Tom",
            "secret",
            "--format",
            "json",
        )
        self.assertEqual(code, 0, stderr)
        message_id = json.loads(stdout)["id"]

        os.environ["OWL_NAME"] = "Lee"
        code, _stdout, stderr = self.run_cli("message", "read", message_id)
        self.assertEqual(code, 1)
        self.assertIn("not addressed", stderr)

    def test_memory_compact_is_append_only_effective_state(self) -> None:
        os.environ["OWL_NAME"] = "Sarah"
        self.assertEqual(self.run_cli("memory", "write", "old")[0], 0)
        self.assertEqual(self.run_cli("memory", "compact", "summary")[0], 0)
        self.assertEqual(self.run_cli("memory", "write", "new")[0], 0)

        code, stdout, stderr = self.run_cli("memory", "show")
        self.assertEqual(code, 0, stderr)
        self.assertEqual(stdout.strip().splitlines(), ["summary", "new"])

        events = (Path(self.tmp.name) / "memories" / "sarah.jsonl").read_text().splitlines()
        self.assertEqual([json.loads(line)["type"] for line in events], ["memory", "compact", "memory"])

    def test_memory_visibility_includes_global_scope(self) -> None:
        self.assertEqual(self.run_cli("memory", "write", "global-old")[0], 0)
        self.assertEqual(self.run_cli("memory", "compact", "global-summary")[0], 0)
        self.assertEqual(self.run_cli("memory", "write", "global-new")[0], 0)

        os.environ["OWL_NAME"] = "Sarah"
        self.assertEqual(self.run_cli("memory", "write", "sarah-old")[0], 0)
        self.assertEqual(self.run_cli("memory", "compact", "sarah-summary")[0], 0)
        self.assertEqual(self.run_cli("memory", "write", "sarah-new")[0], 0)

        os.environ["OWL_NAME"] = "Tom"
        self.assertEqual(self.run_cli("memory", "write", "tom-note")[0], 0)

        os.environ["OWL_NAME"] = "Sarah"
        code, stdout, stderr = self.run_cli("memory", "show", "--format", "json")
        self.assertEqual(code, 0, stderr)
        sarah_memory = json.loads(stdout)
        self.assertEqual(
            [event["text"] for event in sarah_memory["effective"]],
            ["global-summary", "global-new", "sarah-summary", "sarah-new"],
        )
        self.assertEqual({event["agent"] for event in sarah_memory["events"]}, {"global", "sarah"})

        os.environ.pop("OWL_NAME", None)
        code, stdout, stderr = self.run_cli("memory", "show", "--format", "json")
        self.assertEqual(code, 0, stderr)
        global_memory = json.loads(stdout)
        self.assertEqual(global_memory["agent"], "global")
        self.assertEqual(
            {event["text"] for event in global_memory["effective"]},
            {"global-summary", "global-new", "sarah-summary", "sarah-new", "tom-note"},
        )

    def test_custom_spell_overrides_builtin(self) -> None:
        custom = Path(self.tmp.name) / "spells" / "SKILL.md"
        custom.parent.mkdir(parents=True)
        custom.write_text("---\ndescription: Custom owl spell.\n---\n\n# Owl\n\nCustom content.\n")

        code, stdout, stderr = self.run_cli("spells", "list", "--format", "json")
        self.assertEqual(code, 0, stderr)
        rows = json.loads(stdout)
        root = next(row for row in rows if row["path"] == "")
        self.assertEqual(root["source"], "custom")
        self.assertEqual(root["description"], "Custom owl spell.")

        code, stdout, stderr = self.run_cli("spells", "cast", "")
        self.assertEqual(code, 0, stderr)
        self.assertIn("Custom content.", stdout)

    def test_watch_and_status(self) -> None:
        os.environ["OWL_NAME"] = "Sarah"
        code, stdout, stderr = self.run_cli(
            "message",
            "watch",
            "--timeout",
            "0.01",
        )
        self.assertEqual(code, 0, stderr)
        self.assertEqual(stdout, "")

        code, stdout, stderr = self.run_cli("message", "status", "--format", "json")
        self.assertEqual(code, 0, stderr)
        status = json.loads(stdout)[0]
        self.assertEqual(status["status"], "online")

        code, stdout, stderr = self.run_cli(
            "message",
            "watch",
            "--timeout",
            "0",
        )
        self.assertEqual(code, 0, stderr)
        self.assertEqual(stdout, "")

    def test_perch_status_is_read_only_when_no_agents_exist(self) -> None:
        code, stdout, stderr = self.run_cli("perch", "status", "--format", "json")
        self.assertEqual(code, 0, stderr)
        self.assertEqual(json.loads(stdout), [])
        self.assertFalse((Path(self.tmp.name) / "state" / "agents" / "global.json").exists())

    @unittest.skipUnless(hasattr(socket, "AF_UNIX"), "event-driven watch requires Unix sockets")
    def test_perch_status_combines_state_messages_and_watch(self) -> None:
        os.environ["OWL_NAME"] = "Sarah"
        code, _stdout, stderr = self.run_cli("whoami")
        self.assertEqual(code, 0, stderr)
        os.environ["OWL_NAME"] = "Lee"
        code, _stdout, stderr = self.run_cli("whoami")
        self.assertEqual(code, 0, stderr)
        os.environ["OWL_NAME"] = "Sarah"
        code, _stdout, stderr = self.run_cli("message", "send", "Lee", "hello lee")
        self.assertEqual(code, 0, stderr)

        memory_path = Path(self.tmp.name) / "memories" / "memory-only.jsonl"
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

        stale_watch = Path(self.tmp.name) / "state" / "agents" / "ghost.watch.json"
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
        broken_watch = Path(self.tmp.name) / "state" / "agents" / "broken.watch.json"
        broken_watch.write_text("{not-json", encoding="utf-8")

        env = os.environ.copy()
        env["OWL_HOME"] = self.tmp.name
        env["OWL_NAME"] = "Tom"
        env["PYTHONPATH"] = str(Path(__file__).resolve().parents[1] / "src")
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
            cwd=Path(__file__).resolve().parents[1],
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        try:
            self.wait_for_path(Path(self.tmp.name) / "state" / "agents" / "tom.watch.sock")
            code, stdout, stderr = self.run_cli("perch", "status", "--format", "json")
            self.assertEqual(code, 0, stderr)
            rows = {row["key"]: row for row in json.loads(stdout)}
            self.assertEqual(rows["sarah"]["presence"], "online")
            self.assertEqual(rows["lee"]["unread"], 1)
            self.assertEqual(rows["lee"]["newest_unread_from"], "sarah")
            self.assertEqual(rows["lee"]["newest_unread_preview"], "hello lee")
            self.assertEqual(rows["tom"]["watch"], "watching")
            self.assertEqual(rows["tom"]["unread"], 0)
            self.assertEqual(rows["ghost"]["watch"], "stale")
            self.assertEqual(rows["ghost"]["presence"], "unknown")
            self.assertEqual(rows["broken"]["watch"], "stale")
            self.assertNotIn("memory-only", rows)
        finally:
            watcher.terminate()
            try:
                watcher.communicate(timeout=2)
            except subprocess.TimeoutExpired:
                watcher.kill()
                watcher.communicate(timeout=2)

    @unittest.skipUnless(hasattr(socket, "AF_UNIX"), "event-driven watch requires Unix sockets")
    def test_watch_exits_on_message_without_waiting_for_pulse_interval(self) -> None:
        env = os.environ.copy()
        env["OWL_HOME"] = self.tmp.name
        env["OWL_NAME"] = "Tom"
        env["PYTHONPATH"] = str(Path(__file__).resolve().parents[1] / "src")
        started = time.monotonic()
        proc = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "owl_cli",
                "message",
                "watch",
                "--timeout",
                "5",
            ],
            cwd=Path(__file__).resolve().parents[1],
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        self.wait_for_path(Path(self.tmp.name) / "state" / "agents" / "tom.watch.sock")
        os.environ["OWL_NAME"] = "Sarah"
        code, _stdout, stderr = self.run_cli("message", "send", "Tom", "wake up")
        self.assertEqual(code, 0, stderr)
        stdout, stderr = proc.communicate(timeout=2)
        elapsed = time.monotonic() - started
        self.assertEqual(proc.returncode, 0)
        self.assertEqual(stdout, "")
        self.assertIn("1 unread message", stderr)
        self.assertLess(elapsed, 2.5)

    @unittest.skipUnless(hasattr(socket, "AF_UNIX"), "event-driven watch requires Unix sockets")
    def test_watch_pulse_exits_when_notification_is_missed(self) -> None:
        env = os.environ.copy()
        env["OWL_HOME"] = self.tmp.name
        env["OWL_NAME"] = "Tom"
        env["PYTHONPATH"] = str(Path(__file__).resolve().parents[1] / "src")
        proc = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "owl_cli",
                "message",
                "watch",
                "--interval",
                "0.1",
                "--timeout",
                "5",
                "--format",
                "json",
            ],
            cwd=Path(__file__).resolve().parents[1],
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        self.wait_for_path(Path(self.tmp.name) / "state" / "agents" / "tom.watch.sock")
        append_message_event(
            Store(Path(self.tmp.name)),
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
        self.assertEqual(proc.returncode, 0, stderr)
        self.assertEqual(json.loads(stdout), {"agent": "tom", "event": "message", "unread": 1})

    @unittest.skipUnless(hasattr(socket, "AF_UNIX"), "event-driven watch requires Unix sockets")
    def test_watch_replaces_existing_watcher_for_same_agent(self) -> None:
        env = os.environ.copy()
        env["OWL_HOME"] = self.tmp.name
        env["OWL_NAME"] = "Tom"
        env["PYTHONPATH"] = str(Path(__file__).resolve().parents[1] / "src")
        first = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "owl_cli",
                "message",
                "watch",
                "--timeout",
                "30",
            ],
            cwd=Path(__file__).resolve().parents[1],
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        self.wait_for_path(Path(self.tmp.name) / "state" / "agents" / "tom.watch.sock")

        second = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "owl_cli",
                "message",
                "watch",
                "--timeout",
                "0.01",
            ],
            cwd=Path(__file__).resolve().parents[1],
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        second_stdout, second_stderr = second.communicate(timeout=2)
        self.assertEqual(second.returncode, 0, second_stderr)
        self.assertEqual(second_stdout, "")

        first_stdout, first_stderr = first.communicate(timeout=2)
        self.assertEqual(first_stdout, "")
        self.assertEqual(first_stderr, "")
        self.assertEqual(first.returncode, -signal.SIGTERM)

    def test_whoami_without_owl_name_touches_global_state(self) -> None:
        code, stdout, stderr = self.run_cli("whoami", "--format", "json")
        self.assertEqual(code, 0, stderr)
        self.assertEqual(json.loads(stdout)["key"], "global")
        self.assertTrue((Path(self.tmp.name) / "state" / "agents" / "global.json").exists())

    def test_malformed_jsonl_and_state_are_controlled(self) -> None:
        messages = Path(self.tmp.name) / "messages" / "messages.jsonl"
        messages.parent.mkdir(parents=True)
        messages.write_text('"not an object"\n')

        os.environ["OWL_NAME"] = "Sarah"
        code, _stdout, stderr = self.run_cli("message", "inbox")
        self.assertEqual(code, 1)
        self.assertIn("expected object", stderr)

        state = Path(self.tmp.name) / "state" / "agents" / "sarah.json"
        state.parent.mkdir(parents=True, exist_ok=True)
        state.write_text('{"last_seen_at": "not-a-date"}\n')

        code, stdout, stderr = self.run_cli("message", "status", "--format", "json")
        self.assertEqual(code, 0, stderr)
        self.assertEqual(json.loads(stdout)[0]["status"], "unknown")

    def test_malformed_spell_frontmatter_does_not_crash(self) -> None:
        custom = Path(self.tmp.name) / "spells" / "broken" / "SKILL.md"
        custom.parent.mkdir(parents=True)
        custom.write_text("---\ndescription: Broken\n# Broken\n\nBody.\n")

        code, stdout, stderr = self.run_cli("spells", "list", "broken", "--format", "json")
        self.assertEqual(code, 0, stderr)
        self.assertEqual(json.loads(stdout)[0]["path"], "broken")


if __name__ == "__main__":
    unittest.main()
