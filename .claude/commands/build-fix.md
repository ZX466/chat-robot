---
description: Detect the build system and incrementally fix build/type errors with minimal safe changes.
---

# Build & Fix

## Step 1: Detect build system

| Indicator | Command |
|---|---|
| `package.json` with `build` | `npm run build` / `pnpm build` |
| `tsconfig.json` | `npx tsc --noEmit` |
| `Cargo.toml` | `cargo build` |
| `go.mod` | `go build ./...` |
| `pyproject.toml` | `python -m build` (or `mypy`/`ruff`) |

## Step 2: Fix iteratively

Fix errors one category at a time (type errors → build errors → tests):

1. Run the build to collect the full error set.
2. Fix the **earliest** error in the dependency order first; later errors often cascade.
3. Make minimal, targeted changes — avoid unrelated refactors.
4. Re-run the build; repeat until clean.
5. If a library version mismatch is the root cause, fix imports/declarations rather than bypassing with `// @ts-ignore`.

## Step 3: Verify

- Re-run the full build.
- Run the test suite for touched modules.
- Diff review: confirm no behavioral changes beyond the fix.

$ARGUMENTS: optional `[path]` to scope the build to a specific module.