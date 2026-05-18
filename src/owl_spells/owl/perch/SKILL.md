---
name: perch
description: "Use or extend the Owl perch dashboard for read-only agent observability."
---

# Owl Perch

Use `perch` to inspect agent presence, watcher state, and unread mailbox status.
The current implementation is a read-only dashboard, not a supervisor.

## Dashboard

```bash
owl perch status
owl perch status --format json
```

Dashboard rows include:

- Agent key and display name.
- Presence from heartbeat state: `online`, `idle`, `offline`, or `unknown`.
- Watch state: `watching`, `stale`, or `no-watch`.
- Unread count and newest unread metadata.
- Last heartbeat and watch start timestamps.

`perch status` is read-only. It must not touch heartbeat state or change
message read state. Rows are created only from heartbeat state files and watch
registration files; message and memory data can enrich existing rows, but
should not create agent rows by themselves.

## Current Boundaries

- Keep identity as `OWL_NAME` only.
- Do not add bind/session identity.
- Do not start, resume, or stop agents from the dashboard.
- Treat a watch registration as live only when its pid is alive, its command
  matches the recorded command, and its socket exists.

## Future Supervisor

Future supervision can add commands such as:

```bash
owl perch wake Sarah "Prompt"
owl perch start
owl perch stop
```

Build these only after the resume contract is explicit. A future supervisor
should launch agent runtimes with `OWL_NAME=<agent>` and record run logs, exit
status, retry count, and backoff state. It should not make session ids a second
identity system.
