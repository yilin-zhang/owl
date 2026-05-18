---
name: spells
description: "Discover and cast Owl spells without loading irrelevant instructions into context."
---

# Owl Spells

Spells are local `SKILL.md` files discoverable through Owl. Use them to load
task-specific instructions only when needed.

## Discover

```bash
owl spells list
owl spells list owl --all
owl spells list owl/messages --format json
```

## Cast

```bash
owl spells cast owl/messages
```

## Install

```bash
owl spells install owl
```

This creates or refreshes a symlink at `~/.codex/skills/owl/SKILL.md` by
default, or under `CODEX_HOME` when that environment variable is set.
The symlink keeps the registered skill live with the installed Owl source; rerun
install if that source path changes.

For Claude Code:

```bash
owl spells install owl --app claude-code
```

This creates or refreshes a symlink at `~/.claude/skills/owl/SKILL.md` by
default, or under `CLAUDE_CONFIG_DIR` when that environment variable is set.
The symlink keeps the registered skill live with the installed Owl source; rerun
install if that source path changes.

Install handles one `SKILL.md`, not a recursive spell tree.

## Custom Spells

Custom spells live under:

```text
$OWL_HOME/spells/<relative-path>/SKILL.md
```

Custom spells override built-in spells with the same relative path.

Use `spell-creator` when creating or revising a spell.
