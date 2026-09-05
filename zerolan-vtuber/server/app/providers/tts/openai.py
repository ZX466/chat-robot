"""OpenAI 兼容 TTS 适配（/v1/audio/speech，httpx 异步）。

响应为音频字节流；当前一次性 aread 后单块产出（复用 MimoTTS 单块模式，
仅 opus 等格式才有意义真流式，后续可按需切换 aiter_bytes）。
错误处理：HTTP 4xx/5xx 或 200 但 Content-Type 非 audio → 解析 OpenAI 错误包
{"error": {message, type, code}} 抛 OpenAITTSError；错误消息不回显请求 input。
"""

from collections.abc import AsyncIterator

import httpx
from loguru import logger

from ..config import OpenAITTSConfig
from ..http import get_shared_client


class OpenAITTSError(RuntimeError):
    """OpenAI 兼容 TTS 请求失败或响应不符合契约。"""


class OpenAITTSProvider:
    def __init__(
        self,
        config: OpenAITTSConfig,
        *,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._config = config
        self._client = client or get_shared_client()

    async def synthesize(self, text: str, voice: str) -> AsyncIterator[bytes]:
        """合成语音，单块产出音频字节。voice 非空覆盖配置默认音色。"""
        if not self._config.api_key:
            raise ValueError("OpenAI api_key must be provided")
        if not text:
            raise ValueError("text must not be empty")

        payload = {
            "model": self._config.model,
            "input": text,
            "voice": voice or self._config.voice,
            "response_format": self._config.audio_format,
        }
        response = await self._client.post(
            # rstrip('/') 防用户 base_url 尾带斜杠拼出 //v1/... 双斜杠（P3-4，部分网关 404）
            self._config.base_url.rstrip("/") + self._config.api_path,
            headers={"Authorization": f"Bearer {self._config.api_key}"},
            json=payload,
        )

        content_type = response.headers.get("Content-Type", "").lower()
        if response.status_code >= 400 or "audio" not in content_type:
            self._raise_api_error(response)

        data = await response.aread()
        logger.info("OpenAI TTS generated {} bytes of audio", len(data))
        yield data

    @staticmethod
    def _raise_api_error(response: httpx.Response) -> None:
        """解析 OpenAI 错误包；不回显请求 input（codex 安全反馈）。"""
        detail = ""
        try:
            error = response.json().get("error")
            # 只取 error.message/type/code，不回显远端原始错误体（P3-1：自建网关
            # 可能回显 Authorization/input，整段透传会泄漏）
            if isinstance(error, dict):
                parts = [
                    str(error.get(key))
                    for key in ("message", "type", "code")
                    if error.get(key) is not None
                ]
                detail = ", ".join(parts)
        except ValueError:
            detail = ""
        raise OpenAITTSError(
            f"OpenAI TTS failed: HTTP {response.status_code}" + (f" ({detail})" if detail else "")
        )
