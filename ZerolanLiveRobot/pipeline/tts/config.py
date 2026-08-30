from pydantic import Field, BaseModel

from common.enumerator import BaseEnum
from common.utils.enum_util import enum_to_markdown
from pipeline.base.base_sync import AbstractPipelineConfig


#######
# TTS #
#######

class TTSModelIdEnum(BaseEnum):
    GPT_SoVITS = "AkagawaTsurunaki/GPT-SoVITS"  # Forked repo
    BaiduTTS = "BaiduTTS"
    MimoTTS = "MimoTTS"


# Config for BaiduTTS and should
class BaiduTTSConfig(BaseModel):
    api_key: str = Field(default="", description="The API key for Baidu TTS service.")
    secret_key: str = Field(default="", description="The secret key for Baidu TTS service.")


class MimoTTSConfig(BaseModel):
    api_key: str = Field(default="", description="The API key (api-key header) for Mimo TTS service.\n"
                                                  "Set via environment variable $MIMO_API_KEY or directly here.")
    api_url: str = Field(default="https://token-plan-cn.xiaomimimo.com/v1/chat/completions",
                         description="The API URL for Mimo TTS service.")
    model: str = Field(default="mimo-v2.5-tts", description="Model name. Default: mimo-v2.5-tts")
    voice: str = Field(default="Chloe", description="Voice name to use. Examples: Chloe, etc.")
    audio_format: str = Field(default="wav", description="Output audio format. Options: wav, mp3")
    tone_prompt: str = Field(default="", description="Tone/style prompt for the user message.\n"
                                                    "Controls emotion, pace, pitch of generated speech.\n"
                                                    "Example: 'Bright, bouncy, slightly sing-song tone — like you are bursting with good news.'")


# Config for ZerolanCore
class TTSPipelineConfig(AbstractPipelineConfig):
    model_id: TTSModelIdEnum = Field(default=TTSModelIdEnum.GPT_SoVITS,
                                     description=f"The ID of the model used for text-to-speech. \n"
                                                 f"{enum_to_markdown(TTSModelIdEnum)}")
    predict_url: str = Field(default="http://127.0.0.1:11000/tts/predict",
                             description="The URL for TTS prediction requests.")
    stream_predict_url: str = Field(default="http://127.0.0.1:11000/tts/stream-predict",
                                    description="The URL for streaming TTS prediction requests.")
    baidu_tts_config: BaiduTTSConfig = Field(default=BaiduTTSConfig(),
                                             description=f"Baidu TTS config. \n"
                                                         f"Only edit it when you set `model_id` to `{TTSModelIdEnum.BaiduTTS.value}`.\n"
                                                         f"For more details please see the [documents](https://cloud.baidu.com/doc/SPEECH/s/mlbxh7xie).")
    mimo_tts_config: MimoTTSConfig = Field(default=MimoTTSConfig(),
                                           description=f"Mimo (XiaoMiMiMo) TTS config. "
                                                       f"Only edit it when you set `model_id` to `{TTSModelIdEnum.MimoTTS.value}`.\n"
                                                       f"Supports emotion/tone control via tone_prompt. "
                                                       f"For more details please see the Mimo API documentation.")
