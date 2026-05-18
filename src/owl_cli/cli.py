from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path
from typing import Any

from .agents import list_states, resolve_name, status_for_state, touch_state
from .constants import DEFAULT_WATCH_INTERVAL_SECONDS
from .errors import OwlError, die
from .memory import append_memory, visible_effective_memory, visible_memory_events
from .messages import MailboxWatcher, WatchRegistration, inbox_rows, read_message, send_message, sent_rows, unread_count
from .output import format_text_message, write_json, write_tsv
from .perch import perch_rows
from .spells import all_spells, cast_spell, filter_spells
from .store import Store, json_line


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    store = Store()
    try:
        code = args.func(args, store)
        if code == 0:
            maybe_report_unread(args, store)
        return code
    except OwlError as exc:
        return die(str(exc))
    except KeyboardInterrupt:
        return die("interrupted")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="owl")
    subparsers = parser.add_subparsers(dest="command", required=True)

    whoami = subparsers.add_parser("whoami", help="Show the current Owl agent.")
    add_format(whoami)
    whoami.set_defaults(func=cmd_whoami)

    memory = subparsers.add_parser("memory", help="Memory commands.")
    memory_sub = memory.add_subparsers(dest="memory_command", required=True)
    memory_show = memory_sub.add_parser("show")
    memory_show.add_argument("--format", choices=["text", "json"], default="text")
    memory_show.set_defaults(func=cmd_memory_show)
    memory_write = memory_sub.add_parser("write")
    memory_write.add_argument("text")
    add_format(memory_write)
    memory_write.set_defaults(func=cmd_memory_write)
    memory_compact = memory_sub.add_parser("compact")
    memory_compact.add_argument("text")
    add_format(memory_compact)
    memory_compact.set_defaults(func=cmd_memory_compact)

    message = subparsers.add_parser("message", help="Mailbox commands.")
    message_sub = message.add_subparsers(dest="message_command", required=True)
    message_send = message_sub.add_parser("send")
    message_send.add_argument("recipient", nargs="?")
    message_send.add_argument("body_arg", nargs="?")
    message_send.add_argument("--to", action="append", default=[])
    message_send.add_argument("--cc", action="append", default=[])
    message_send.add_argument("--body")
    message_send.add_argument("--body-file")
    message_send.add_argument("--stdin", action="store_true", dest="body_stdin")
    add_format(message_send)
    message_send.set_defaults(func=cmd_message_send)
    message_inbox = message_sub.add_parser("inbox")
    add_format(message_inbox)
    message_inbox.set_defaults(func=cmd_message_inbox)
    message_read = message_sub.add_parser("read")
    message_read.add_argument("message_id")
    message_read.add_argument("--format", choices=["text", "json"], default="text")
    message_read.set_defaults(func=cmd_message_read)
    message_sent = message_sub.add_parser("sent")
    add_format(message_sent)
    message_sent.set_defaults(func=cmd_message_sent)
    message_watch = message_sub.add_parser("watch")
    message_watch.add_argument("--timeout", type=float)
    message_watch.add_argument("--interval", type=float, default=DEFAULT_WATCH_INTERVAL_SECONDS)
    message_watch.add_argument("--format", choices=["text", "json"], default="text")
    message_watch.set_defaults(func=cmd_message_watch)
    message_status = message_sub.add_parser("status")
    message_status.add_argument("--threshold", type=int, default=120)
    add_format(message_status)
    message_status.set_defaults(func=cmd_message_status)

    perch = subparsers.add_parser("perch", help="Perch dashboard commands.")
    perch_sub = perch.add_subparsers(dest="perch_command", required=True)
    perch_status = perch_sub.add_parser("status")
    perch_status.add_argument("--threshold", type=int, default=120)
    add_format(perch_status)
    perch_status.set_defaults(func=cmd_perch_status)

    spells = subparsers.add_parser("spells", help="Spell discovery commands.")
    spells_sub = spells.add_subparsers(dest="spells_command", required=True)
    spells_list = spells_sub.add_parser("list")
    spells_list.add_argument("path", nargs="?")
    spells_list.add_argument("--all", action="store_true")
    add_format(spells_list)
    spells_list.set_defaults(func=cmd_spells_list)
    spells_cast = spells_sub.add_parser("cast")
    spells_cast.add_argument("path")
    spells_cast.set_defaults(func=cmd_spells_cast)

    return parser


