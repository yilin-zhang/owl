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

This creates or refreshes a symlink at `~/.codex/skills/owl` by
default, or under `CODEX_HOME` when that environment variable is set.
The symlink points to the Owl skill directory, keeping `SKILL.md` and any
adjacent skill resources live with the installed Owl source; rerun install if
that source path changes.

For Claude Code:

```bash
owl spells install owl --app claude-code
```

This creates or refreshes a symlink at `~/.claude/skills/owl` by
default, or under `CLAUDE_CONFIG_DIR` when that environment variable is set.
The symlink points to the Owl skill directory, keeping `SKILL.md` and any
adjacent skill resources live with the installed Owl source; rerun install if
that source path changes.

Install handles one skill directory, not a recursive spell tree.

## Custom Spells

Custom spells live under:

```text
$OWL_HOME/spells/<relative-path>/SKILL.md
./.owl/spells/<relative-path>/SKILL.md
```

Project spells override user spells, and user spells override built-ins with
the same relative path. Use `OWL_PROJECT_ROOT` when the project root is not the
current working directory; prefer an absolute path in agent launch
configuration.

Most successful Owl commands check unread messages for the current identity, so
spell discovery still belongs to the active project context.

Use `spell-creator` when creating or revising a spell.
