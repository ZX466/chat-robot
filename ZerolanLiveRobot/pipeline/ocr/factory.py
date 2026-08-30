from pipeline.ocr.config import OCRPipelineConfig, OCRModelIdEnum
from pipeline.ocr.ocr_async import OCRAsyncPipeline
from pipeline.ocr.deepseek_ocr import DeepSeekOCRPipeline

def create_ocr_pipeline(config: OCRPipelineConfig):
    if config.model_id == OCRModelIdEnum.PaddleOCR:
        return OCRAsyncPipeline(config)
    elif config.model_id == OCRModelIdEnum.DeepSeekOCR:
        return DeepSeekOCRPipeline(config)
    else:
        raise ValueError(f"Unsupported OCR model: {config.model_id}")
