import os

from requests import Response
from zerolan.data.pipeline.vid_cap import VidCapQuery, VidCapPrediction

from pipeline.base.base_sync import CommonModelPipeline
from pipeline.vidcap.config import VidCapPipelineConfig


class VidCapSyncPipeline(CommonModelPipeline):

    def __init__(self, config: VidCapPipelineConfig):
        """
        此接口保留，但是可能会在将来废弃而放弃维护
        :param config:
        """
        super().__init__(config)

    def predict(self, query: VidCapQuery) -> VidCapPrediction | None:
        if not os.path.exists(query.vid_path):
            raise FileNotFoundError(f"视频路径不存在：{query.vid_path}")
        return super().predict(query)

    def stream_predict(self, query: VidCapQuery, chunk_size: int | None = None):
        prediction = self.predict(query)
        yield prediction

    def parse_prediction(self, response: Response) -> VidCapPrediction:
        json_val = response.content
        return VidCapPrediction.model_validate(json_val)
