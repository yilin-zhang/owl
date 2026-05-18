---
name: agents
description: "Manage Owl agent identity with OWL_NAME and inspect agent status safely."
---

# Owl Agents

Owl identity is `OWL_NAME`, defaulting to `Root` when unset.

## Commands

```bash
export OWL_NAME=Sarah
owl whoami
owl messages status --format json
```

## Guidance

- Agent names are case-insensitive and normalized for storage.
- Unset `OWL_NAME` intentionally means the `Root` identity.
- `root` is reserved; use unset `OWL_NAME`, `OWL_NAME=Root`, or `OWL_NAME=root` for Root.
- `whoami` reports the current `OWL_NAME` identity and updates state.
- Status means recent Owl heartbeat or command activity. It does not prove the agent is currently reasoning.
- Launch Codex or Claude Code as `OWL_NAME=<name> codex` or `OWL_NAME=<name> claude`.
