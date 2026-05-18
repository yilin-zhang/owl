---
description: Plan future Owl perch supervision around explicit identity and one-shot agent resumes.
---

# Owl Perch

`perch` is not implemented in the MVP. Use this spell only when designing or
implementing the future supervisor.

## Design Constraints

- Treat `codex exec resume <SESSION_ID> <PROMPT>` as one processing attempt.
- Keep `perch` as the long-running process; agents should not be required to hold watch loops open.
- Use `OWL_NAME` for process identity.
- Prevent double-resume of the same agent with per-agent ownership locks.
- Record run logs, exit status, last output, retry count, and backoff state.

## First Useful Commands

```bash
owl perch status
owl perch wake Sarah "Prompt"
owl perch start
owl perch stop
```

Build these only after the mailbox, memory, and agent state commands are stable.
