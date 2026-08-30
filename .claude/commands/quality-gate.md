---
description: Run the project's quality gate (format + lint + type) on changed files and report remediation.
---

# Quality Gate

Run formatting, lint, and type checks on the project and fix findings.

## Step 1: Determine the toolchain

| Tool | Command |
|---|---|
| Biome | `npx biome check` |
| Prettier | `npx prettier --check <files>` |
| ESLint | `npx eslint .` |
| Ruff (Python) | `ruff check . && ruff format --check .` |
| gofmt | `gofmt -l .` |
| tsc | `npx tsc --noEmit` |

## Step 2: Run gate on changed files

Scope to files touched in this change for speed; escalate to full-project only on suspicion.

## Step 3: Fix & verify

- Auto-fix what the formatter allows (`--write`/`--fix`).
- Hand-fix remaining lint errors with minimal edits.
- Re-run the gate until clean.

$ARGUMENTS: optional `[path]` to gate a single file.