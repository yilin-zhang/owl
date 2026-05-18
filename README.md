# Owl 🦉

`owl` is a local-first CLI for agent identity, mailbox, memory, and spell
discovery. It is designed as the durable data layer for later agent
orchestration.

Owl keeps project runtime state in `./.owl` by default: messages, memory,
agent heartbeat state, watches, and project-local spells. Run Owl from the
project root, or set `OWL_PROJECT_ROOT` to point at the project explicitly.
When setting `OWL_PROJECT_ROOT` for agent sessions, use an absolute path.

`OWL_HOME` is separate. It defaults to `~/.owl` and is for user-level reusable
spells such as `$OWL_HOME/spells/<name>/SKILL.md`.

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

Owl defaults to the `Root` identity. Set `OWL_NAME` for an individual agent:

```bash
export OWL_NAME=Sarah
owl whoami
```

Launch agent tools the same way:

```bash
OWL_NAME=Sarah codex
OWL_NAME=Taylor claude
```

`root` is reserved. Unset `OWL_NAME` or set `OWL_NAME=root` to use Root memory
intentionally.

## Opt-In Agent Skill

Owl does not have to be forced into every agent session. When an agent should
coordinate through Owl, register the built-in Owl skill with that agent app.

For Codex, install the skill into the Codex skills directory:

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

Then start a new agent session with an Owl identity:

```bash
OWL_NAME=Sarah codex
OWL_NAME=Taylor claude
```

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
owl messages send Tom "Please review the patch"
owl messages send --to Tom --to Lee --body "Please review the patch"
owl messages send --to Tom --body-file ./note.md
owl messages send --to Tom --stdin < ./note.md
owl messages inbox
owl messages read <message-id>
```

Use `--body-file` or `--stdin` for multiline bodies, command examples, quotes,
or other shell-sensitive text.

Successful non-watch commands print an unread-message reminder to stderr when
the current identity has pending mail. Command data still goes to stdout.

Watch is a one-shot wait:

```bash
owl messages watch --format json
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

Individual agents see Root memory plus their own memory. The `Root` identity
sees memory from every agent in the current project.

Discover built-in and custom spells:

```bash
owl spells list
owl spells list owl --all
owl spells cast owl/messages
```

Custom spells can live in two places:

```text
$OWL_HOME/spells/<relative-path>/SKILL.md
./.owl/spells/<relative-path>/SKILL.md
```

Project spells override user spells, and user spells override built-ins.
Most successful Owl commands also check unread messages for the current
identity, so even discovery commands should be run from the project root or
with `OWL_PROJECT_ROOT` set.

Add `.owl/` to the project `.gitignore` unless you intentionally want to commit
project-local Owl data.

## Development

```bash
uv lock
uv run pytest
uv run mypy src tests
owl --help
```

## License

MIT