def add_format(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--format", choices=["tsv", "json"], default="tsv")


def output_rows(rows: list[dict[str, Any]], columns: list[str], fmt: str) -> None:
    if fmt == "json":
        write_json(rows)
    else:
        write_tsv(rows, columns)


def output_one(row: dict[str, Any], columns: list[str], fmt: str) -> None:
    if fmt == "json":
        write_json(row)
    else:
        write_tsv([row], columns)


def cmd_whoami(args: argparse.Namespace, store: Store) -> int:
    ref = resolve_name()
    touch_state(store, ref)
    output_one({"key": ref.key, "name": ref.name}, ["key", "name"], args.format)
    return 0


def cmd_memory_show(args: argparse.Namespace, store: Store) -> int:
    ref = resolve_name()
    events = visible_memory_events(store, ref)
    effective = visible_effective_memory(store, ref)
    touch_state(store, ref)
    if args.format == "json":
        write_json({"agent": ref.key, "events": events, "effective": effective})
    else:
        print("\n".join(event.get("text", "") for event in effective))
    return 0


def cmd_memory_write(args: argparse.Namespace, store: Store) -> int:
    ref = resolve_name()
    event = append_memory(store, ref, "memory", args.text)
    output_one(event, ["id", "agent", "type", "created_at"], args.format)
    return 0


def cmd_memory_compact(args: argparse.Namespace, store: Store) -> int:
    ref = resolve_name()
    event = append_memory(store, ref, "compact", args.text)
    output_one(event, ["id", "agent", "type", "created_at"], args.format)
    return 0


def cmd_message_send(args: argparse.Namespace, store: Store) -> int:
    sender = resolve_name()
    recipients, body = message_send_inputs(args)
    event = send_message(store, sender, recipients, args.cc, body)
    row = {
        "id": event["id"],
        "from": event["from"],
        "to": ",".join(event["to"]),
        "cc": ",".join(event["cc"]),
        "created_at": event["created_at"],
    }
    output_one(row, ["id", "from", "to", "cc", "created_at"], args.format)
    return 0


def cmd_message_inbox(args: argparse.Namespace, store: Store) -> int:
    ref = resolve_name()
    rows = inbox_rows(store, ref)
    touch_state(store, ref)
    output_rows(rows, ["id", "status", "role", "from", "created_at", "preview"], args.format)
    return 0


def cmd_message_read(args: argparse.Namespace, store: Store) -> int:
    ref = resolve_name()
    message = read_message(store, ref, args.message_id)
    if args.format == "json":
        write_json(message)
    else:
        print(format_text_message(message))
    return 0


def cmd_message_sent(args: argparse.Namespace, store: Store) -> int:
    ref = resolve_name()
    rows = sent_rows(store, ref)
    touch_state(store, ref)
    output_rows(rows, ["id", "to", "cc", "created_at", "read_by", "unread_by", "preview"], args.format)
    return 0


def cmd_message_watch(args: argparse.Namespace, store: Store) -> int:
    ref = resolve_name()
    start = time.monotonic()
    deadline = None if args.timeout is None else start + args.timeout
    pulse_interval = max(args.interval, 1.0)
    next_pulse = start + pulse_interval
    touch_state(store, ref)
    with WatchRegistration(store, ref), MailboxWatcher(store, ref) as watcher:
        count = unread_count(store, ref)
        if count:
            report_unread(ref.key, count, args.format)
            return 0
        while True:
            now = time.monotonic()
            wait_until = next_pulse
            if deadline is not None:
                wait_until = min(wait_until, deadline)
            wait_timeout = max(wait_until - now, 0.0)
            changed = watcher.wait(wait_timeout)
            if changed:
                count = unread_count(store, ref)
                if count:
                    report_unread(ref.key, count, args.format)
                    return 0
                continue
            now = time.monotonic()
            if now >= next_pulse:
                count = unread_count(store, ref)
                if count:
                    report_unread(ref.key, count, args.format)
                    return 0
                touch_state(store, ref)
                next_pulse = now + pulse_interval
            if deadline is not None and now >= deadline:
                count = unread_count(store, ref)
                if count:
                    report_unread(ref.key, count, args.format)
                    return 0
                if args.format == "json":
                    write_json_line({"event": "timeout", "agent": ref.key})
                return 0


def report_unread(agent: str, count: int, fmt: str) -> None:
    if fmt == "json":
        write_json_line({"event": "message", "unread": count, "agent": agent})
    else:
        print(f"{count} unread message(s)", file=sys.stderr)


def cmd_message_status(args: argparse.Namespace, store: Store) -> int:
    rows: list[dict[str, Any]] = []
    for row in list_states(store):
        rows.append(status_row(row["key"], row["name"], row["state"], args.threshold))
    output_rows(rows, ["key", "name", "status", "last_seen_at"], args.format)
    return 0


def cmd_perch_status(args: argparse.Namespace, store: Store) -> int:
    rows = perch_rows(store, args.threshold)
    output_rows(
        rows,
        [
            "key",
            "name",
            "presence",
            "watch",
            "watcher_pid",
            "unread",
            "last_seen_at",
            "watch_started_at",
            "newest_unread_from",
            "newest_unread_at",
            "newest_unread_preview",
        ],
        args.format,
    )
    return 0


def status_row(key: str, name: str, state: dict[str, Any] | None, threshold: int) -> dict[str, Any]:
    return {
        "key": key,
        "name": name,
        "status": status_for_state(state, threshold),
        "last_seen_at": "" if not state else state.get("last_seen_at", ""),
    }


def write_json_line(data: dict[str, Any]) -> None:
    print(json_line(data), end="", flush=True)


def cmd_spells_list(args: argparse.Namespace, store: Store) -> int:
    rows = filter_spells(all_spells(store), args.path, args.all)
    output_rows(rows, ["path", "source", "description"], args.format)
    return 0


def cmd_spells_cast(args: argparse.Namespace, store: Store) -> int:
    print(cast_spell(store, args.path))
    return 0


def message_send_inputs(args: argparse.Namespace) -> tuple[list[str], str]:
    body_sources = [
        args.body is not None,
        args.body_file is not None,
        args.body_stdin,
    ]
    if sum(body_sources) > 1:
        raise OwlError("choose only one message body source")
    if any(body_sources) and args.body_arg is not None:
        raise OwlError("positional body cannot be used with --body, --body-file, or --stdin")

    recipients = []
    if args.recipient is not None:
        recipients.append(args.recipient)
    if args.body is not None:
        body = args.body
    elif args.body_file is not None:
        try:
            body = Path(args.body_file).read_text(encoding="utf-8")
        except OSError as exc:
            raise OwlError(f"failed to read message body file: {exc}") from exc
    elif args.body_stdin:
        body = sys.stdin.read()
    else:
        if args.body_arg is not None:
            body = args.body_arg
        else:
            raise OwlError("message requires recipients and a body")

    return [*recipients, *args.to], body


def maybe_report_unread(args: argparse.Namespace, store: Store) -> None:
    if getattr(args, "command", None) == "message" and getattr(args, "message_command", None) == "watch":
        return
    try:
        ref = resolve_name()
        count = unread_count(store, ref)
    except OwlError as exc:
        print(f"owl: message check failed: {exc}", file=sys.stderr)
        return
    if count:
        print(f"owl: {count} unread message(s). Run `owl message inbox`.", file=sys.stderr)
