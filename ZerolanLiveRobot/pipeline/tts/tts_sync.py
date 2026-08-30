import os.path
import uuid
from http import HTTPStatus

import requests
from loguru import logger
from zerolan.data.pipeline.tts import TTSQuery, TTSPrediction, TTSStreamPrediction

from pipeline.base.base_sync import CommonModelPipeline
from pipeline.tts.baidu_tts import BaiduTTSPipeline
from pipeline.tts.mimo_tts import MimoTTSPipeline
from pipeline.tts.config import TTSPipelineConfig, TTSModelIdEnum


class TTSSyncPipeline(CommonModelPipeline):

    def __init__(self, config: TTSPipelineConfig):
        super().__init__(config)
        if config.model_id == TTSModelIdEnum.BaiduTTS and config.baidu_tts_config is not None:
            self.baidu = BaiduTTSPipeline(api_key=config.baidu_tts_config.api_key,
                                          secret_key=config.baidu_tts_config.secret_key)
            self.predict = self.baidu.predict
            self.stream_predict = self.baidu.stream_predict
        elif config.model_id == TTSModelIdEnum.MimoTTS and config.mimo_tts_config is not None:
            self.mimo = MimoTTSPipeline(config=config.mimo_tts_config)
            self.predict = self.mimo.predict
            self.stream_predict = self.mimo.stream_predict

    def predict(self, query: TTSQuery) -> TTSPrediction | None:
        if os.path.exists(query.refer_wav_path):
            query.refer_wav_path = os.path.abspath(query.refer_wav_path).replace("\\", "/")
        query_dict = self.parse_query(query)
        response = requests.post(url=self.predict_url, stream=True, json=query_dict)
        if response.status_code == HTTPStatus.OK:
            prediction = TTSPrediction(wave_data=response.content, audio_type=query.audio_type)
            return prediction
        else:
            logger.error(response.content)
            response.raise_for_status()

    def stream_predict(self, query: TTSQuery, chunk_size: int | None = None):
        if os.path.exists(query.refer_wav_path):
            query.refer_wav_path = os.path.abspath(query.refer_wav_path).replace("\\", "/")
        query_dict = self.parse_query(query)
        response = self._session.post(url=self.stream_predict_url, stream=True,
                                 json=query_dict, timeout=self._timeout)
        response.raise_for_status()
        last = 0
        id = str(uuid.uuid4())
        for idx, chunk in enumerate(response.iter_content(chunk_size=1024)):
            last = idx
            yield TTSStreamPrediction(seq=idx,
                                      id=id,
                                      is_final=False,
                                      wave_data=chunk,
                                      audio_type=query.audio_type)
        yield TTSStreamPrediction(is_final=True, seq=last + 1, audio_type=query.audio_type, wave_data=b'')

    def parse_query(self, query: any) -> dict:
        return super().parse_query(query)
