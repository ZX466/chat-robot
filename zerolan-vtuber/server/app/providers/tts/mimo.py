"""小米 MiMo TTS（chat/completions 形态）适配，httpx 异步。

原实现：ZerolanLiveRobot/pipeline/tts/mimo_tts.py（requests 同步）。
响应两种形态：audio/* 直接返回音频；JSON 取 choices[0].message.audio.data(base64)。
"""

import base64
from collections.abc import AsyncIterator

import httpx
from loguru import logger

from ..config import MimoTTSConfig
from ..http import get_shared_client


class MimoTTSError(RuntimeError):
    """MiMo TTS 响应缺少音频数据。"""


class MimoTTSProvider:
    def __init__(
        self,
        config: MimoTTSConfig,
        *,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._config = config
        self._client = client or get_shared_client()

    async def synthesize(self, text: str, voice: str) -> AsyncIterator[bytes]:
        """合成语音；当前为单块产出，后续可按需真流式。"""
        if not self._config.api_key:
            raise ValueError("Mimo api_key must be provided")
        if not text:
            raise ValueError("text must not be empty")

        tone = self._config.tone_prompt or "Neutral, natural speaking tone."
        payload = {
            "model": self._config.model,
            "messages": [
                {"role": "user", "content": tone},
                {"role": "assistant", "content": text},
            ],
            "audio": {
                "format": self._config.audio_format,
                "voice": voice or self._config.voice,
            },
        }
        headers = {
            "Authorization": f"Bearer {self._config.api_key}",
            "api-key": self._config.api_key,
        }
        response = await self._client.post(
            self._config.base_url + self._config.api_path,
            headers=headers,
            json=payload,
        )
        response.raise_for_status()

        content_type = response.headers.get("Content-Type", "").lower()
        if "audio" in content_type:
            wave = response.content
            logger.info("Mimo TTS generated {} bytes of audio", len(wave))
            yield wave
            return

        data = response.json()
        choices = data.get("choices") or []
        audio_b64 = ""
        if choices:
            audio_b64 = (choices[0].get("message") or {}).get("audio", {}).get("data", "")
        if not audio_b64:
            raise MimoTTSError(f"Mimo TTS response missing audio data: {data}")
        wave = base64.b64decode(audio_b64)
        logger.info("Mimo TTS generated {} bytes of audio", len(wave))
        yield wave
