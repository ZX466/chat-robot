import base64
import json
import os.path
import time
import uuid
from typing import Generator

import requests
from loguru import logger
from typeguard import typechecked
from zerolan.data.pipeline.asr import ASRQuery, ASRPrediction, ASRStreamQuery

from common.io.api import save_audio
from common.io.file_type import AudioFileType
from pipeline.asr.config import BigASRConfig


class BigASRPipeline:
    def __init__(self, config: BigASRConfig):
        self._api_key = config.api_key
        self._resource_id = config.resource_id
        self._submit_url = config.submit_url
        self._query_url = config.query_url
        self._poll_interval = config.poll_interval
        self._max_poll_times = config.max_poll_times

    @typechecked
    def predict(self, query: ASRQuery) -> ASRPrediction:
        if not os.path.exists(query.audio_path):
            raise FileNotFoundError(f"{query.audio_path} does not exist!")
        if not self._api_key:
            raise ValueError("API key must be provided!")

        request_id = str(uuid.uuid4())

        audio_base64 = self._encode_audio(query.audio_path)

        submit_payload = {
            "user": {"uid": "ZerolanLiveRobot"},
            "audio": {
                "data": audio_base64,
                "format": query.media_type,
                "codec": "raw",
                "rate": query.sample_rate,
                "bits": 16,
                "channel": query.channels
            },
            "request": {
                "model_name": "bigmodel",
                "enable_itn": True,
                "enable_punc": False,
                "enable_ddc": False,
                "enable_speaker_info": False,
                "enable_channel_split": False,
                "show_utterances": False,
                "vad_segment": False,
                "sensitive_words_filter": ""
            }
        }

        submit_headers = {
            'Content-Type': 'application/json',
            'x-api-key': self._api_key,
            'X-Api-Resource-Id': self._resource_id,
            'X-Api-Request-Id': request_id,
            'X-Api-Sequence': '-1'
        }

        submit_resp = requests.post(self._submit_url, headers=submit_headers, json=submit_payload, timeout=30)
        submit_resp.raise_for_status()
        submit_status = submit_resp.headers.get('X-Api-Status-Code', '')
        if submit_status and submit_status != '20000000':
            raise Exception(f"BigASR submit failed, status_code={submit_status}, "
                            f"message={submit_resp.headers.get('X-Api-Message', '')}")
        logger.debug(f"BigASR submit response: {submit_resp.text}, "
                     f"status_code={submit_status}")

        transcript = self._poll_query(request_id)
        return ASRPrediction(transcript=transcript)

    @typechecked
    def stream_predict(self, query: ASRStreamQuery, chunk_size: int | None = None) -> Generator[
        ASRPrediction, None, None]:
        audio_path = save_audio(query.audio_data, AudioFileType.WAV, prefix="asr")
        yield self.predict(ASRQuery(
            audio_path=str(audio_path),
            media_type=query.media_type,
            sample_rate=query.sample_rate,
            channels=query.channels,
        ))

    def _encode_audio(self, audio_path: str) -> str:
        with open(audio_path, "rb") as f:
            data = f.read()
        return base64.b64encode(data).decode('utf-8')

    def _poll_query(self, request_id: str) -> str:
        query_headers = {
            'Content-Type': 'application/json',
            'x-api-key': self._api_key,
            'X-Api-Resource-Id': self._resource_id,
            'X-Api-Request-Id': request_id
        }

        for i in range(self._max_poll_times):
            time.sleep(self._poll_interval)
            query_resp = requests.post(self._query_url, headers=query_headers, json={}, timeout=10)
            query_resp.raise_for_status()

            status_code = query_resp.headers.get('X-Api-Status-Code', '')
            result = query_resp.json()
            logger.debug(f"BigASR query response: {result}, status_code={status_code}")

            if status_code == '20000000':
                result_data = result.get("result", {})
                transcript = result_data.get("text", "")
                utterances = result_data.get("utterances", [])
                if not transcript and utterances:
                    transcript = " ".join([u.get("text", "") for u in utterances])
                logger.info(f"BigASR recognition completed: {transcript}")
                return transcript
            elif status_code == '20000003':
                logger.warning("BigASR detected silent audio, returning empty transcript")
                return ""
            elif status_code not in ('20000001', '20000002', ''):
                error_msg = query_resp.headers.get('X-Api-Message', 'Unknown error')
                raise Exception(f"BigASR recognition failed, "
                                f"status_code={status_code}, message={error_msg}")
            else:
                logger.debug(f"BigASR polling... ({i + 1}/{self._max_poll_times}), "
                             f"status_code={status_code}")

        raise TimeoutError(f"BigASR recognition timed out after {self._max_poll_times} attempts")
