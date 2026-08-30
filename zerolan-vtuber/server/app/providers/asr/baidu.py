"""百度短语音识别（标准版）适配，httpx 异步。

原实现：ZerolanLiveRobot/pipeline/asr/baidu_asr.py（requests 同步）。
差异说明：
- 重依赖 librosa/soundfile 的多声道转单声道不在 provider 内做，调用方须传单声道音频。
"""

import base64
import uuid

import httpx
from loguru import logger

from ..auth.baidu_token import BaiduTokenManager
from ..config import BaiduASRConfig
from ..http import get_shared_client


class BaiduASRError(RuntimeError):
    """百度 ASR 返回 err_no != 0 或结果为空。"""


class BaiduASRProvider:
    def __init__(
        self,
        config: BaiduASRConfig,
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

    async def transcribe(
        self,
        audio: bytes,
        fmt: str,
        *,
        sample_rate: int = 16000,
        channels: int = 1,
    ) -> str:
        """识别整段单声道音频，返回转写文本（百度标准版仅单声道）。"""
        if not audio:
            raise ValueError("audio bytes must not be empty")
        token = await self._tokens.get_token()
        payload = {
            "format": fmt,
            "rate": sample_rate,
            "channel": channels,
            "cuid": self._cuid,
            "speech": base64.b64encode(audio).decode("ascii"),
            "len": len(audio),
            "token": token,
        }
        response = await self._client.post(f"{self._config.base_url}/server_api", json=payload)
        response.raise_for_status()
        data = response.json()
        if data.get("err_no"):
            err_no = data["err_no"]
            raise BaiduASRError(
                f"Baidu ASR failed: err_no={err_no} "
                f"err_msg={data.get('err_msg')} sn={data.get('sn')}"
            )
        result = data.get("result") or []
        if not result:
            raise BaiduASRError(f"Baidu ASR returned empty result: sn={data.get('sn')}")
        transcript = str(result[0])
        logger.info("Baidu ASR transcript: {}", transcript)
        return transcript
