"""Zerolan 协议数据模型（从 zerolan-data 精简并入，pydantic v2）。

WS 消息信封 `ZerolanProtocol` 与 Unity 客户端 Route.cs 保持一致，
现有 action 语义不得变更（兼容红线，见 REFACTOR_PROMPT §7/§12）。
"""

from enum import StrEnum
from typing import Any

from pydantic import BaseModel


class RoleEnum(StrEnum):
    system = "system"
    user = "user"
    assistant = "assistant"
    function = "function"


class Conversation(BaseModel):
    """单轮会话消息（LLM 历史）。"""

    role: RoleEnum
    content: str
    metadata: str | None = None


class ZerolanProtocol(BaseModel):
    """WS 消息信封，字段与 Route.cs 现有解析完全一致。"""

    protocol: str = "ZerolanProtocol"
    version: str = "1.1"
    message: str
    action: str
    code: int
    data: Any = None


# --- 各 action 的 data 载荷（data 形状待 kiro 规格清单产出后核对） ---


class ServerHelloData(BaseModel):
    """client_hello → server_hello 载荷。

    含 ws/http 服务地址与三组 provider 掩码（如 deepseek/k***）供客户端回显。
    """

    ws_url: str
    http_url: str
    llm_provider: str | None
    asr_provider: str | None
    tts_provider: str | None


class UpdateProviderConfigData(BaseModel):
    """update_provider_config 载荷（§7，key 仅存服务端）。"""

    llm: dict[str, str] | None = None  # {base_url, api_key, model}
    asr: dict[str, str] | None = None  # {vendor, base_url, api_key, model}
    tts: dict[str, str] | None = None  # {vendor, base_url, api_key, model}


class PlaySpeechData(BaseModel):
    """play_speech 载荷：TTS 音频的 HTTP 下载地址。"""

    url: str
    duration_ms: int | None = None
