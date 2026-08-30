---
description: Measure test coverage and identify untested code to improve.
---

# Test Coverage

## Step 1: Detect coverage tool

| Tool | Command |
|---|---|
| Vitest | `npx vitest run --coverage` |
| Jest | `npx jest --coverage` |
| pytest | `pytest --cov=.` |
| Go | `go test -cover ./...` |
| Rust | `cargo llvm-cov` |

## Step 2: Analyze gaps

- Report total coverage % per module.
- List modules below the project's threshold (default 80%).
- Identify high-risk untested paths: error branches, auth, I/O, edge cases.

## Step 3: Write missing tests

Prioritize by risk × coverage gap. Add tests for the highest-value thunks first.

## Step 4: Verify

- Coverage increases on the targeted modules.
- No existing tests regressed.

$ARGUMENTS: optional `[module]` to target a specific package.