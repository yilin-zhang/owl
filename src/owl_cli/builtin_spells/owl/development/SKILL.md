---
name: development
description: "Work on Owl's Python CLI implementation, tests, package layout, and uv-based verification."
---

# Owl Development

Use this spell when editing Owl itself.

## Project Shape

```text
src/owl_cli/
  cli.py
  agents.py
  messages.py
  memory.py
  spells.py
  store.py
  output.py
  builtin_spells/
tests/
```

Keep built-in spell files under `src/owl_cli/builtin_spells`, not beside
`spells.py`.

## Verify

```bash
uv run isort --check-only src tests
uv run black --check src tests
uv run pytest
uv run python -m compileall src tests
uv run mypy src tests
uv run owl spells list owl --all --format json
```

Use `OWL_PROJECT_ROOT` to isolate manual runtime tests. Use `OWL_HOME` only when
testing user-level custom spell discovery.
