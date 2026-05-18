---
description: Use Owl mailbox commands to send, list, read, and track messages between agents.
---

# Owl Messages

Use the mailbox for work requests, handoffs, and durable inter-agent notes.

## Read Incoming Mail

```bash
owl message inbox --format json
owl message read <message-id>
```

`read` marks the message as read for that recipient.

## Send Mail

```bash
owl message send Tom "Please inspect the failing test."
owl message send Tom --cc Lee "Please inspect the failing test."
```

Use `--cc` for CC recipients. The primary recipient is one name; do not encode recipient lists inside the positional name.

## Sent Mail

```bash
owl message sent --format json
```

Sent output includes per-recipient read state. Use JSON when another agent will parse the result.

## Watching

```bash
owl message watch --timeout 120 --format json
```

Watch waits for new mail addressed to the current identity and exits when unread mail arrives.
