---
paths:
  - "**/*.ts"
  - "**/*.tsx"
  - "**/*.js"
  - "**/*.jsx"
---
# TypeScript/JavaScript Security

## Secret Management

- NEVER hardcode secrets. Use env vars, validate at startup.
- Scrub args/output of tokens before logging.

## Injection & XSS

- Parameterized queries only; no string-built SQL.
- Sanitize user HTML (`DOMPurify.sanitize`) instead of `dangerouslySetInnerHTML`.

## Checklist

- [ ] No secrets in source/git history
- [ ] `npm audit` / `pnpm audit` clean or documented
- [ ] Input validated with schema at boundaries
- [ ] `npx tsc --noEmit` passes