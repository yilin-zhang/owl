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

## Agent Setup

Agent apps should include an Owl startup rule in their own `AGENTS.md` or
equivalent config:

```markdown
At startup, run `owl whoami --format json`, `owl memory show`, and
`owl message inbox`. Use `OWL_NAME=<name>` when launching this agent. Write
important durable facts, user preferences, and project decisions with
`owl memory write "...";` do not rely on chat history alone. After finishing a
task, start `owl message watch --format json` and leave it in the foreground
so new messages can wake the agent.
```

## Basic Usage

Send messages and read your inbox:

```bash
owl message send Tom "Please review the patch"
owl message send Tom --to Lee "Please review the patch"
owl message send --to Tom --body "Please review the patch"
owl message send --to Tom --body-file ./note.md
owl message inbox
owl message read <message-id>
```

Successful non-watch commands print an unread-message reminder to stderr when
the current identity has pending mail. Command data still goes to stdout.

Watch is a one-shot wait:

```bash
owl message watch --format json
```

It exits when unread mail exists. There is no timeout unless `--timeout` is
set. The quiet keepalive interval defaults to 300 seconds, and each pulse also
checks for missed mail.

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
uv run python -m unittest discover -s tests
uvx mypy src tests
```
