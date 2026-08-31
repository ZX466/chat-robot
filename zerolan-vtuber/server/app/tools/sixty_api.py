"""60s API 客户端（tools/sixty_api.py）。

BaseURL 可配置，默认 https://60s.viki.moe，支持自托管。
统一响应包 {code:200, message, data}；code!=200 抛 SixtyApiError。
httpx + 内存 TTL 缓存（热榜类 600s，资讯类 1800s，天气 600s）。
端点路径以 60s API 官方文档（docs.60s-api.viki.moe）为准。
"""

import time
from dataclasses import dataclass, field
from typing import Any

import httpx
from loguru import logger
from pydantic import BaseModel, Field

from app.config import settings
from app.tools.registry import Tool


class SixtyApiError(Exception):
    """60s API 响应码非 200 时抛出。"""


@dataclass
class CacheEntry:
    data: Any
    expires_at: float


class TTLCache:
    """简单内存 TTL 缓存。"""

    def __init__(self) -> None:
        self._store: dict[str, CacheEntry] = {}

    def get(self, key: str) -> Any | None:
        entry = self._store.get(key)
        if entry is None:
            return None
        if time.monotonic() > entry.expires_at:
            del self._store[key]
            return None
        return entry.data

    def set(self, key: str, data: Any, ttl: float) -> None:
        self._store[key] = CacheEntry(data=data, expires_at=time.monotonic() + ttl)

    def clear(self) -> None:
        self._store.clear()


class SixtyApiClient:
    """60s API HTTP 客户端，带 TTL 缓存。"""

    # TTL 常量（秒）
    TTL_HOT_LIST = 600.0
    TTL_NEWS = 1800.0
    TTL_WEATHER = 600.0

    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        self._client = client or httpx.AsyncClient(timeout=10.0)
        self._owns_client = client is None
        self._base_url = settings.tools.sixty_api.base_url.rstrip("/")
        self._cache = TTLCache()

    async def close(self) -> None:
        if self._owns_client and self._client is not None:
            await self._client.aclose()

    async def _request(self, path: str, cache_key: str, ttl: float) -> Any:
        """通用请求：缓存命中直接返回，否则请求并缓存。"""
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached

        url = f"{self._base_url}{path}"
        resp = await self._client.get(url)
        resp.raise_for_status()
        body = resp.json()
        code = body.get("code")
        if code != 200:
            raise SixtyApiError(f"60s API error: code={code}, message={body.get('message')}")
        data = body.get("data")
        self._cache.set(cache_key, data, ttl)
        return data

    # ---- 公开方法 ----

    async def get_daily_news(self) -> str:
        """每日60秒读世界（markdown 格式）。

        /v2/60s?encoding=markdown 返回纯文本（非 JSON），需单独处理。
        """
        cache_key = "daily_news"
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached

        url = f"{self._base_url}/v2/60s?encoding=markdown"
        resp = await self._client.get(url)
        resp.raise_for_status()
        text = resp.text
        self._cache.set(cache_key, text, self.TTL_NEWS)
        return text

    async def get_hot_list(self, platform: str) -> str:
        """各平台实时热搜。platform: bili/weibo/zhihu/douyin/toutiao/rednote。"""
        valid = ("bili", "weibo", "zhihu", "douyin", "toutiao", "rednote")
        if platform not in valid:
            return f"Invalid platform: {platform}. Valid: {', '.join(valid)}"
        data = await self._request(f"/v2/{platform}", f"hot_{platform}", self.TTL_HOT_LIST)
        if isinstance(data, list):
            lines = [f"{i+1}. {item}" for i, item in enumerate(data[:20])]
            return "\n".join(lines)
        return str(data)

    async def get_weather(self, city: str) -> str:
        """实时天气。"""
        data = await self._request(f"/v2/weather?city={city}", f"weather_{city}", self.TTL_WEATHER)
        if isinstance(data, dict):
            parts = [f"{k}: {v}" for k, v in data.items()]
            return "\n".join(parts)
        return str(data)

    async def get_epic_free(self) -> str:
        """Epic 免费游戏。"""
        data = await self._request("/v2/epic", "epic_free", self.TTL_HOT_LIST)
        if isinstance(data, list):
            lines = [f"- {item}" for item in data]
            return "\n".join(lines) if lines else "No free games currently."
        return str(data)

    async def get_exchange_rate(self) -> str:
        """汇率。"""
        data = await self._request("/v2/exchange-rate", "exchange_rate", self.TTL_HOT_LIST)
        if isinstance(data, dict):
            parts = [f"{k}: {v}" for k, v in data.items()]
            return "\n".join(parts)
        return str(data)

    async def get_hitokoto(self) -> str:
        """一言。"""
        data = await self._request("/v2/hitokoto", "hitokoto", self.TTL_HOT_LIST)
        if isinstance(data, dict):
            return data.get("hitokoto", str(data))
        return str(data)

    async def get_moyu(self) -> str:
        """摸鱼日报。"""
        data = await self._request("/v2/moyu", "moyu", self.TTL_NEWS)
        if isinstance(data, list):
            return "\n".join(data)
        return str(data)


