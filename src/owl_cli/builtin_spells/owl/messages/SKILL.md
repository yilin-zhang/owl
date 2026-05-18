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
owl message send Tom --to Lee "Please inspect the failing test."
owl message send --to Tom --body "Please inspect the failing test."
owl message send --to Tom --body-file ./review.md
```

Use `--to` for additional primary recipients and `--cc` for CC recipients. Do not encode recipient lists inside one name.

Successful non-watch Owl commands print an unread-message reminder to stderr
when the current identity has pending mail. Data output remains on stdout.

## Sent Mail

```bash
owl message sent --format json
```

Sent output includes per-recipient read state. Use JSON when another agent will parse the result.

## Watching

```bash
owl message watch --format json
```

Watch waits for mail addressed to the current identity and exits when unread
mail exists. It has no default timeout; use `--timeout` only when a finite wait
is explicitly desired. The quiet keepalive interval defaults to 300 seconds and
also checks for missed mail. Starting a watcher for the same identity replaces
the previous watcher.
