from pydantic import Field, BaseModel

from common.enumerator import BaseEnum
from common.utils.enum_util import enum_to_markdown
from pipeline.base.base_sync import AbstractPipelineConfig


#######
# ASR #
#######

class AudioFormatEnum(BaseEnum):
    Float32: str = "float32"


class ASRModelIdEnum(BaseEnum):
    Paraformer = "iic/speech_paraformer_asr_nat-zh-cn-16k-common-vocab8358-tensorflow1"
    KotobaWhisper = 'kotoba-tech/kotoba-whisper-v2.0'
    BaiduASR = "BaiduASR"
    WhisperASR = "WhisperASR"
    BigASR = "BigASR"


class BaiduASRConfig(BaseModel):
    api_key: str = Field(default="", description="The API key for Baidu ASR service.")
    secret_key: str = Field(default="", description="The secret key for Baidu ASR service.")


class WhisperASRConfig(BaseModel):
    api_key: str = Field(default="", description="The API key for OpenAI/Whisper ASR service.")
    api_url: str = Field(default="https://api.openai.com/v1/audio/transcriptions",
                         description="The API URL for Whisper ASR service. Default: https://api.openai.com/v1/audio/transcriptions")
    model: str = Field(default="whisper-1", description="The model ID to use. Currently only whisper-1 is available.")
    language: str | None = Field(default=None, description="The language of the input audio. ISO-639-1 format. Optional but improves accuracy.")
    prompt: str | None = Field(default=None, description="Optional text to guide the model's style or continue a previous audio segment.")
    temperature: float = Field(default=0.0, description="Sampling temperature between 0 and 1. Higher values make output more random.")
    response_format: str = Field(default="json", description="The format of the transcript output. Options: json, text, srt, verbose_json, vtt")


class BigASRConfig(BaseModel):
    api_key: str = Field(default="", description="The API key (x-api-key) for ByteDance BigASR service.\n"
                                                  "Reference: https://www.volcengine.com/docs/6561/80818")
    resource_id: str = Field(default="volc.bigasr.auc", description="The X-Api-Resource-Id header value. Default: volc.bigasr.auc")
    submit_url: str = Field(default="https://openspeech.bytedance.com/api/v3/auc/bigmodel/submit",
                            description="URL for submitting audio recognition task.")
    query_url: str = Field(default="https://openspeech.bytedance.com/api/v3/auc/bigmodel/query",
                           description="URL for querying recognition result.")
    poll_interval: float = Field(default=0.5, description="Polling interval in seconds between submit and query requests.")
    max_poll_times: int = Field(default=120, description="Maximum number of polling attempts before timeout.")


class ASRPipelineConfig(AbstractPipelineConfig):
    sample_rate: int = Field(16000, description="The sample rate for audio input.")
    channels: int = Field(1, description="The number of audio channels.")
    format: AudioFormatEnum = Field(AudioFormatEnum.Float32,
                                    description=f"The format of the audio data. {enum_to_markdown(AudioFormatEnum)}")
    model_id: ASRModelIdEnum = Field(default=ASRModelIdEnum.Paraformer,
                                     description=f"The ID of the model used for ASR. \n{enum_to_markdown(ASRModelIdEnum)}")
    predict_url: str = Field(default="http://127.0.0.1:11000/asr/predict",
                             description="The URL for ASR prediction requests.")
    stream_predict_url: str = Field(default="http://127.0.0.1:11000/asr/stream-predict",
                                    description="The URL for streaming ASR prediction requests.")
    baidu_asr_config: BaiduASRConfig = Field(default=BaiduASRConfig(), description="Baidu ASR config."
                                                                                   f"Only edit it when you set `model_id` to `{ASRModelIdEnum.BaiduASR.value}`.\n"
                                                                                   f"For more details please see the [documents](https://cloud.baidu.com/doc/SPEECH/s/qlcirqhz0).")
    whisper_asr_config: WhisperASRConfig = Field(default=WhisperASRConfig(), description="Whisper ASR config. "
                                                                                        f"Only edit it when you set `model_id` to `{ASRModelIdEnum.WhisperASR.value}`.\n"
                                                                                        f"For more details please see the [documents](https://zhizengzeng.com/docs/audio).")
    bigasr_config: BigASRConfig = Field(default=BigASRConfig(), description="ByteDance BigASR (Volcengine) config. "
                                                                              f"Only edit it when you set `model_id` to `{ASRModelIdEnum.BigASR.value}`.\n"
                                                                              f"For more details please see the [documents](https://www.volcengine.com/docs/6561/80818).")
