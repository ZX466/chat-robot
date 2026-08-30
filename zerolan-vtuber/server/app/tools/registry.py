"""ToolRegistry：每个 Tool = {name, description, parameters(JSON Schema), handler}。

pydantic 模型自动生成 JSON Schema，直接传 litellm tools 参数（§5）。
"""

import inspect
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, TypeVar

from pydantic import BaseModel

F = TypeVar("F", bound=Callable[..., Any])


@dataclass(frozen=True)
class Tool:
    name: str
    description: str
    parameters: dict[str, Any]
    handler: Callable[..., Any]

    def to_litellm(self) -> dict[str, Any]:
        """转 litellm 工具参数格式。"""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }


def tool_from_model(schema: type[BaseModel]) -> Callable[[F], F]:
    """装饰器：以 pydantic 模型生成 JSON Schema，注册到 ToolRegistry。"""

    def decorator(fn: F) -> F:
        registry.register(
            Tool(
                name=fn.__name__,
                description=(inspect.getdoc(fn) or "").strip().splitlines()[0],
                parameters=schema.model_json_schema(),
                handler=fn,
            )
        )
        return fn

    return decorator


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        self._tools[tool.name] = tool

    def get(self, name: str) -> Tool:
        return self._tools[name]

    def all(self) -> list[Tool]:
        return list(self._tools.values())

    def litellm_tools(self) -> list[dict[str, Any]]:
        return [t.to_litellm() for t in self._tools.values()]

    async def invoke(self, name: str, arguments: dict[str, Any]) -> str:
        """执行工具，成功返回字符串结果；异常返回错误文本（不冒泡）。"""
        tool = self._tools[name]
        try:
            result = tool.handler(**arguments)
            if inspect.isawaitable(result):
                result = await result
            return str(result)
        except Exception as exc:  # noqa: BLE001 — 工具错误转文本回给 LLM
            return f"Error executing tool {name}: {type(exc).__name__}: {exc}"


registry = ToolRegistry()
