from typing import List

from requests import Response
from zerolan.data.pipeline.ocr import OCRQuery, OCRPrediction, RegionResult

from pipeline.base.base_sync import AbstractImagePipeline
from pipeline.ocr.config import OCRPipelineConfig


class OCRSyncPipeline(AbstractImagePipeline):

    def __init__(self, config: OCRPipelineConfig):
        super().__init__(config)

    def predict(self, query: OCRQuery) -> OCRPrediction | None:
        return super().predict(query)

    def stream_predict(self, query: OCRQuery, chunk_size: int | None = None):
        prediction = self.predict(query)
        yield prediction

    def parse_query(self, query: any) -> dict:
        return super().parse_query(query)

    def parse_prediction(self, response: Response) -> OCRPrediction:
        json_val = response.content
        return OCRPrediction.model_validate_json(json_val)


def avg_confidence(p: OCRPrediction) -> float:
    if not p.region_results:
        return 0.0
    return sum(r.confidence for r in p.region_results) / len(p.region_results)


def stringify(region_results: List[RegionResult]):
    if not isinstance(region_results, list):
        raise TypeError("region_results must be a list")
    for region_result in region_results:
        if not isinstance(region_result, RegionResult):
            raise TypeError("Each item must be a RegionResult")

    return ''.join(f"[{i}] {region_result.content} \n" for i, region_result in enumerate(region_results))
