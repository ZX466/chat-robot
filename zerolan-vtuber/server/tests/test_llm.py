"""LLMProvider 契约测试。

litellm 传输层不保证走 httpx（respx 拦截不可靠），
因此测试工具侧：ToolCallAggregator 聚合、rebuild 热替换、Router 构建。
实际 acompletion 调用路径由 Codex 评审 + E2E 验证覆盖。
"""

from app.config import LLMConfig
from app.providers.llm import LLMProvider, ToolCallAggregator, ToolCallDelta


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
    provider.rebuild(
        base_url="https://new.test/v1", api_key="new-key", model="openai/gpt-5"
    )
    assert provider._config.model == "openai/gpt-5"
    assert provider._config.api_key == "new-key"
    assert provider._config.base_url == "https://new.test/v1"


def test_router_built_with_fallbacks() -> None:
    provider = make_provider(
        model="deepseek/deepseek-chat", fallback_models=["openai/gpt-4o-mini"]
    )
    assert provider._router is not None

    provider2 = make_provider(model="deepseek/deepseek-chat", fallback_models=[])
    assert provider2._router is None
