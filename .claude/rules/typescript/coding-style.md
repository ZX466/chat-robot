---
paths:
  - "**/*.ts"
  - "**/*.tsx"
  - "**/*.js"
  - "**/*.jsx"
---
# TypeScript/JavaScript Coding Style

## Types & Interfaces

- Explicit types on public APIs (exported functions, shared models, component props).
- `interface` for extensible object shapes; `type` for unions/intersections/tuples/utility types.
- String literal unions over `enum` unless interop requires it.
- Avoid `any`; use `unknown` for untrusted input then narrow; use generics for caller-dependent types.
- Type all callback props; skip `React.FC` unless needed.
- `.js/.jsx`: JSDoc when types clarify, keep aligned with runtime.

## Immutability

- Spread for updates; never mutate in place: `{ ...user, name }`.

## Error Handling

- `async/await` + try/catch; narrow unknown: `error instanceof Error`.
- No silent catches; log then rethrow with context.

## Input Validation

- Zod schema-based validation; infer types from schema (`z.infer<typeof schema>`).

## Console.log

- No `console.log` in production; use a logging library.

```typescript
// WRONG
export function formatUser(user) { ... }
// CORRECT
interface User { firstName: string; lastName: string }
export function formatUser(user: User): string { ... }
```