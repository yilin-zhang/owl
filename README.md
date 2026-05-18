# Owl

`owl` is a local-first CLI for agent identity, mailbox, memory, and spell
discovery. It is designed as the durable data layer for later agent
orchestration.

Owl keeps its state in `~/.owl` by default. Set `OWL_HOME` to use a different
runtime directory for testing or isolated projects.

## Install

```bash
uv sync
owl --help
```

To install the CLI globally for agent apps on this machine:

```bash
uv tool install --editable .
owl --help
```

## Identity

Owl defaults to the `global` identity. Set `OWL_NAME` for an individual agent:

```bash
export OWL_NAME=Sarah
owl whoami
```

Launch agent tools the same way:

```bash
OWL_NAME=Sarah codex
OWL_NAME=Taylor claude
```

`global` is reserved. Unset `OWL_NAME` or set `OWL_NAME=global` to use global
memory intentionally.

## Opt-In Agent Skill

Owl does not have to be forced into every agent session. When an agent should
coordinate through Owl, register the built-in Owl skill with that agent app.

For Codex, write the skill into the Codex skills directory:

```bash
owl spells install owl
```

This writes `${CODEX_HOME:-~/.codex}/skills/owl/SKILL.md`. `CODEX_HOME` is
optional.

Then start a new agent session with an Owl identity:

```bash
OWL_NAME=Sarah codex
```

For another agent app, use the same idea: save `owl spells cast owl` as
`SKILL.md` in that app's skills or custom-instructions directory, then reload or
start a new session so the app discovers it.

`owl spells cast owl` only prints the skill file. The registered skill carries
the operating instructions for identity, mail, memory, perch, and watching. To
inspect the focused sub-skills:

```bash
owl spells list owl --all
owl spells cast owl/messages
owl spells cast owl/memory
owl spells cast owl/perch
```

## Basic Usage

Send messages and read your inbox:

```bash
owl message send Tom "Please review the patch"
owl message send --to Tom --to Lee --body "Please review the patch"
owl message send --to Tom --body-file ./note.md
owl message send --to Tom --stdin < ./note.md
owl message inbox
owl message read <message-id>
```

Use `--body-file` or `--stdin` for multiline bodies, command examples, quotes,
or other shell-sensitive text.

Successful non-watch commands print an unread-message reminder to stderr when
the current identity has pending mail. Command data still goes to stdout.

Watch is a one-shot wait:

```bash
owl message watch --format json
```

It exits when unread mail exists. There is no timeout unless `--timeout` is
set. The quiet keepalive interval defaults to 300 seconds, and each pulse also
checks for missed mail.

View the current agent dashboard:

```bash
owl perch status
owl perch status --format json
```

The perch status view is read-only. It shows agents with heartbeat or watch
state, their presence, watch state, unread counts, and newest unread message
metadata. It does not start, resume, or stop agent processes.

Write and inspect memory:

```bash
owl memory write "Prefers concise mailbox updates."
owl memory show
```

Individual agents see global memory plus their own memory. The `global` identity
sees memory from every agent.

Discover built-in and custom spells:

```bash
owl spells list
owl spells list owl --all
owl spells cast owl/messages
```

Custom spells go under `$OWL_HOME/spells`.

## Development

```bash
uv lock
owl --help
uv run pytest
uv run python -m compileall src tests
uvx mypy src tests
```
