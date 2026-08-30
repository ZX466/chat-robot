"""火山引擎 BigASR（大模型录音文件识别）适配，httpx 异步。

原实现：ZerolanLiveRobot/pipeline/asr/bigasr_asr.py（requests 同步 + time.sleep 轮询）。
状态码：20000000=完成、20000003=静音、20000001/20000002/空=进行中。
差异说明：提交阶段除 20000000 外兼容 20000001（任务已受理）为成功——
旧实现在提交阶段将 20000001 判为失败，与火山文档不符，此处已修正。
"""

import asyncio
import base64
import uuid

import httpx
from loguru import logger

from ..config import VolcanoASRConfig
from ..http import get_shared_client

_STATUS_DONE = "20000000"
_STATUS_ACCEPTED = "20000001"
_STATUS_SILENT = "20000003"
_STATUS_PENDING = {"20000001", "20000002", ""}


class VolcanoASRError(RuntimeError):
    """BigASR 提交或识别失败。"""


class VolcanoASRProvider:
    def __init__(
        self,
        config: VolcanoASRConfig,
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
        """提交音频并轮询识别结果，返回转写文本。"""
        if not audio:
            raise ValueError("audio bytes must not be empty")
        if not self._config.api_key:
            raise ValueError("Volcano BigASR api_key must be provided")

        request_id = str(uuid.uuid4())
        await self._submit(audio, fmt, sample_rate, channels, request_id)
        return await self._poll(request_id)

    async def _submit(
        self,
        audio: bytes,
        fmt: str,
        sample_rate: int,
        channels: int,
        request_id: str,
    ) -> None:
        payload = {
            "user": {"uid": self._config.uid},
            "audio": {
                "data": base64.b64encode(audio).decode("ascii"),
                "format": fmt,
                "codec": "raw",
                "rate": sample_rate,
                "bits": 16,
                "channel": channels,
            },
            "request": {
                "model_name": self._config.model,
                "enable_itn": True,
                "enable_punc": False,
                "enable_ddc": False,
                "enable_speaker_info": False,
                "enable_channel_split": False,
                "show_utterances": False,
                "vad_segment": False,
                "sensitive_words_filter": "",
            },
        }
        response = await self._client.post(
            self._config.base_url + self._config.submit_path,
            headers=self._headers(request_id, sequence="-1"),
            json=payload,
        )
        response.raise_for_status()
        status = response.headers.get("X-Api-Status-Code", "")
        if status and status not in (_STATUS_DONE, _STATUS_ACCEPTED):
            raise VolcanoASRError(
                f"BigASR submit failed: status_code={status} "
                f"message={response.headers.get('X-Api-Message', '')}"
            )
        logger.debug("BigASR submitted: request_id={} status={}", request_id, status)

    async def _poll(self, request_id: str) -> str:
        headers = self._headers(request_id)
        for attempt in range(1, self._config.max_poll_times + 1):
            await asyncio.sleep(self._config.poll_interval)
            response = await self._client.post(
                self._config.base_url + self._config.query_path,
                headers=headers,
                json={},
            )
            response.raise_for_status()
            status = response.headers.get("X-Api-Status-Code", "")
            data = response.json()

            if status == _STATUS_DONE:
                result = data.get("result") or {}
                transcript = result.get("text") or ""
                if not transcript:
                    utterances = result.get("utterances") or []
                    transcript = " ".join(
                        str(u.get("text", "")) for u in utterances
                    ).strip()
                logger.info("BigASR transcript: {}", transcript)
                return transcript
            if status == _STATUS_SILENT:
                logger.warning("BigASR detected silent audio, returning empty transcript")
                return ""
            if status not in _STATUS_PENDING:
                raise VolcanoASRError(
                    f"BigASR recognition failed: status_code={status} "
                    f"message={response.headers.get('X-Api-Message', 'Unknown error')}"
                )
            logger.debug(
                "BigASR polling {}/{} status={}",
                attempt,
                self._config.max_poll_times,
                status,
            )
        raise TimeoutError(
            f"BigASR recognition timed out after {self._config.max_poll_times} polls"
        )

    def _headers(self, request_id: str, *, sequence: str | None = None) -> dict[str, str]:
        headers = {
            "Content-Type": "application/json",
            "x-api-key": self._config.api_key,
            "X-Api-Resource-Id": self._config.resource_id,
            "X-Api-Request-Id": request_id,
        }
        if sequence is not None:
            headers["X-Api-Sequence"] = sequence
        return headers
