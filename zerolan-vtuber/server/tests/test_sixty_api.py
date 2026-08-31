"""60s API 契约测试（respx mock httpx）。

真实响应样本放 tests/fixtures/，此处验证客户端逻辑。
"""

import httpx
import pytest
import respx

from app.tools.sixty_api import SixtyApiClient, SixtyApiError


@pytest.fixture
def api_client() -> SixtyApiClient:
    return SixtyApiClient(client=httpx.AsyncClient(timeout=5.0))


@pytest.mark.asyncio
@respx.mock
async def test_get_daily_news(api_client: SixtyApiClient) -> None:
    # /v2/60s?encoding=markdown 返回纯文本（非 JSON）
    respx.get("https://60s.viki.moe/v2/60s").mock(
        return_value=httpx.Response(200, text="2024年1月1日\n新闻1\n新闻2")
    )
    result = await api_client.get_daily_news()
    assert "新闻1" in result
    assert "新闻2" in result


@pytest.mark.asyncio
@respx.mock
async def test_get_hot_list_bili(api_client: SixtyApiClient) -> None:
    respx.get("https://60s.viki.moe/v2/bili").mock(
        return_value=httpx.Response(200, json={"code": 200, "message": "ok", "data": ["item1", "item2"]})
    )
    result = await api_client.get_hot_list("bili")
    assert "1. item1" in result
    assert "2. item2" in result


@pytest.mark.asyncio
@respx.mock
async def test_get_hot_list_rednote(api_client: SixtyApiClient) -> None:
    respx.get("https://60s.viki.moe/v2/rednote").mock(
        return_value=httpx.Response(200, json={"code": 200, "message": "ok", "data": ["笔记1", "笔记2"]})
    )
    result = await api_client.get_hot_list("rednote")
    assert "1. 笔记1" in result
    assert "2. 笔记2" in result


@pytest.mark.asyncio
@respx.mock
async def test_get_hot_list_invalid_platform(api_client: SixtyApiClient) -> None:
    result = await api_client.get_hot_list("invalid")
    assert "Invalid platform" in result


@pytest.mark.asyncio
@respx.mock
async def test_get_weather(api_client: SixtyApiClient) -> None:
    respx.get("https://60s.viki.moe/v2/weather").mock(
        return_value=httpx.Response(200, json={"code": 200, "message": "ok", "data": {"city": "北京", "temp": "25°C"}})
    )
    result = await api_client.get_weather("北京")
    assert "city: 北京" in result
    assert "temp: 25°C" in result


@pytest.mark.asyncio
@respx.mock
async def test_get_epic_free(api_client: SixtyApiClient) -> None:
    respx.get("https://60s.viki.moe/v2/epic").mock(
        return_value=httpx.Response(200, json={"code": 200, "message": "ok", "data": ["Game A", "Game B"]})
    )
    result = await api_client.get_epic_free()
    assert "- Game A" in result
    assert "- Game B" in result


@pytest.mark.asyncio
@respx.mock
async def test_get_exchange_rate(api_client: SixtyApiClient) -> None:
    respx.get("https://60s.viki.moe/v2/exchange-rate").mock(
        return_value=httpx.Response(200, json={"code": 200, "message": "ok", "data": {"USD": 7.2, "EUR": 7.8}})
    )
    result = await api_client.get_exchange_rate()
    assert "USD: 7.2" in result


@pytest.mark.asyncio
@respx.mock
async def test_get_hitokoto(api_client: SixtyApiClient) -> None:
    respx.get("https://60s.viki.moe/v2/hitokoto").mock(
        return_value=httpx.Response(200, json={"code": 200, "message": "ok", "data": {"hitokoto": "人生苦短"}})
    )
    result = await api_client.get_hitokoto()
    assert result == "人生苦短"


@pytest.mark.asyncio
@respx.mock
async def test_get_moyu(api_client: SixtyApiClient) -> None:
    respx.get("https://60s.viki.moe/v2/moyu").mock(
        return_value=httpx.Response(200, json={"code": 200, "message": "ok", "data": ["摸鱼1", "摸鱼2"]})
    )
    result = await api_client.get_moyu()
    assert result == "摸鱼1\n摸鱼2"


@pytest.mark.asyncio
@respx.mock
async def test_api_error(api_client: SixtyApiClient) -> None:
    # 测试非 200 响应码的错误处理
    respx.get("https://60s.viki.moe/v2/bili").mock(
        return_value=httpx.Response(200, json={"code": 400, "message": "bad request", "data": None})
    )
    with pytest.raises(SixtyApiError, match="code=400"):
        await api_client.get_hot_list("bili")


@pytest.mark.asyncio
@respx.mock
async def test_cache_hit(api_client: SixtyApiClient) -> None:
    # 测试缓存命中：第二次调用不发送请求
    route = respx.get("https://60s.viki.moe/v2/bili").mock(
        return_value=httpx.Response(200, json={"code": 200, "message": "ok", "data": ["cached"]})
    )
    await api_client.get_hot_list("bili")
    await api_client.get_hot_list("bili")
    assert route.call_count == 1


@pytest.mark.asyncio
async def test_close_client() -> None:
    # 外部传入的 client 不归 SixtyApiClient 管理
    client = httpx.AsyncClient()
    api = SixtyApiClient(client=client)
    await api.close()
    assert api._client is not None  # 仍持有引用，调用者负责关闭
