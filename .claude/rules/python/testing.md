---
paths:
  - "**/*.py"
  - "**/*.pyi"
---
# Python Testing

## Framework

- **pytest** as the testing framework.

## Coverage

```bash
pytest --cov=src --cov-report=term-missing
```

## Organization

- One test file per module: `tests/test_<module>.py`.
- Use `pytest.mark` to categorize unit/integration.

```python
import pytest

@pytest.mark.unit
def test_calculate_total(): ...

@pytest.mark.integration
def test_database_connection(): ...
```

- Fixtures for setup; `tmp_path` for filesystem tests; `monkeypatch` for env/IO.