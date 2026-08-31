import json
import os
from collections.abc import Callable
from pathlib import Path

# 必须在 import litellm 前设置，否则收集阶段会联网拉模型价目表（无网时挂起）
os.environ.setdefault("LITELLM_LOCAL_MODEL_COST_MAP", "True")
os.environ.setdefault("LITELLM_LOG", "ERROR")

import pytest

from app.providers import http as http_pool

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
