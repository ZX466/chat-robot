"""OpenAI 兼容 ASR 适配（/v1/audio/transcriptions，httpx 异步）。

覆盖 OpenAI whisper 及一切 OpenAI 兼容端点（siliconflow/fish-audio/自建 whisper 等）。
错误处理：HTTP 4xx/5xx 或响应缺失 text 字段 → OpenAIASRError（不回显音频内容）。
"""

from typing import ClassVar

import httpx
from loguru import logger

from ..config import OpenAIASRConfig
from ..http import get_shared_client


class OpenAIASRError(RuntimeError):
    """OpenAI 兼容 ASR 请求失败或响应不符合契约。"""


class OpenAIASRProvider:
    # 安全（codex 反馈）：上传格式白名单，防任意扩展名/内容注入到网关侧
    _ALLOWED_FMTS: ClassVar[frozenset[str]] = frozenset(
        {"wav", "mp3", "m4a", "webm", "flac", "ogg"}
    )

    def __init__(
        self,
        config: OpenAIASRConfig,
        *,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._config = config
        self._client = client or get_shared_client()

    async def transcribe(
        self,
        audio: bytes,
        fmt: str,
        *,
        sample_rate: int = 16000,
        channels: int = 1,
    ) -> str:
        """上传音频转写，返回文本。sample_rate/channels 忽略（whisper 自动重采样）。"""
        del sample_rate, channels
        if not audio:
            raise ValueError("audio bytes must not be empty")
        if not self._config.api_key:
            raise ValueError("OpenAI api_key must be provided")
        fmt_lower = fmt.lower()
        if fmt_lower not in self._ALLOWED_FMTS:
            raise OpenAIASRError(
                f"unsupported audio format: {fmt} (allowed: {sorted(self._ALLOWED_FMTS)})"
            )

        response = await self._client.post(
            self._config.base_url + self._config.api_path,
            headers={"Authorization": f"Bearer {self._config.api_key}"},
            files={"file": (f"audio.{fmt_lower}", audio)},
            data={"model": self._config.model, "response_format": self._config.response_format},
        )
        if response.status_code >= 400:
            self._raise_api_error(response)

        if self._config.response_format == "text":
            transcript = response.text.strip()
        else:  # json / verbose_json
            try:
                data = response.json()
            except ValueError as exc:
                raise OpenAIASRError(
                    f"OpenAI ASR returned non-JSON body (HTTP {response.status_code})"
                ) from exc
            transcript = str(data.get("text") or "")
        if not transcript:
            raise OpenAIASRError(
                f"OpenAI ASR returned empty transcript (HTTP {response.status_code})"
            )
        logger.info("OpenAI ASR transcript: {}", transcript)
        return transcript

    @staticmethod
    def _raise_api_error(response: httpx.Response) -> None:
        """解析 OpenAI 错误包 {"error": {message, type, code}}；不回显音频内容。"""
        detail = ""
        try:
            error = response.json().get("error")
            if isinstance(error, dict):
                parts = [
                    str(error.get(key))
                    for key in ("message", "type", "code")
                    if error.get(key) is not None
                ]
                detail = ", ".join(parts)
        except ValueError:
            detail = ""
        raise OpenAIASRError(
            f"OpenAI ASR failed: HTTP {response.status_code}" + (f" ({detail})" if detail else "")
        )
