---
description: Create or revise Owl spells: concise SKILL.md files with clear trigger descriptions and optional progressive disclosure.
---

# Owl Spell Creator

Use this spell when creating or updating an Owl spell.

This is adapted from the Codex `skill-creator` pattern: keep the spell concise,
give it clear trigger metadata, and add extra resources only when they reduce
future context load.

## Spell Shape

An Owl spell is a directory containing `SKILL.md`:

```text
some/path/SKILL.md
```

The file must have YAML frontmatter with a `description`:

```markdown
---
description: Use when the agent needs to do X with Y.
---

# Spell Title

Core instructions go here.
```

## Location

For user/local spells:

```text
$OWL_HOME/spells/<relative-path>/SKILL.md
```

For built-in spells while developing Owl:

```text
src/owl_cli/builtin_spells/<relative-path>/SKILL.md
```

Custom spells override built-ins by relative path.

## Writing Rules

- Keep the body short and procedural.
- Assume the agent is capable; include only context it would not already know.
- Put the trigger/use case in `description`, not just in the body.
- Prefer commands and decision rules over broad explanation.
- Avoid separate README or changelog files inside a spell.
- If a spell grows large, keep `SKILL.md` as the routing guide and link to one-level reference files.

## Validate

```bash
owl spells list <parent-path> --all --format json
owl spells cast <relative-path>
```

Check that the listed description is clear enough for an agent to choose the
spell without reading the full body.
