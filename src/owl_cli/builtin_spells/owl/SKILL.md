---
description: Use Owl itself: identify agents, read mail, write memory, discover spells, and choose the right owl subcommand.
---

# Owl

Use this spell when you need to operate Owl from an agent session.

## Identity

Owl defaults to `global`. Set `OWL_NAME` before using an individual agent identity:

```bash
export OWL_NAME=Sarah
owl whoami
```

Do not use identity flags. Owl reads the current agent name from `OWL_NAME`, or
uses `global` when `OWL_NAME` is unset.

## Mail

Check mail before starting delegated work:

```bash
owl message inbox --format json
owl message read <message-id>
owl message sent --format json
```

Send to a recipient from the current identity:

```bash
owl message send Tom "Message body"
owl message send Tom --cc Lee "Message body"
```

## Memory

Use memory for durable facts that should survive context compaction:

```bash
owl memory show --format json
owl memory write "A concise durable fact."
owl memory compact "Current compacted memory summary."
```

Individual identities see global memory plus their own memory. The `global`
identity sees all memory.

## Spells

Discover first, cast only when relevant:

```bash
owl spells list owl --all
owl spells cast owl/messages
```

Prefer JSON output for agent parsing and TSV for quick human inspection.
