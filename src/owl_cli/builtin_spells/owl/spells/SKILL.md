---
description: Discover and cast Owl spells without loading irrelevant instructions into context.
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

This writes `${CODEX_HOME:-~/.codex}/skills/owl/SKILL.md` for Codex. It
installs one `SKILL.md`, not a recursive spell tree.

## Custom Spells

Custom spells live under:

```text
$OWL_HOME/spells/<relative-path>/SKILL.md
```

Custom spells override built-in spells with the same relative path.

Use `owl/spell-creator` when creating or revising a spell.
