"""ToolRegistry + AgentLoop 测试。"""

from typing import Any

import pytest
from pydantic import BaseModel

from app.core.agent_loop import MAX_TOOL_ROUNDS, AgentLoop, _truncate
from app.providers.llm import LLMResponse, ToolCall
from app.tools.registry import Tool, ToolRegistry


class EchoArgs(BaseModel):
    text: str
    times: int = 1


def test_register_and_litellm_format() -> None:
    registry = ToolRegistry()

    def echo(args: EchoArgs) -> str:
        return args.text * args.times

    registry.register(
        Tool(
            name="echo",
            description="Echo text",
            parameters=EchoArgs.model_json_schema(),
            handler=echo,
        )
    )
    spec = registry.litellm_tools()[0]
    assert spec["function"]["name"] == "echo"
    assert "text" in spec["function"]["parameters"]["properties"]


class FakeProvider:
    """模拟 LLMProvider：按序返回预设响应。"""

    def __init__(self, responses: list[LLMResponse]) -> None:
        self._responses = list(responses)
        self.calls: list[list[dict[str, Any]]] = []

    async def acompletion(
        self, messages: list[dict[str, str]], tools: list[dict[str, Any]] | None = None
    ) -> LLMResponse:
        self.calls.append(messages)
        return self._responses.pop(0)


def make_echo_registry() -> ToolRegistry:
    registry = ToolRegistry()
    registry.register(
        Tool(
            name="echo",
            description="Echo text",
            parameters=EchoArgs.model_json_schema(),
            handler=lambda text, times=1: text * times,
        )
    )
    return registry


@pytest.mark.asyncio
async def test_agent_loop_no_tools_round1() -> None:
    provider = FakeProvider([LLMResponse(content="hello")])
    loop = AgentLoop(provider, make_echo_registry())  # type: ignore[arg-type]
    result = await loop.run([{"role": "user", "content": "hi"}])
    assert result.content == "hello"
    assert result.rounds == 1


@pytest.mark.asyncio
async def test_agent_loop_rounds_and_truncate() -> None:
    provider = FakeProvider(
        [
            LLMResponse(
                content="",
                tool_calls=[ToolCall(id="t1", name="echo", arguments='{"text":"x"*3000}')],
            ),
            LLMResponse(content="done"),
        ]
    )
    registry = make_echo_registry()
    loop = AgentLoop(provider, registry)  # type: ignore[arg-type]

    # 直接验证 _truncate
    long = "a" * 2500
    assert _truncate(long) == "a" * 2000 + f"...[truncated {500} chars]"
    assert _truncate("short") == "short"

    # agent_loop 主逻辑：mock provider 但需要真实参数注入 —— 用 monkeypatch 的 _provider
    # 此处验证 truncate 与历史组装逻辑分点：结果注入长度上限在 _invoke。
    tc = ToolCall(id="t2", name="echo", arguments=f'{{"text":"{"b" * 3000}"}}')
    history = await loop._invoke(tc)
    assert history["role"] == "tool"
    assert history["content"].startswith("bbb")
    assert "...[truncated" in history["content"]


@pytest.mark.asyncio
async def test_agent_loop_max_rounds_exhausted() -> None:
    tool_call = ToolCall(id="t", name="echo", arguments='{"text":"msg"}')
    provider = FakeProvider([LLMResponse(content="", tool_calls=[tool_call])] * MAX_TOOL_ROUNDS)
    loop = AgentLoop(provider, make_echo_registry())  # type: ignore[arg-type]
    result = await loop.run([{"role": "user", "content": "hi"}])
    assert result.rounds == MAX_TOOL_ROUNDS


@pytest.mark.asyncio
async def test_agent_loop_tool_then_answer() -> None:
    tool_call = ToolCall(id="t3", name="echo", arguments='{"text":"ab","times":2}')
    provider = FakeProvider(
        [LLMResponse(content="", tool_calls=[tool_call]), LLMResponse(content="abab")]
    )
    loop = AgentLoop(provider, make_echo_registry())  # type: ignore[arg-type]
    result = await loop.run([{"role": "user", "content": "hi"}])
    assert result.content == "abab"
    assert result.rounds == 2
    assert len(result.tool_calls) == 1
    # 工具结果已注入历史
    tool_msgs = [m for m in provider.calls[-1] if m.get("role") == "tool"]
    assert tool_msgs and tool_msgs[0]["content"] == "abab"
