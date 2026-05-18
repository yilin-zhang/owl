from __future__ import annotations

import contextlib
import json
import os
import re
from pathlib import Path

import yaml

from owl_cli.spells import BUILTIN_SPELLS, extract_description
from tests.helpers import CliRunner

SKILL_NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def builtin_spell_paths() -> dict[str, Path]:
    paths: dict[str, Path] = {}
    for skill_path in BUILTIN_SPELLS.rglob("SKILL.md"):
        rel = skill_path.parent.relative_to(BUILTIN_SPELLS)
        key = "" if str(rel) == "." else rel.as_posix()
        paths[key] = skill_path
    return paths


def test_builtin_spell_frontmatter_is_valid_yaml() -> None:
    for skill_path in builtin_spell_paths().values():
        text = skill_path.read_text(encoding="utf-8")
        assert text.startswith("---\n"), skill_path
        parts = text.split("---", 2)
        assert len(parts) == 3, skill_path
        metadata = yaml.safe_load(parts[1])
        assert isinstance(metadata, dict), skill_path
        assert set(metadata) >= {"name", "description"}, skill_path
        assert isinstance(metadata.get("name"), str), skill_path
        assert isinstance(metadata.get("description"), str), skill_path
        assert 1 <= len(metadata["name"]) <= 64, skill_path
        assert SKILL_NAME_RE.fullmatch(metadata["name"]), skill_path
        assert metadata["name"] == skill_path.parent.name, skill_path
        assert metadata["description"]
        assert len(metadata["description"]) <= 1024, skill_path
        assert extract_description(text) == metadata["description"]


def test_builtin_spells_are_discoverable_and_castable(cli: CliRunner) -> None:
    expected = builtin_spell_paths()
    code, stdout, stderr = cli.run("spells", "list", "--all", "--format", "json")
    assert code == 0, stderr
    assert {row["path"] for row in json.loads(stdout)} == set(expected)

    for path, skill_path in expected.items():
        code, stdout, stderr = cli.run("spells", "cast", path)
        assert code == 0, stderr
        assert stdout == skill_path.read_text(encoding="utf-8") + "\n"


def write_spell(path: Path, description: str, body: str) -> None:
    path.parent.mkdir(parents=True)
    path.write_text(
        f'---\nname: {path.parent.name}\ndescription: "{description}"\n---\n\n{body}\n',
        encoding="utf-8",
    )


def test_custom_spell_precedence_is_builtin_user_then_project(cli: CliRunner) -> None:
    user_custom = Path(cli.user_home) / "spells" / "owl" / "messages" / "SKILL.md"
    project_custom = Path(cli.home) / "spells" / "owl" / "messages" / "SKILL.md"
    write_spell(user_custom, "User message spell.", "# User Messages")

    code, stdout, stderr = cli.run("spells", "list", "owl/messages", "--format", "json")
    assert code == 0, stderr
    rows = json.loads(stdout)
    assert rows == [
        {"path": "owl/messages", "source": "custom", "description": "User message spell."}
    ]

    code, stdout, stderr = cli.run("spells", "cast", "owl/messages")
    assert code == 0, stderr
    assert "# User Messages" in stdout

    write_spell(project_custom, "Project message spell.", "# Project Messages")
    code, stdout, stderr = cli.run("spells", "list", "owl/messages", "--format", "json")
    assert code == 0, stderr
    assert json.loads(stdout) == [
        {"path": "owl/messages", "source": "custom", "description": "Project message spell."}
    ]

    code, stdout, stderr = cli.run("spells", "cast", "owl/messages")
    assert code == 0, stderr
    assert "# Project Messages" in stdout


def test_spells_install_writes_codex_skill(cli: CliRunner) -> None:
    os.environ["CODEX_HOME"] = str(Path(cli.home) / "codex")
    code, cast_stdout, stderr = cli.run("spells", "cast", "owl")
    assert code == 0, stderr

    code, stdout, stderr = cli.run("spells", "install", "owl", "--format", "json")
    assert code == 0, stderr
    destination = Path(cli.home) / "codex" / "skills" / "owl"
    assert json.loads(stdout) == {"path": "owl", "installed_to": str(destination)}
    assert destination.is_symlink()
    assert (destination / "SKILL.md").read_text(encoding="utf-8") + "\n" == cast_stdout

    destination.unlink()
    destination.mkdir()
    (destination / "SKILL.md").write_text("stale\n", encoding="utf-8")
    code, _stdout, stderr = cli.run("spells", "install", "owl")
    assert code == 0, stderr
    assert destination.is_symlink()
    assert (destination / "SKILL.md").read_text(encoding="utf-8") + "\n" == cast_stdout

    custom = Path(cli.home) / "spells" / "owl" / "SKILL.md"
    custom.parent.mkdir(parents=True)
    custom.write_text("---\ndescription: Custom owl.\n---\n\n# Custom Owl\n", encoding="utf-8")
    code, custom_cast_stdout, stderr = cli.run("spells", "cast", "owl")
    assert code == 0, stderr
    code, _stdout, stderr = cli.run("spells", "install", "owl")
    assert code == 0, stderr
    assert destination.is_symlink()
    assert destination.resolve() == custom.parent.resolve()
    assert (destination / "SKILL.md").read_text(encoding="utf-8") + "\n" == custom_cast_stdout