# ---- 工具注册 ----


class DailyNewsArgs(BaseModel):
    pass


class HotListArgs(BaseModel):
    platform: str = Field(description="Platform: bili/weibo/zhihu/douyin/toutiao/rednote")


class WeatherArgs(BaseModel):
    city: str = Field(description="City name in Chinese")


class EpicFreeArgs(BaseModel):
    pass


class ExchangeRateArgs(BaseModel):
    pass


class HitokotoArgs(BaseModel):
    pass


class MoyuArgs(BaseModel):
    pass


_client: SixtyApiClient | None = None


def _get_client() -> SixtyApiClient:
    global _client
    if _client is None:
        _client = SixtyApiClient()
    return _client


async def _get_daily_news_handler() -> str:
    return await _get_client().get_daily_news()


async def _get_hot_list_handler(platform: str) -> str:
    return await _get_client().get_hot_list(platform)


async def _get_weather_handler(city: str) -> str:
    return await _get_client().get_weather(city)


async def _get_epic_free_handler() -> str:
    return await _get_client().get_epic_free()


async def _get_exchange_rate_handler() -> str:
    return await _get_client().get_exchange_rate()


async def _get_hitokoto_handler() -> str:
    return await _get_client().get_hitokoto()


async def _get_moyu_handler() -> str:
    return await _get_client().get_moyu()


def register_sixty_api(registry: Any) -> None:
    """注册 60s API 工具组。"""
    tools = [
        Tool(
            name="get_daily_news",
            description="Get 60-second daily news digest (markdown format).",
            parameters=DailyNewsArgs.model_json_schema(),
            handler=_get_daily_news_handler,
        ),
        Tool(
            name="get_hot_list",
            description="Get real-time hot list from a platform.",
            parameters=HotListArgs.model_json_schema(),
            handler=_get_hot_list_handler,
        ),
        Tool(
            name="get_weather",
            description="Get real-time weather for a city.",
            parameters=WeatherArgs.model_json_schema(),
            handler=_get_weather_handler,
        ),
        Tool(
            name="get_epic_free",
            description="Get current free games from Epic Games Store.",
            parameters=EpicFreeArgs.model_json_schema(),
            handler=_get_epic_free_handler,
        ),
        Tool(
            name="get_exchange_rate",
            description="Get current exchange rates.",
            parameters=ExchangeRateArgs.model_json_schema(),
            handler=_get_exchange_rate_handler,
        ),
        Tool(
            name="get_hitokoto",
            description="Get a random quote (hitokoto).",
            parameters=HitokotoArgs.model_json_schema(),
            handler=_get_hitokoto_handler,
        ),
        Tool(
            name="get_moyu",
            description="Get daily moyu (slacking off) report.",
            parameters=MoyuArgs.model_json_schema(),
            handler=_get_moyu_handler,
        ),
    ]
    for tool in tools:
        registry.register(tool)
