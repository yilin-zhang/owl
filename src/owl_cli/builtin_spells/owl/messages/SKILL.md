---
name: messages
description: "Use Owl mailbox commands to send, list, read, and track messages between agents."
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

Use the shorthand only for a single-recipient, one-line message:

```bash
owl message send Tom "Please inspect the failing test."
```

Use the explicit form for multiple recipients, CC, or non-trivial bodies:

```bash
owl message send --to Tom --to Lee --body "Please inspect the failing test."
owl message send --to Tom --cc Lee --body "Please inspect the failing test."
owl message send --to Tom --body-file ./review.md
owl message send --to Tom --stdin < ./review.md
```

The two forms are mutually exclusive. Do not combine positional recipients or
bodies with `--to`, `--cc`, `--body`, `--body-file`, or `--stdin`. Do not encode
recipient lists inside one name.

Use `--body-file` or `--stdin` for multiline bodies, command examples, quotes,
or any text containing shell metacharacters. Do not compose those bodies through
shell command substitution or positional arguments.

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
