import json
from collections.abc import Callable
from pathlib import Path

import pytest

from providers import http as http_pool

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def load_fixture() -> Callable[[str], dict]:
    def _load(name: str) -> dict:
        return json.loads((FIXTURES_DIR / name).read_text(encoding="utf-8"))

    return _load


@pytest.fixture(autouse=True)
async def _close_shared_client():
    yield
    await http_pool.close_shared_client()
