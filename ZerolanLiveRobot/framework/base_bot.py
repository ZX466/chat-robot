from loguru import logger

from framework.context import ZerolanLiveRobotContext
from manager.config_manager import get_config
from pipeline.asr.asr_async import ASRAsyncPipeline
from pipeline.asr.asr_sync import ASRSyncPipeline
from pipeline.db.milvus.milvus_async import MilvusAsyncPipeline
from pipeline.db.milvus.milvus_sync import MilvusSyncPipeline
from pipeline.imgcap.imgcap_async import ImgCapAsyncPipeline
from pipeline.imgcap.imgcap_sync import ImgCapSyncPipeline
from pipeline.llm.llm_async import LLMAsyncPipeline
from pipeline.llm.llm_sync import LLMSyncPipeline
from pipeline.ocr.ocr_async import OCRAsyncPipeline
from pipeline.ocr.ocr_sync import OCRSyncPipeline
from pipeline.tts.tts_async import TTSAsyncPipeline
from pipeline.tts.tts_sync import TTSSyncPipeline
from pipeline.vidcap.vidcap_async import VidCapAsyncPipeline
from pipeline.vidcap.vidcap_sync import VidCapSyncPipeline
from pipeline.vla.showui.showui_async import ShowUIAsyncPipeline
from pipeline.vla.showui.showui_sync import ShowUISyncPipeline


class BaseBot(ZerolanLiveRobotContext):
    """Base bot providing pipeline reload and device management.

    Subclasses (e.g. ZerolanLiveRobot) add event orchestration, TTS, and
    service lifecycle.  `reload_device` currently handles microphone
    pause/resume only; extend it for additional device types as needed.
    """

    def __init__(self):
        super().__init__()

    @staticmethod
    def _reload_single_pipeline(current_pipeline, sync_cls, async_cls, pipeline_config, name: str):
        if current_pipeline is None:
            logger.warning(f"Pipeline {name} will not reload because it has not been established.")
            return None
        pipeline_type = type(current_pipeline)
        if pipeline_type is sync_cls:
            current_pipeline.close()
            return sync_cls(pipeline_config)
        if pipeline_type is async_cls:
            current_pipeline.close()
            return async_cls(pipeline_config)
        logger.error(f"Unsupported pipeline type: {pipeline_type}")
        return current_pipeline

    def reload_pipeline(self):
        config = get_config()

        self.asr = self._reload_single_pipeline(self.asr, ASRSyncPipeline, ASRAsyncPipeline, config.pipeline.asr, "asr")
        self.vec_db = self._reload_single_pipeline(self.vec_db, MilvusSyncPipeline, MilvusAsyncPipeline, config.pipeline.vec_db.milvus, "vec_db")
        self.img_cap = self._reload_single_pipeline(self.img_cap, ImgCapSyncPipeline, ImgCapAsyncPipeline, config.pipeline.img_cap, "img_cap")
        self.llm = self._reload_single_pipeline(self.llm, LLMSyncPipeline, LLMAsyncPipeline, config.pipeline.llm, "llm")
        self.ocr = self._reload_single_pipeline(self.ocr, OCRSyncPipeline, OCRAsyncPipeline, config.pipeline.ocr, "ocr")
        self.tts = self._reload_single_pipeline(self.tts, TTSSyncPipeline, TTSAsyncPipeline, config.pipeline.tts, "tts")
        self.vid_cap = self._reload_single_pipeline(self.vid_cap, VidCapSyncPipeline, VidCapAsyncPipeline, config.pipeline.vid_cap, "vid_cap")
        self.showui = self._reload_single_pipeline(self.showui, ShowUISyncPipeline, ShowUIAsyncPipeline, config.pipeline.showui, "showui")

        logger.info("Reloaded pipelines.")

    def reload_device(self):
        config = get_config()

        # Microphone
        if self.mic is not None:
            if config.system.default_enable_microphone:
                self.mic.resume()
            else:
                self.mic.pause()
        else:
            logger.info("Microphone will not reload because there is no microphone found.")
