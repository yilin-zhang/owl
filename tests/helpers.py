from __future__ import annotations

import contextlib
import io
import sys
import time
from dataclasses import dataclass
from pathlib import Path

from owl_cli.cli import main


@dataclass(frozen=True)
class CliRunner:
    home: Path
    repo_root: Path

    def run(self, *args: str, stdin: str | None = None) -> tuple[int, str, str]:
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
        raise AssertionError(f"timed out waiting for {path}")
