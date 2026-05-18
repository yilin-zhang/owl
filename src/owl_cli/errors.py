from __future__ import annotations

import sys


class OwlError(Exception):
    """Expected user-facing command error."""


def die(message: str) -> int:
    print(f"owl: {message}", file=sys.stderr)
    return 1
