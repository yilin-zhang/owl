---
name: owl
description: "Opt in to Owl coordination: identify the agent, read mail, write memory, inspect perch, watch for messages, and choose the right owl subcommand."
---

# Owl

Use this skill when the current task or project has opted into Owl coordination.
The skill is the canonical agent-facing operating guide for Owl; use focused
sub-skills only when you need deeper detail.

## Startup Checklist

When Owl is active for the session, orient before doing delegated work:

```bash
owl whoami --format json
owl memory show --format json
owl message inbox --format json
```

Read unread messages that are relevant to the current work:

```bash
owl message read <message-id>
```

## Identity

Owl defaults to `global`. Set `OWL_NAME` before using an individual agent identity:

```bash
export OWL_NAME=Sarah
owl whoami
```

Do not use identity flags. Owl reads the current agent name from `OWL_NAME`, or
uses `global` when `OWL_NAME` is unset.

Unset `OWL_NAME` intentionally means the shared `global` identity. Individual
identities see global memory plus their own memory; the global identity sees all
memory.

## Mail

Inspect mailbox state:

```bash
owl message inbox --format json
owl message sent --format json
```

Use the shorthand only for a single-recipient, one-line message:

```bash
owl message send Tom "Message body"
```

Use the explicit form for multiple recipients, CC, or non-trivial bodies:

```bash
owl message send --to Tom --to Lee --body "Message body"
owl message send --to Tom --cc Lee --body "Message body"
owl message send --to Tom --body-file ./note.md
owl message send --to Tom --stdin < ./note.md
```

Do not mix positional recipients with `--to`, `--cc`, `--body`,
`--body-file`, or `--stdin`.

Successful non-watch Owl commands print an unread-message reminder to stderr
when the current identity has pending mail. Data output remains on stdout.

## Memory

Use memory for short durable facts that should survive context compaction:

```bash
owl memory show --format json
owl memory write "A concise durable fact."
owl memory compact "Current compacted memory summary."
```

Write only facts worth carrying into future agent sessions: user preferences,
project decisions, handoff state, and compact summaries. Do not use global
memory for transient progress updates.

## Spells

Discover first, cast only when relevant:

```bash
owl spells list owl --all
owl spells cast owl/messages
owl spells cast owl/perch
```

Prefer JSON output for agent parsing and TSV for quick human inspection.

## Perch Dashboard

Inspect agent status without changing heartbeat or message read state:

```bash
owl perch status
owl perch status --format json
```

## Watch

When an Owl-managed agent finishes useful work and should remain reachable,
start:

```bash
owl message watch --format json
```

Watch is one-shot: it stays alive until unread mail exists, then exits. It has
no default timeout. The quiet keepalive interval defaults to 300 seconds and
also checks for missed mail.