def test_spells_install_uses_default_codex_home(cli: CliRunner) -> None:
    os.environ["HOME"] = str(Path(cli.home) / "home")
    code, stdout, stderr = cli.run("spells", "install", "owl", "--format", "json")
    assert code == 0, stderr
    destination = Path(cli.home) / "home" / ".codex" / "skills" / "owl"
    assert json.loads(stdout) == {"path": "owl", "installed_to": str(destination)}
    assert destination.is_symlink()


def test_spells_install_treats_empty_app_home_env_as_explicit_path(cli: CliRunner) -> None:
    cwd = Path(cli.home) / "cwd"
    cwd.mkdir(parents=True)
    os.environ["CODEX_HOME"] = ""
    with contextlib.chdir(cwd):
        code, stdout, stderr = cli.run("spells", "install", "owl", "--format", "json")
    assert code == 0, stderr
    destination = Path("skills") / "owl"
    assert json.loads(stdout) == {"path": "owl", "installed_to": str(destination)}
    assert (cwd / destination).is_symlink()


def test_spells_install_writes_claude_code_skill(cli: CliRunner) -> None:
    os.environ["CLAUDE_CONFIG_DIR"] = str(Path(cli.home) / "claude")
    code, cast_stdout, stderr = cli.run("spells", "cast", "owl")
    assert code == 0, stderr

    code, stdout, stderr = cli.run(
        "spells",
        "install",
        "owl",
        "--app",
        "claude-code",
        "--format",
        "json",
    )
    assert code == 0, stderr
    destination = Path(cli.home) / "claude" / "skills" / "owl"
    assert json.loads(stdout) == {"path": "owl", "installed_to": str(destination)}
    assert destination.is_symlink()
    assert (destination / "SKILL.md").read_text(encoding="utf-8") + "\n" == cast_stdout


def test_spells_install_does_not_replace_populated_skill_directory(cli: CliRunner) -> None:
    os.environ["CODEX_HOME"] = str(Path(cli.home) / "codex")
    destination = Path(cli.home) / "codex" / "skills" / "owl"
    destination.mkdir(parents=True)
    (destination / "SKILL.md").write_text("local\n", encoding="utf-8")
    (destination / "asset.txt").write_text("keep\n", encoding="utf-8")

    code, _stdout, stderr = cli.run("spells", "install", "owl")
    assert code == 1
    assert "skill install path already exists and is not replaceable" in stderr
    assert not destination.is_symlink()
    assert (destination / "asset.txt").read_text(encoding="utf-8") == "keep\n"


def test_spells_install_requires_named_spell_path(cli: CliRunner) -> None:
    root_spell = Path(cli.user_home) / "spells" / "SKILL.md"
    root_spell.parent.mkdir(parents=True)
    root_spell.write_text("---\ndescription: Root spell.\n---\n\n# Root\n", encoding="utf-8")

    code, _stdout, stderr = cli.run("spells", "install", "")
    assert code == 1
    assert "install requires a named spell path" in stderr


def test_spells_install_unknown_path_is_rejected(cli: CliRunner) -> None:
    code, _stdout, stderr = cli.run("spells", "install", "missing")
    assert code == 1
    assert "unknown spell path: missing" in stderr


def test_malformed_spell_frontmatter_does_not_crash(cli: CliRunner) -> None:
    custom = Path(cli.home) / "spells" / "broken" / "SKILL.md"
    custom.parent.mkdir(parents=True)
    custom.write_text("---\ndescription: Broken\n# Broken\n\nBody.\n")

    code, stdout, stderr = cli.run("spells", "list", "broken", "--format", "json")
    assert code == 0, stderr
    assert json.loads(stdout)[0]["path"] == "broken"
