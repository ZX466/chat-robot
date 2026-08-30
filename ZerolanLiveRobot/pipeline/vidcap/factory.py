from pipeline.vidcap.config import VidCapPipelineConfig, VidCapModelIdEnum
from pipeline.vidcap.vidcap_async import VidCapAsyncPipeline
from pipeline.vidcap.doubao_vidcap import DoubaoVidCapPipeline

def create_vidcap_pipeline(config: VidCapPipelineConfig):
    if config.model_id == VidCapModelIdEnum.Hitea:
        return VidCapAsyncPipeline(config)
    elif config.model_id == VidCapModelIdEnum.DoubaoVisionPro:
        return DoubaoVidCapPipeline(config)
    else:
        raise ValueError(f"Unsupported VidCap model: {config.model_id}")
