import httpx
import pytest
import respx

from app.providers.auth.baidu_token import TOKEN_URL, BaiduTokenError, BaiduTokenManager


@respx.mock
async def test_get_token_caches_single_request(load_fixture):
    route = respx.post(TOKEN_URL).respond(json=load_fixture("baidu_token_ok.json"))
    async with httpx.AsyncClient() as client:
        manager = BaiduTokenManager("ak", "sk", client=client)
        first = await manager.get_token()
        second = await manager.get_token()
    assert first == second == "24.abc123.def456"
    assert route.call_count == 1


@respx.mock
async def test_invalidate_triggers_refresh(load_fixture):
    route = respx.post(TOKEN_URL).respond(json=load_fixture("baidu_token_ok.json"))
    async with httpx.AsyncClient() as client:
        manager = BaiduTokenManager("ak", "sk", client=client)
        await manager.get_token()
        manager.invalidate()  # 模拟 token 过期/失效
        await manager.get_token()
    assert route.call_count == 2


@respx.mock
async def test_missing_access_token_raises(load_fixture):
    respx.post(TOKEN_URL).respond(json=load_fixture("baidu_token_error.json"))
    async with httpx.AsyncClient() as client:
        manager = BaiduTokenManager("ak", "sk", client=client)
        with pytest.raises(BaiduTokenError):
            await manager.get_token()


async def test_missing_credentials_raise_on_call():
    """部署宽容：key 空可构造（如仅配 llm 也能起服务），首次取 token 时报错。"""
    manager = BaiduTokenManager("", "sk")
    with pytest.raises(BaiduTokenError, match="must be provided"):
        await manager.get_token()
