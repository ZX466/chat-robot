"""ASR/TTS 槽位与厂商配置（§4.2：{vendor, base_url, api_key, model}，vendor 必填）。

vendor 决定协议实现；三元组（四元组）是该 vendor 实现的参数。
默认值与旧工程 ZerolanLiveRobot/pipeline/{asr,tts}/config.py 保持一致。
"""

from typing import Literal

from pydantic import BaseModel


class BaiduASRConfig(BaseModel):
    """百度短语音识别（标准版）。"""

    vendor: Literal["baidu"] = "baidu"
    base_url: str = "https://vop.baidu.com"
    api_key: str = ""
    secret_key: str = ""
    model: str | None = None
    sample_rate: int = 16000
    token_refresh_margin: int = 60


class VolcanoASRConfig(BaseModel):
    """火山引擎 BigASR（大模型录音文件识别）。"""

    vendor: Literal["volcano"] = "volcano"
    base_url: str = "https://openspeech.bytedance.com"
    submit_path: str = "/api/v3/auc/bigmodel/submit"
    query_path: str = "/api/v3/auc/bigmodel/query"
    api_key: str = ""
    resource_id: str = "volc.bigasr.auc"
    model: str = "bigmodel"
    poll_interval: float = 0.5
    max_poll_times: int = 120
    uid: str = "zerolan-vtuber"


class BaiduTTSConfig(BaseModel):
    """百度语音合成（短文本）。"""

    vendor: Literal["baidu"] = "baidu"
    base_url: str = "https://tsn.baidu.com"
    api_key: str = ""
    secret_key: str = ""
    model: str | None = None
    voice: str = "1"  # 音库 per，默认度小美
    audio_format: Literal["mp3", "pcm", "wav"] = "mp3"
    spd: int = 5
    pit: int = 5
    vol: int = 5
    token_refresh_margin: int = 60


class MimoTTSConfig(BaseModel):
    """小米 MiMo TTS（chat/completions 形态）。"""

    vendor: Literal["mimo"] = "mimo"
    base_url: str = "https://token-plan-cn.xiaomimimo.com"
    api_path: str = "/v1/chat/completions"
    api_key: str = ""
    model: str = "mimo-v2.5-tts"
    voice: str = "Chloe"
    audio_format: Literal["wav", "mp3"] = "wav"
    tone_prompt: str = ""


ASRSlotConfig = BaiduASRConfig | VolcanoASRConfig
TTSSlotConfig = BaiduTTSConfig | MimoTTSConfig
