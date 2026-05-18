from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .errors import OwlError


def message_send_inputs(args: argparse.Namespace) -> tuple[list[str], str]:
    usage = (
        "messages send supports either `owl messages send NAME BODY` or "
        "`owl messages send --to NAME [--to NAME ...] [--cc NAME ...] "
        "(--body TEXT | --body-file PATH | --stdin)`"
    )
    body_sources = [
        args.body is not None,
        args.body_file is not None,
        args.body_stdin,
    ]
    flags_present = bool(args.to or args.cc or any(body_sources))
    if flags_present and (args.recipient is not None or args.body_arg is not None):
        raise OwlError(usage)
    if not flags_present:
        if args.recipient is None or args.body_arg is None:
            raise OwlError(usage)
        return [args.recipient], args.body_arg
    if not args.to:
        raise OwlError("explicit message form requires at least one --to recipient")
    body_source_count = sum(body_sources)
    if body_source_count > 1:
        raise OwlError("choose only one message body source")
    if body_source_count == 0:
        raise OwlError("explicit message form requires --body, --body-file, or --stdin")

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
        raise OwlError("explicit message form requires --body, --body-file, or --stdin")

    return args.to, body
