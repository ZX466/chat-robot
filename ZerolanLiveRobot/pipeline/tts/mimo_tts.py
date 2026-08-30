import base64

import requests
from loguru import logger
from zerolan.data.pipeline.tts import TTSQuery, TTSPrediction

from pipeline.tts.config import MimoTTSConfig


class MimoTTSPipeline:
    def __init__(self, config: MimoTTSConfig):
        self._api_key = config.api_key
        self._api_url = config.api_url
        self._model = config.model
        self._voice = config.voice
        self._audio_format = config.audio_format
        self._tone_prompt = config.tone_prompt

    def predict(self, query: TTSQuery) -> TTSPrediction:
        if not self._api_key:
            raise ValueError("Mimo API key must be provided!")

        tone = self._tone_prompt or "Neutral, natural speaking tone."

        payload = {
            "model": self._model,
            "messages": [
                {"role": "user", "content": tone},
                {"role": "assistant", "content": query.text}
            ],
            "audio": {
                "format": self._audio_format,
                "voice": self._voice
            }
        }

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self._api_key}",
            "api-key": self._api_key
        }

        response = requests.post(self._api_url, headers=headers, json=payload)
        response.raise_for_status()

        content_type = response.headers.get("Content-Type", "").lower()

        if "audio" in content_type:
            return TTSPrediction(wave_data=response.content, audio_type=self._audio_format)

        result = response.json()
        audio_b64 = (
            result.get("choices", [{}])[0]
            .get("message", {})
            .get("audio", {})
            .get("data", "")
        )
        if not audio_b64:
            raise ValueError(f"Mimo TTS response missing audio data: {result}")

        wave_data = base64.b64decode(audio_b64)
        logger.info(f"Mimo TTS generated {len(wave_data)} bytes of audio")
        return TTSPrediction(wave_data=wave_data, audio_type=self._audio_format)

    def stream_predict(self, *args, **kwargs):
        raise NotImplementedError("Mimo stream TTS is not supported.")
