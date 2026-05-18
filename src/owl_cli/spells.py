from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from .constants import SOURCE_BUILTIN, SOURCE_CUSTOM
from .errors import OwlError
from .store import Store, user_home

BUILTIN_SPELLS = Path(__file__).parent / "builtin_spells"


@dataclass(frozen=True)
class SkillApp:
    key: str
    home_env_var: str
    default_home_name: str

    def home(self) -> Path:
        env_value = os.environ.get(self.home_env_var)
        if env_value is None:
            return Path.home() / self.default_home_name
        return Path(env_value).expanduser()

    def skill_path(self, spell_key: str | None) -> Path:
        if not spell_key:
            return self.home() / "skills" / "SKILL.md"
        return self.home() / "skills" / spell_key / "SKILL.md"


SKILL_APPS = {
    "codex": SkillApp("codex", "CODEX_HOME", ".codex"),
    "claude-code": SkillApp("claude-code", "CLAUDE_CONFIG_DIR", ".claude"),
}


def load_builtin_spells() -> dict[str, dict[str, str]]:
    return collect_spells_from_path(BUILTIN_SPELLS, SOURCE_BUILTIN)


def collect_spells_from_path(root: Path, source: str) -> dict[str, dict[str, str]]:
    spells: dict[str, dict[str, str]] = {}
    if not root.exists():
        return spells
    for skill in root.rglob("SKILL.md"):
        rel = skill.parent.relative_to(root)
        key = "" if str(rel) == "." else rel.as_posix()
        text = skill.read_text(encoding="utf-8")
        spells[key] = {
            "path": key,
            "source": source,
            "description": extract_description(text),
        }
    return spells


def extract_description(text: str) -> str:
    if text.startswith("---\n"):
        parts = text.split("---", 2)
        if len(parts) == 3:
            _, frontmatter, rest = parts
            for line in frontmatter.splitlines():
                if line.lower().startswith("description:"):
                    return line.split(":", 1)[1].strip().strip("\"'")
            text = rest
    lines = text.splitlines()
    paragraph: list[str] = []
    seen_heading = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("#"):
            seen_heading = True
            continue
        if not stripped:
            if paragraph:
                break
            continue
        if seen_heading or not paragraph:
            paragraph.append(stripped)
    return " ".join(paragraph)


def all_spells(store: Store) -> dict[str, dict[str, str]]:
    spells = load_builtin_spells()
    spells.update(collect_spells_from_path(user_home() / "spells", SOURCE_CUSTOM))
    spells.update(collect_spells_from_path(store.home / "spells", SOURCE_CUSTOM))
    return spells


def filter_spells(
    spells: dict[str, dict[str, str]], path: str | None, include_all: bool
) -> list[dict[str, str]]:
    prefix = normalize_spell_path(path)
    rows: list[dict[str, str]] = []
    for key, spell in spells.items():
        if prefix is not None:
            if key != prefix and not key.startswith(prefix + "/"):
                continue
            if not include_all and key != prefix:
                remainder = key[len(prefix) :].strip("/")
                if "/" in remainder:
                    continue
        elif not include_all and "/" in key:
            continue
        rows.append({k: spell[k] for k in ["path", "source", "description"]})
    rows.sort(key=lambda row: row["path"])
    return rows


def normalize_spell_path(path: str | None) -> str | None:
    if path is None:
        return None
    clean = path.strip().strip("/")
    if ".." in clean.split("/"):
        raise OwlError("invalid spell path")
    return clean


def cast_spell(store: Store, path: str) -> str:
    return resolve_spell_file(store, path).read_text(encoding="utf-8")


def resolve_spell_file(store: Store, path: str) -> Path:
    key = normalize_spell_path(path)
    spell_path = spell_file_path(BUILTIN_SPELLS, key)
    user_custom_path = spell_file_path(user_home() / "spells", key)
    project_custom_path = spell_file_path(store.home / "spells", key)
    if user_custom_path.exists():
        spell_path = user_custom_path
    if project_custom_path.exists():
        spell_path = project_custom_path
    if not spell_path.exists():
        raise OwlError(f"unknown spell path: {path}")
    return spell_path


def install_spell(store: Store, path: str, app: str = "codex") -> Path:
    key = normalize_spell_path(path)
    source = resolve_spell_file(store, path)
    destination = skill_install_path(app, key)
    try:
        destination.parent.mkdir(parents=True, exist_ok=True)
        try:
            destination.unlink()
        except FileNotFoundError:
            pass
        destination.symlink_to(source.resolve())
    except OSError as exc:
        raise OwlError(f"failed to install spell: {exc}") from exc
    return destination


def skill_install_path(app: str, key: str | None) -> Path:
    try:
        skill_app = SKILL_APPS[app]
    except KeyError as exc:
        raise OwlError(f"unknown app: {app}") from exc
    return skill_app.skill_path(key)


def codex_skill_path(key: str | None) -> Path:
    return skill_install_path("codex", key)


def claude_code_skill_path(key: str | None) -> Path:
    return skill_install_path("claude-code", key)


def spell_file_path(root: Path, key: str | None) -> Path:
    if not key:
        return root / "SKILL.md"
    return root / key / "SKILL.md"
