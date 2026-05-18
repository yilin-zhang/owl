# Owl

`owl` is a local-first CLI for agent identity, mailbox, memory, and spell
discovery. It is designed as the durable data layer for later agent
orchestration.

Owl keeps its state in `~/.owl` by default. Set `OWL_HOME` to use a different
runtime directory for testing or isolated projects.

## Install

```bash
uv sync
uv run owl --help
```

## Identity

Owl defaults to the `global` identity. Set `OWL_NAME` for an individual agent:

```bash
export OWL_NAME=Sarah
uv run owl whoami
```

Launch agent tools the same way:

```bash
OWL_NAME=Sarah codex
OWL_NAME=Taylor claude
```

## Basic Usage

Send messages and read your inbox:

```bash
uv run owl message send Tom "Please review the patch"
uv run owl message inbox
uv run owl message read <message-id>
```

Write and inspect memory:

```bash
uv run owl memory write "Prefers concise mailbox updates."
uv run owl memory show
```

Individual agents see global memory plus their own memory. The `global` identity
sees memory from every agent.

Discover built-in and custom spells:

```bash
uv run owl spells list
uv run owl spells list owl --all
uv run owl spells cast owl/messages
```

Custom spells go under `$OWL_HOME/spells`.

## Development

```bash
uv lock
uv run owl --help
uv run python -m unittest discover -s tests
uvx mypy src tests
```
