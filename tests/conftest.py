from __future__ import annotations

import os
import tempfile
from collections.abc import Iterator
from pathlib import Path

import pytest

from tests.helpers import CliRunner

_ENV_KEYS = (
    "OWL_HOME",
    "OWL_PROJECT_ROOT",
    "OWL_NAME",
    "CODEX_HOME",
    "CLAUDE_CONFIG_DIR",
    "HOME",
)


@pytest.fixture()
def cli() -> Iterator[CliRunner]:
    saved_env = {key: os.environ.get(key) for key in _ENV_KEYS}

    with tempfile.TemporaryDirectory(prefix="o-", dir="/tmp") as root:
        base = Path(root)
        user_home = base / "user-home"
        project_root = base / "project"
        user_home.mkdir()
        project_root.mkdir()

        os.environ["OWL_HOME"] = str(user_home)
        os.environ["OWL_PROJECT_ROOT"] = str(project_root)
        os.environ.pop("OWL_NAME", None)
        os.environ.pop("CODEX_HOME", None)
        os.environ.pop("CLAUDE_CONFIG_DIR", None)

        try:
            yield CliRunner(
                home=project_root / ".owl",
                project_root=project_root,
                user_home=user_home,
                repo_root=Path(__file__).resolve().parents[1],
            )
        finally:
            for key, value in saved_env.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value
