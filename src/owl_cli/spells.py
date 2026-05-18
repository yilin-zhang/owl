from __future__ import annotations

import os
from pathlib import Path

from .constants import SOURCE_BUILTIN, SOURCE_CUSTOM
from .errors import OwlError
from .store import Store

BUILTIN_SPELLS = Path(__file__).parent / "builtin_spells"


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
            "content": text,
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
    spells.update(collect_spells_from_path(store.home / "spells", SOURCE_CUSTOM))
    return spells


def filter_spells(spells: dict[str, dict[str, str]], path: str | None, include_all: bool) -> list[dict[str, str]]:
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
    key = normalize_spell_path(path)
    spell_path = spell_file_path(BUILTIN_SPELLS, key)
    custom_path = spell_file_path(store.home / "spells", key)
    if custom_path.exists():
        spell_path = custom_path
    if not spell_path.exists():
        raise OwlError(f"unknown spell path: {path}")
    return spell_path.read_text(encoding="utf-8")


def install_spell(store: Store, path: str) -> Path:
    key = normalize_spell_path(path)
    content = cast_spell(store, path)
    destination = codex_skill_path(key)
    try:
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(content, encoding="utf-8")
    except OSError as exc:
        raise OwlError(f"failed to install spell: {exc}") from exc
    return destination


def codex_skill_path(key: str | None) -> Path:
    codex_home = Path(os.environ.get("CODEX_HOME") or Path.home() / ".codex").expanduser()
    if not key:
        return codex_home / "skills" / "SKILL.md"
    return codex_home / "skills" / key / "SKILL.md"


def spell_file_path(root: Path, key: str | None) -> Path:
    if not key:
        return root / "SKILL.md"
    return root / key / "SKILL.md"
