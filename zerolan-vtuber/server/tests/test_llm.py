"""LLMProvider 契约测试。

litellm 传输层不保证走 httpx（respx 拦截不可靠），
因此测试工具侧：ToolCallAggregator 聚合、rebuild 热替换、Router 构建。
实际 acompletion 调用路径由 Codex 评审 + E2E 验证覆盖。
"""

import types
from typing import Any

import pytest

from app.config import LLMConfig
from app.providers.llm import ContentDelta, LLMProvider, ToolCallAggregator, ToolCallDelta


def make_provider(**overrides: object) -> LLMProvider:
    model = overrides.pop("model", "openai/gpt-4o-mini")
    config = LLMConfig(
        model=str(model),
        base_url="https://mock-provider.test/v1",
        api_key="mock-key",
        **overrides,
    )
    return LLMProvider(config)


def test_aggregator_builds_full_tool_call() -> None:
    agg = ToolCallAggregator()
    agg.feed(ToolCallDelta(index=0, id="call_1", name="get_weather"))
    agg.feed(ToolCallDelta(index=0, arguments_delta='{"city":'))
    agg.feed(ToolCallDelta(index=0, arguments_delta=' "beijing"}'))
    calls = agg.build()
    assert len(calls) == 1
    assert calls[0].id == "call_1"
    assert calls[0].name == "get_weather"
    assert calls[0].arguments == '{"city": "beijing"}'
    assert agg.is_complete() is True


def test_aggregator_empty_returns_nothing() -> None:
    agg = ToolCallAggregator()
    assert agg.build() == []
    assert agg.is_complete() is False


def test_aggregator_multiple_calls_parallel() -> None:
    agg = ToolCallAggregator()
    agg.feed(ToolCallDelta(index=0, id="c0", name="a", arguments_delta="{}"))
    agg.feed(ToolCallDelta(index=1, id="c1", name="b", arguments_delta="{}"))
    calls = agg.build()
    assert [c.id for c in calls] == ["c0", "c1"]


def test_aggregator_orders_names() -> None:
    agg = ToolCallAggregator()
    agg.feed(ToolCallDelta(index=0, id="c0"))
    agg.feed(ToolCallDelta(index=0, name="late_name"))
    call = agg.build()[0]
    assert call.name == "late_name"  # name 可后续增量补全


def test_rebuild_updates_config() -> None:
    provider = make_provider()
    provider.rebuild(base_url="https://new.test/v1", api_key="new-key", model="openai/gpt-5")
    assert provider._config.model == "openai/gpt-5"
    assert provider._config.api_key == "new-key"
    assert provider._config.base_url == "https://new.test/v1"


def test_router_built_with_fallbacks() -> None:
    provider = make_provider(model="deepseek/deepseek-chat", fallback_models=["openai/gpt-4o-mini"])
    assert provider._router is not None

    provider2 = make_provider(model="deepseek/deepseek-chat", fallback_models=[])
    assert provider2._router is None


# --- §10：Router 降级契约 + acompletion/stream 主路径 ---


class FakeRouter:
    """记录 acompletion 调用；返回含 content + tool_calls 的假响应。"""

    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    async def acompletion(self, **kwargs: Any) -> Any:
        self.calls.append(kwargs)
        tc = types.SimpleNamespace(
            message=types.SimpleNamespace(
                content="你好",
                tool_calls=[
                    types.SimpleNamespace(
                        id="c1",
                        function=types.SimpleNamespace(
                            name="web_search", arguments='{"query":"x"}'
                        ),
                    )
                ],
            )
        )
        return types.SimpleNamespace(choices=[tc])


@pytest.mark.asyncio
async def test_acompletion_via_router_primary_alias() -> None:
    """Router 降级契约：有 fallback 时经 Router 调用，model 重写为 primary 别名。"""
    provider = make_provider(
        model="deepseek/deepseek-chat", fallback_models=["openai/gpt-4o-mini"]
    )
    router = FakeRouter()
    provider._router = router  # noqa: SLF001 — 注入替身验证委托
    resp = await provider.acompletion(
        [{"role": "user", "content": "hi"}], tools=[{"type": "function"}]
    )
    call = router.calls[0]
    assert call["model"] == "primary"
    assert call["tools"] == [{"type": "function"}]
    assert resp.content == "你好"
    assert resp.tool_calls[0].id == "c1"
    assert resp.tool_calls[0].name == "web_search"
    assert resp.tool_calls[0].arguments == '{"query":"x"}'


@pytest.mark.asyncio
async def test_acompletion_via_litellm_direct(monkeypatch: pytest.MonkeyPatch) -> None:
    provider = make_provider(fallback_models=[])
    captured: dict[str, Any] = {}

    async def fake_acompletion(**kwargs: Any) -> Any:
        captured.update(kwargs)
        return types.SimpleNamespace(
            choices=[
                types.SimpleNamespace(
                    message=types.SimpleNamespace(content="direct", tool_calls=None)
                )
            ]
        )

    monkeypatch.setattr("app.providers.llm.litellm.acompletion", fake_acompletion)
    resp = await provider.acompletion([{"role": "user", "content": "hi"}])
    assert resp.content == "direct"
    assert captured["api_key"] == "mock-key"
    assert captured["api_base"] == "https://mock-provider.test/v1"


@pytest.mark.asyncio
async def test_stream_completion_yields_deltas(monkeypatch: pytest.MonkeyPatch) -> None:
    provider = make_provider(fallback_models=[])
    stream = [
        types.SimpleNamespace(
            choices=[
                types.SimpleNamespace(
                    delta=types.SimpleNamespace(content="你", tool_calls=None)
                )
            ]
        ),
        types.SimpleNamespace(
            choices=[
                types.SimpleNamespace(
                    delta=types.SimpleNamespace(
                        content=None,
                        tool_calls=[
                            types.SimpleNamespace(
                                index=0,
                                id="c1",
                                function={"name": "web_search", "arguments": '{"q":'},
                            )
                        ],
                    )
                )
            ]
        ),
        types.SimpleNamespace(choices=[]),
    ]

    async def fake_stream(**kwargs: Any) -> Any:
        async def gen() -> Any:
            for chunk in stream:
                yield chunk

        return gen()

    monkeypatch.setattr("app.providers.llm.litellm.acompletion", fake_stream)
    deltas = [d async for d in provider.stream_completion([{"role": "user", "content": "hi"}])]
    contents = [d.delta for d in deltas if isinstance(d, ContentDelta)]
    assert contents == ["你"]
    tcs = [d for d in deltas if isinstance(d, ToolCallDelta)]
    assert tcs[0].id == "c1"
    assert tcs[0].name == "web_search"
    assert tcs[0].arguments_delta == '{"q":'


@pytest.mark.asyncio
async def test_stream_completion_non_stream_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    provider = make_provider(fallback_models=[])

    async def fake_stream(**kwargs: Any) -> dict[str, str]:
        return {"error": "not stream"}

    monkeypatch.setattr("app.providers.llm.litellm.acompletion", fake_stream)
    with pytest.raises(ValueError):
        [d async for d in provider.stream_completion([{"role": "user", "content": "hi"}])]
