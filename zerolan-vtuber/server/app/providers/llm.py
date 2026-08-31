"""LLM Provider：litellm 封装（唯一 LLM 入口，§4.1）。

- acompletion / stream_completion 唯一入口，内部调 litellm。
- fallback_models → litellm.Router 降级。
- 流式 tool_call 增量片段聚合（litellm 已统一格式）。
- 运行时热替换：rebuild() 重建调参，无需重启。
"""

from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import litellm
from loguru import logger

from app.config import LLMConfig
from app.providers.http import get_shared_client

if TYPE_CHECKING:
    from litellm import Router  # type: ignore[attr-defined]
else:
    Router = litellm.Router  # type: ignore[attr-defined]

litellm.set_verbose = False  # type: ignore[attr-defined]


@dataclass(frozen=True)
class ToolCall:
    id: str
    name: str
    arguments: str  # JSON 字符串（工具侧再反序列化）


@dataclass
class LLMResponse:
    content: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)


@dataclass(frozen=True)
class ContentDelta:
    delta: str


@dataclass(frozen=True)
class ToolCallDelta:
    index: int
    id: str | None = None
    name: str | None = None
    arguments_delta: str = ""


StreamDelta = ContentDelta | ToolCallDelta


class LLMProvider:
    def __init__(self, config: LLMConfig) -> None:
        self._config = config
        self._router: Router | None = None
        self._rebuild_router()

    def _rebuild_router(self) -> None:
        """按当前配置重建 litellm.Router（含 fallback 降级）。"""
        model = self._config.model
        fallbacks = self._config.fallback_models
        if not fallbacks:
            self._router = None
            return
        model_list = [
            {
                "model_name": "primary",
                "litellm_params": self._litellm_params(model),
            }
        ]
        for i, fb in enumerate(fallbacks):
            model_list.append(
                {"model_name": f"fallback{i}", "litellm_params": self._litellm_params(fb)}
            )
        self._router = Router(model_list=model_list)

    def _litellm_params(self, model: str) -> dict[str, Any]:
        params: dict[str, Any] = {"model": model}
        if self._config.api_key:
            params["api_key"] = self._config.api_key
        if self._config.base_url:
            params["api_base"] = self._config.base_url
        return params

    def rebuild(
        self,
        *,
        base_url: str | None = None,
        api_key: str | None = None,
        model: str | None = None,
    ) -> None:
        """热替换 provider 调用参数（§7 update_provider_config）。"""
        if base_url is not None:
            self._config.base_url = base_url
        if api_key is not None:
            self._config.api_key = api_key
        if model is not None:
            self._config.model = model
        self._rebuild_router()
        logger.info(
            "LLM provider rebuilt: model={} base_url_configured={}",
            self._config.model,
            bool(self._config.base_url),
        )

    async def acompletion(
        self, messages: list[dict[str, str]], tools: list[dict[str, Any]] | None = None
    ) -> LLMResponse:
        kwargs: dict[str, Any] = {
            "model": self._config.model,
            "messages": messages,
            "temperature": self._config.temperature,
            "client": get_shared_client(),  # P0-2：连接池复用，避免每次新建
        }
        if tools:
            kwargs["tools"] = tools
        if self._router is not None:
            kwargs["model"] = "primary"
            response = await self._router.acompletion(**kwargs)
        else:
            if self._config.api_key:
                kwargs["api_key"] = self._config.api_key
            if self._config.base_url:
                kwargs["api_base"] = self._config.base_url
            response = await litellm.acompletion(**kwargs)

        content = ""
        tool_calls: list[ToolCall] = []
        for choice in response.choices:
            message = choice.message
            if message.content:
                content += str(message.content)
            for tc in message.tool_calls or []:
                fn = tc.function
                tool_calls.append(
                    ToolCall(id=tc.id, name=fn.name or "", arguments=fn.arguments or "{}")
                )
        return LLMResponse(content=content, tool_calls=tool_calls)

    async def stream_completion(
        self, messages: list[dict[str, str]], tools: list[dict[str, Any]] | None = None
    ) -> AsyncIterator[StreamDelta]:
        """流式产出：原文增量 ContentDelta 或 tool_call 增量 ToolCallDelta。"""
        kwargs: dict[str, Any] = {
            "model": self._config.model,
            "messages": messages,
            "temperature": self._config.temperature,
            "stream": True,
            "client": get_shared_client(),  # P0-2：连接池复用，避免每次新建
        }
        if tools:
            kwargs["tools"] = tools
        if self._router is not None:
            kwargs["model"] = "primary"
            stream = await self._router.acompletion(**kwargs)
        else:
            if self._config.api_key:
                kwargs["api_key"] = self._config.api_key
            if self._config.base_url:
                kwargs["api_base"] = self._config.base_url
            stream = await litellm.acompletion(**kwargs)

        if isinstance(stream, (dict, str)):
            # 某些失败路径返回非流式对象，统一抛错
            raise ValueError(f"litellm stream call returned non-stream result: {stream}")

        async for chunk in stream:
            choices = chunk.choices
            if not choices:
                continue
            choice = choices[0]
            delta = choice.delta
            if not delta:
                continue
            if delta.content:
                yield ContentDelta(delta=delta.content)
            for tc in delta.tool_calls or []:
                fn = getattr(tc, "function", None)
                fn_dict = fn if isinstance(fn, dict) else {}
                yield ToolCallDelta(
                    index=tc.index,
                    id=tc.id,
                    name=fn_dict.get("name"),
                    arguments_delta=fn_dict.get("arguments", "") or "",
                )


class ToolCallAggregator:
    """流式 tool_call 增量聚合器：完成后产出完整 ToolCall。"""

    def __init__(self) -> None:
        self._parts: dict[int, list[ToolCallDelta]] = {}

    def feed(self, delta: ToolCallDelta) -> None:
        self._parts.setdefault(delta.index, []).append(delta)

    def is_complete(self) -> bool:
        """存在带 id 的 tool_call 片段即视为已发起调用。"""
        return any(any(p.id is not None for p in parts) for parts in self._parts.values())

    def build(self) -> list[ToolCall]:
        result: list[ToolCall] = []
        for index in sorted(self._parts):
            parts = self._parts[index]
            call_id = next((p.id for p in parts if p.id), "")
            name = next((p.name for p in parts if p.name), "")
            arguments = "".join(p.arguments_delta for p in parts)
            result.append(ToolCall(id=call_id, name=name, arguments=arguments or "{}"))
        return result
