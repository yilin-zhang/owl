---
description: Use Owl memory commands for durable per-agent facts and compacted summaries.
---

# Owl Memory

Use memory for durable facts that should outlive the current conversation.
Keep entries short and concrete.

## Commands

```bash
owl memory show --format json
owl memory write "Durable fact."
owl memory compact "Compacted memory summary."
```

## Guidance

- `write` appends a memory event.
- `compact` appends a compacted summary event; it does not rewrite history.
- `show` returns effective memory from the latest compaction onward.
- Individual identities see global memory plus their own memory.
- The `global` identity sees all memory.
- Memory files are local policy/audit storage, not a hard security boundary.
- Prefer one durable fact per write.
