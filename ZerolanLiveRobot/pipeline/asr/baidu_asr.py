import base64
import json
import os.path
import uuid
from io import BytesIO
from typing import List, Generator

import librosa
import requests
import soundfile as sf
from pydantic import BaseModel
from typeguard import typechecked
from zerolan.data.pipeline.asr import ASRQuery, ASRPrediction, ASRStreamQuery

from common.io.api import save_audio
from common.io.file_type import AudioFileType
from pipeline.utils.baidu_auth import get_baidu_access_token


class BaiduTTSResponse(BaseModel):
    corpus_no: str
    err_msg: str
    err_no: int
    result: List[str]
    sn: str


class BaiduASRPipeline:

    def __init__(self, api_key, secret_key):
        self._access_token = get_baidu_access_token(api_key, secret_key)
        self._cuid = str(uuid.uuid4())

    @typechecked
    def predict(self, query: ASRQuery):
        if not os.path.exists(query.audio_path):
            raise FileNotFoundError(f"{query.audio_path} does not exist!")
        if self._access_token is None:
            raise ValueError("Baidu access token is not initialized")
        url = "https://vop.baidu.com/server_api"

        if query.channels > 1:
            data, sr = librosa.load(query.audio_path, mono=True)
            memory_file = BytesIO()
            sf.write(memory_file, data, sr, format=query.media_type)
            memory_file.seek(0)  # Reset pointer to beginning
            data = memory_file.read()
        else:
            with open(query.audio_path, "rb") as f:
                data = f.read()

        data_len = len(data)
        audio_base64 = base64.b64encode(data).decode('utf-8')

        payload = json.dumps({
            "format": query.media_type,
            "rate": query.sample_rate,
            "channel": 1,
            "cuid": self._cuid,
            "speech": audio_base64,
            "len": data_len,
            "token": self._access_token
        }, ensure_ascii=False)
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        response = requests.request("POST", url, headers=headers, data=payload.encode("utf-8"))
        response.raise_for_status()
        response = json.loads(response.text)

        if response['err_no'] != 0:
            raise Exception(response)

        return ASRPrediction(transcript=response['result'][0])

    def stream_predict(self, query: ASRStreamQuery, chunk_size: int | None = None) -> Generator[
        ASRPrediction, None, None]:
        audio_path = save_audio(query.audio_data, AudioFileType.WAV, prefix="asr")
        yield self.predict(ASRQuery(
            audio_path=str(audio_path),
            media_type=query.media_type,
            sample_rate=query.sample_rate,
            channels=query.channels,
        ))
