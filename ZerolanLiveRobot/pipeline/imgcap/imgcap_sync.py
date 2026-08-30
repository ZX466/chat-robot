from requests import Response
from typeguard import typechecked
from zerolan.data.pipeline.img_cap import ImgCapQuery, ImgCapPrediction

from pipeline.base.base_sync import AbstractImagePipeline
from pipeline.imgcap.config import ImgCapPipelineConfig, ImgCapModelIdEnum
from pipeline.imgcap.doubao_vision import DoubaoVisionPipeline


class ImgCapSyncPipeline(AbstractImagePipeline):

    def __init__(self, config: ImgCapPipelineConfig):
        super().__init__(config)
        if config.model_id == ImgCapModelIdEnum.DoubaoVision and config.doubao_vision_config is not None:
            self._doubao = DoubaoVisionPipeline(config=config.doubao_vision_config)
            self.predict = self._doubao.predict
            self.stream_predict = self._doubao.stream_predict

    @typechecked
    def predict(self, query: ImgCapQuery) -> ImgCapPrediction | None:
        return super().predict(query)

    @typechecked
    def stream_predict(self, query: ImgCapQuery, chunk_size: int | None = None):
        prediction = self.predict(query)
        yield prediction

    def parse_query(self, query: any) -> dict:
        return super().parse_query(query)

    def parse_prediction(self, response: Response) -> ImgCapPrediction:
        json_val = response.content
        return ImgCapPrediction.model_validate_json(json_val)
