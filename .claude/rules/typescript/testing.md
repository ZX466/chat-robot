---
paths:
  - "**/*.ts"
  - "**/*.tsx"
  - "**/*.js"
  - "**/*.jsx"
---
# TypeScript/JavaScript Testing

## Framework

- **Vitest** or **Jest** for unit/testing; **Playwright** for E2E critical flows.

## Conventions

- Test files colocated or in `__tests__/`; one describe per unit.
- Table-driven cases for edge inputs; assert error paths too.
- Coverage ≥ 80% on new code: `npx vitest run --coverage`.

## E2E

- Playwright: cover critical user flows only, keep fast; CI on every PR.

## Checklist

- [ ] `npx tsc --noEmit` passes
- [ ] `npx vitest run` / `jest` passes
- [ ] New behavior covered by tests