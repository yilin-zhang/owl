from __future__ import annotations

import os
import tempfile
from collections.abc import Iterator
from pathlib import Path

import pytest

from tests.helpers import CliRunner

_ENV_KEYS = ("OWL_HOME", "OWL_NAME", "CODEX_HOME", "CLAUDE_CONFIG_DIR", "HOME")


@pytest.fixture()
def cli() -> Iterator[CliRunner]:
    saved_env = {key: os.environ.get(key) for key in _ENV_KEYS}

    with tempfile.TemporaryDirectory(prefix="owl-", dir=tempfile.gettempdir()) as home:
        os.environ["OWL_HOME"] = home
        os.environ.pop("OWL_NAME", None)
        os.environ.pop("CODEX_HOME", None)
        os.environ.pop("CLAUDE_CONFIG_DIR", None)

        try:
            yield CliRunner(home=Path(home), repo_root=Path(__file__).resolve().parents[1])
        finally:
            for key, value in saved_env.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value
