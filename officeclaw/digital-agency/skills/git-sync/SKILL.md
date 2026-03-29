---
name: git-sync
description: Living repo git protocol. Always active. Every agent run must start with git pull and end with a structured commit of all changes.
always: true
---

# Git Sync Protocol

Every run has two mandatory bookends: **pull at start**, **commit at end**.

## Start of run

```bash
git pull --rebase origin main
```

Do this before any file reads or work. If rebase fails (conflict), stop and report — do not proceed with stale state.

## End of run

Commit everything you changed:

```bash
git add -A
git commit -m "[agent/<trigger>] <phase>: <one-line summary>

Status: <complete|ready-for-review|blocked>
Uncertainty: <what you were unsure about, or 'none'>"
```

**`<trigger>`**: `cron` or `channel` — which trigger fired this run.

**`<phase>`**: what part of the vertical you were working on (e.g. `brief`, `moodboard`, `research`, `site-build`).

**`<one-line summary>`**: what actually happened, factually. Not "processed request" — write what changed.

**`Status`**:
- `complete` — work done, next step is clear
- `ready-for-review` — output exists, operator should review before proceeding
- `blocked` — can't continue without input

**`Uncertainty`**: what you couldn't resolve, what you guessed at, what felt ambiguous. This is what the operator reads first. Be honest, not diplomatic.

## Examples

```
[agent/channel] brief: collected requirements from client

Status: complete
Uncertainty: client said "premium feel" but didn't define it — guessed serif + dark palette
```

```
[agent/cron] research: scanned 8 design trend sources

Status: ready-for-review
Uncertainty: unsure which 2 of 5 trends are relevant to our ICP — left all 5 in research/2026-03-29-trends.md
```

```
[agent/channel] moodboard: created 3 directions, selected B

Status: ready-for-review
Uncertainty: direction A also viable — couldn't decide between A and B without client input
```

## If nothing changed

If your run produced no file changes (e.g. only sent a message), still commit a marker:

```bash
git commit --allow-empty -m "[agent/<trigger>] <phase>: no file changes — <what you did>"
```

This keeps the git log as a complete run history even for message-only turns.
