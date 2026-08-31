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


class ProviderMask(BaseModel):
    """provider 掩码：{provider, masked}，永不暴露 key 明文（spec §3.1）。"""

    provider: str
    masked: str


class ServerHelloData(BaseModel):
    """client_hello → server_hello 载荷（spec §3.1 结构）。

    ws_port/res_port 供客户端端口配置；providers 为三组 {provider, masked} 掩码。
    """

    ws_port: int
    res_port: int
    ws_url: str
    http_url: str
    providers: dict[str, ProviderMask]  # {llm, asr, tts}


class UpdateProviderConfigData(BaseModel):
    """update_provider_config 载荷（§7，key 仅存服务端）。"""

    llm: dict[str, str] | None = None  # {base_url, api_key, model}
    asr: dict[str, str] | None = None  # {vendor, base_url, api_key, model}
    tts: dict[str, str] | None = None  # {vendor, base_url, api_key, model}


class PlaySpeechData(BaseModel):
    """play_speech 载荷：TTS 音频元信息 + HTTP 下载地址（客户端 DTO 全字段）。"""

    bot_id: str
    bot_display_name: str
    file_id: str  # 音频下载凭据（GET /resource/file?file_id=）
    transcript: str
    audio_type: str
    duration: float  # 秒
    channels: int
    sample_rate: int
    url: str
