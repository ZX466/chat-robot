"""百度语音合成（短文本在线合成）适配，httpx 异步。

原实现：ZerolanLiveRobot/pipeline/tts/baidu_tts.py（requests 同步）。
响应按 Content-Type 分流：audio/* 为音频数据；application/json|text/* 为错误。
"""

import uuid
from collections.abc import AsyncIterator

import httpx
from loguru import logger

from ..auth.baidu_token import BaiduTokenManager
from ..config import BaiduTTSConfig
from ..http import get_shared_client

_FORMAT_TO_AUE = {"mp3": 3, "pcm": 5, "wav": 6}


class BaiduTTSError(RuntimeError):
    """百度 TTS 返回非音频（JSON/text 错误）响应。"""


def _parse_per(voice: str) -> int:
    """voice 参数映射到百度音库 per（整数字符串），无法解析时回退默认 1。"""
    try:
        return int(voice)
    except (TypeError, ValueError):
        return 1


class BaiduTTSProvider:
    def __init__(
        self,
        config: BaiduTTSConfig,
        *,
        client: httpx.AsyncClient | None = None,
        token_manager: BaiduTokenManager | None = None,
    ) -> None:
        self._config = config
        self._client = client or get_shared_client()
        self._tokens = token_manager or BaiduTokenManager(
            config.api_key,
            config.secret_key,
            client=self._client,
            refresh_margin=config.token_refresh_margin,
        )
        self._cuid = str(uuid.uuid4())

    async def synthesize(self, text: str, voice: str) -> AsyncIterator[bytes]:
        """合成语音；当前为单块产出（整段音频），后续可按需切流。"""
        if not text:
            raise ValueError("text must not be empty")
        token = await self._tokens.get_token()
        payload = {
            "tex": text,
            "tok": token,
            "cuid": self._cuid,
            "ctp": 1,
            "lan": "zh",  # 百度 TTS 不支持 auto
            "spd": self._config.spd,
            "pit": self._config.pit,
            "vol": self._config.vol,
            "per": _parse_per(voice or self._config.voice),
            "aue": _FORMAT_TO_AUE[self._config.audio_format],
        }
        response = await self._client.post(
            f"{self._config.base_url}/text2audio",
            data=payload,
            headers={"Accept": "*/*"},
        )
        response.raise_for_status()

        content_type = response.headers.get("Content-Type", "").lower()
        if content_type.startswith("audio/") or "audio" in content_type:
            wave = response.content
            logger.info("Baidu TTS generated {} bytes of audio", len(wave))
            yield wave
            return

        try:
            detail = response.json()
        except ValueError:
            detail = response.text[:500]
        raise BaiduTTSError(f"Baidu TTS failed: {detail}")
