"""web_search 工具：Tavily 为主（env: TAVILY_API_KEY），失败自动降级 ddgs（§5）。

返回 [{title, url, snippet}]，LLM 回答时口播引用来源域名。
"""

import asyncio
import os
from dataclasses import dataclass
from typing import Any

import httpx
from loguru import logger

from app.tools.registry import Tool


@dataclass(frozen=True)
class SearchResult:
    title: str
    url: str
    snippet: str


class SearchProvider:
    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        self._client = client or httpx.AsyncClient(timeout=10.0)
        self._owns_client = client is None

    async def search(self, query: str, max_results: int = 5) -> list[SearchResult]:
        tavily_key = os.getenv("TAVILY_API_KEY")
        try:
            if tavily_key:
                return await self._tavily(query, max_results, tavily_key)
            logger.debug("TAVILY_API_KEY missing, falling back to ddgs")
            return await self._ddgs(query, max_results)
        except Exception as exc:  # noqa: BLE001 — 搜索失败不阻断对话
            logger.warning("web_search failed ({}), falling back to ddgs", type(exc).__name__)
            if tavily_key:
                try:
                    return await self._ddgs(query, max_results)
                except Exception as exc2:  # noqa: BLE001
                    logger.error("ddgs fallback failed: {}", exc2)
            return []

    async def _tavily(self, query: str, max_results: int, api_key: str) -> list[SearchResult]:
        response = await self._client.post(
            "https://api.tavily.com/search",
            json={"api_key": api_key, "query": query, "max_results": max_results},
        )
        response.raise_for_status()
        data = response.json()
        return [
            SearchResult(
                title=str(item.get("title", "")),
                url=str(item.get("url", "")),
                snippet=str(item.get("content", "")),
            )
            for item in data.get("results", [])
        ]

    async def _ddgs(self, query: str, max_results: int) -> list[SearchResult]:
        from ddgs import DDGS

        def _run() -> list[dict[str, Any]]:
            return list(DDGS().text(query, max_results=max_results))

        results = await asyncio.to_thread(_run)
        return [
            SearchResult(
                title=str(item.get("title", "")),
                url=str(item.get("href", "")),
                snippet=str(item.get("body", "")),
            )
            for item in results
        ]


async def _web_search_handler(query: str, max_results: int = 5) -> str:
    results = await SearchProvider().search(query, max_results)
    if not results:
        return "No results."
    lines = [
        f"- {r.title}\n  URL: {r.url}\n  {r.snippet[:200]}" for r in results
    ]
    return "\n".join(lines)


def register_web_search(registry: Any) -> None:
    """注册 web_search 工具。pydantic JSON Schema 内联。"""
    registry.register(
        Tool(
            name="web_search",
            description=(
                "Search the web for current information. "
                "Use for recent events, unknown facts, prices, etc."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                    "max_results": {"type": "integer", "default": 5},
                },
                "required": ["query"],
            },
            handler=_web_search_handler,
        )
    )
