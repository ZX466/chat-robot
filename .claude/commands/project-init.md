---
description: Scaffold a new project following the team's recommended stack and directory conventions.
---

# Project Init

## Step 1: Clarify scope

Confirm: language/runtime, framework, package manager, and whether this is a lib, app, or monorepo package.

## Step 2: Scaffold

- Use the ecosystem's official scaffolder first (`create-vite`, `next create`, `cargo new`, `uv init`, `go mod init`).
- Configure the project's toolchain: formatter, linter, test runner, and CI entry.

## Step 3: Bootstrap conventions

- Add the project-level agent pack from `ecc-packs` if desired (rules + skills + commands).
- Commit a minimal, working baseline (`hello world` passing tests) before adding features.

## Step 4: Verify

- `npm run build` / equivalent passes.
- Test suite passes.
- Dev server starts.

$ARGUMENTS: `[name]` project name, `[type]` app|lib.