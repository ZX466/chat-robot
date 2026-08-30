---
paths:
  - "**/*.py"
  - "**/*.pyi"
---
# Python Security

## Secret Management

```python
import os

api_key = os.environ["OPENAI_API_KEY"]  # raises KeyError if missing
```

- Never hardcode keys; load from env; fail loud if missing.

## Static Scan

- Run **bandit** in CI: `bandit -r src/`.

## Checklist

- [ ] No secrets in source/git history
- [ ] `bandit -r src/` passes
- [ ] Inputs validated at boundaries (pydantic/FastAPI schemas)
- [ ] No `eval` of untrusted input; no shell=True without validation
- [ ] `ruff check .` clean