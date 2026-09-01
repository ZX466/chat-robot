"""agent_loop：最多 3 轮工具调用循环（§5）。

- 单工具执行超时 10s
- 工具结果注入前截断至 2000 字符
- 全过程结构化日志
"""

import asyncio
import json
from dataclasses import dataclass, field
from typing import Any

from loguru import logger

from app.providers.llm import LLMProvider, ToolCall
from app.tools.registry import ToolRegistry

MAX_TOOL_ROUNDS = 3
TOOL_TIMEOUT = 10.0
RESULT_TRUNCATE = 2000


@dataclass
class AgentResult:
    content: str = ""
    rounds: int = 0
    tool_calls: list[ToolCall] = field(default_factory=list)


def _truncate(text: str, limit: int = RESULT_TRUNCATE) -> str:
    if len(text) <= limit:
        return text
    return text[:limit] + f"...[truncated {len(text) - limit} chars]"


class AgentLoop:
    def __init__(self, provider: LLMProvider, registry: ToolRegistry) -> None:
        self._provider = provider
        self._registry = registry

    def rebuild_provider(
        self, *, base_url: str | None = None, api_key: str | None = None, model: str | None = None
    ) -> None:
        """§7 热替换：重建 LLM provider（Router 重新构建），后续对话生效。"""
        self._provider.rebuild(base_url=base_url, api_key=api_key, model=model)

    async def run(self, messages: list[dict[str, Any]]) -> AgentResult:
        """输入初始 messages，最多 3 轮工具调用后返回最终文本。"""
        result = AgentResult()
        history: list[dict[str, Any]] = list(messages)

        for round_idx in range(1, MAX_TOOL_ROUNDS + 1):
            response = await self._provider.acompletion(
                history, tools=self._registry.litellm_tools()
            )
            if response.content:
                history.append({"role": "assistant", "content": response.content})

            if not response.tool_calls:
                result.content = response.content
                result.rounds = round_idx
                return result

            result.tool_calls.extend(response.tool_calls)
            logger.info(
                "agent_loop round {}/{}: {} tool calls",
                round_idx,
                MAX_TOOL_ROUNDS,
                len(response.tool_calls),
            )

            history.append(
                {
                    "role": "assistant",
                    "content": response.content,
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {"name": tc.name, "arguments": tc.arguments},
                        }
                        for tc in response.tool_calls
                    ],
                }
            )

            results = await asyncio.gather(*[self._invoke(tc) for tc in response.tool_calls])
            history.extend(results)

        # 3 轮后仍无纯文本回复：取最后一轮内容
        last = history[-1]
        result.content = last.get("content", "") if isinstance(last, dict) else ""
        result.rounds = MAX_TOOL_ROUNDS
        logger.warning("agent_loop exhausted {} rounds", MAX_TOOL_ROUNDS)
        return result

    async def _invoke(self, tc: ToolCall) -> dict[str, str]:
        try:
            arguments = json.loads(tc.arguments or "{}")
            if not isinstance(arguments, dict):
                arguments = {}
        except json.JSONDecodeError:
            arguments = {}
        output = await asyncio.wait_for(
            self._registry.invoke(tc.name, arguments), timeout=TOOL_TIMEOUT
        )
        return {"role": "tool", "tool_call_id": tc.id, "content": _truncate(output)}
