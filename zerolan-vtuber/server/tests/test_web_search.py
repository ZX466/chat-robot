"""web_search 工具测试（§5）：Tavily 主路径 + ddgs 降级路径（失败自动回退）。"""

import types
from typing import Any

import pytest

from app.tools.web_search import SearchProvider, SearchResult, _web_search_handler


def fake_response(json_data: dict[str, Any]) -> Any:
    return types.SimpleNamespace(raise_for_status=lambda: None, json=lambda: json_data)


class FakeClient:
    """记录 post 调用；可注入异常模拟 Tavily 故障。"""

    def __init__(self, response: Any = None, exc: Exception | None = None) -> None:
        self._response = response
        self._exc = exc
        self.posts: list[tuple[str, dict[str, Any]]] = []

    async def post(self, url: str, **kwargs: Any) -> Any:
        self.posts.append((url, kwargs))
        if self._exc is not None:
            raise self._exc
        return self._response


@pytest.mark.asyncio
async def test_tavily_primary_path(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TAVILY_API_KEY", "tk")
    client = FakeClient(
        fake_response({"results": [{"title": "A", "url": "https://a", "content": "body"}]})
    )
    sp = SearchProvider(client=client)
    results = await sp.search("query", max_results=3)
    assert results == [SearchResult(title="A", url="https://a", snippet="body")]
    url, kwargs = client.posts[0]
    assert url == "https://api.tavily.com/search"
    assert kwargs["json"]["api_key"] == "tk"
    assert kwargs["json"]["query"] == "query"
    assert kwargs["json"]["max_results"] == 3


@pytest.mark.asyncio
async def test_no_key_falls_back_to_ddgs(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)
    captured: dict[str, Any] = {}

    async def fake_ddgs(query: str, max_results: int) -> list[SearchResult]:
        captured["query"] = query
        captured["max"] = max_results
        return [SearchResult(title="D", url="https://d", snippet="s")]

    sp = SearchProvider(client=FakeClient())
    monkeypatch.setattr(sp, "_ddgs", fake_ddgs)  # noqa: SLF001
    results = await sp.search("q", max_results=5)
    assert captured == {"query": "q", "max": 5}
    assert results[0].title == "D"


@pytest.mark.asyncio
async def test_tavily_error_falls_back_to_ddgs(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TAVILY_API_KEY", "tk")
    sp = SearchProvider(client=FakeClient(exc=RuntimeError("tavily down")))
    seen: list[str] = []

    async def fake_ddgs(query: str, max_results: int) -> list[SearchResult]:
        seen.append(query)
        return [SearchResult(title="F", url="https://f", snippet="fallback")]

    monkeypatch.setattr(sp, "_ddgs", fake_ddgs)  # noqa: SLF001
    results = await sp.search("q")
    assert seen == ["q"]
    assert results[0].title == "F"


@pytest.mark.asyncio
async def test_both_fail_returns_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TAVILY_API_KEY", "tk")
    sp = SearchProvider(client=FakeClient(exc=RuntimeError("tavily down")))

    async def fake_ddgs(query: str, max_results: int) -> list[SearchResult]:
        raise RuntimeError("ddgs also down")

    monkeypatch.setattr(sp, "_ddgs", fake_ddgs)  # noqa: SLF001
    assert await sp.search("q") == []


@pytest.mark.asyncio
async def test_handler_no_results(monkeypatch: pytest.MonkeyPatch) -> None:
    sp = SearchProvider(client=FakeClient(exc=RuntimeError("x")))

    async def fake_ddgs(query: str, max_results: int) -> list[SearchResult]:
        return []

    monkeypatch.setattr(sp, "_ddgs", fake_ddgs)  # noqa: SLF001
    monkeypatch.setattr("app.tools.web_search._get_provider", lambda: sp)
    assert await _web_search_handler("q") == "No results."


@pytest.mark.asyncio
async def test_handler_formats_results(monkeypatch: pytest.MonkeyPatch) -> None:
    sp = SearchProvider(client=FakeClient(exc=RuntimeError("x")))

    async def fake_ddgs(query: str, max_results: int) -> list[SearchResult]:
        return [SearchResult(title="T", url="https://t", snippet="sn")]

    monkeypatch.setattr(sp, "_ddgs", fake_ddgs)  # noqa: SLF001
    monkeypatch.setattr("app.tools.web_search._get_provider", lambda: sp)
    out = await _web_search_handler("q")
    assert "- T" in out
    assert "https://t" in out
    assert "sn" in out
