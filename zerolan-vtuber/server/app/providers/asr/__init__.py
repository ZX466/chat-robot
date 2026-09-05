"""ASR Provider 工厂：vendor → 具体实现。

§7 update_provider_config 热替换时按新配置重建实例。
"""

import httpx

from ..config import ASRSlotConfig, BaiduASRConfig, OpenAIASRConfig, VolcanoASRConfig
from .baidu import BaiduASRError, BaiduASRProvider
from .openai import OpenAIASRError, OpenAIASRProvider
from .volcano import VolcanoASRError, VolcanoASRProvider

__all__ = [
    "BaiduASRError",
    "BaiduASRProvider",
    "OpenAIASRError",
    "OpenAIASRProvider",
    "VolcanoASRError",
    "VolcanoASRProvider",
    "create_asr_provider",
]


def create_asr_provider(
    config: ASRSlotConfig, *, client: httpx.AsyncClient | None = None
) -> BaiduASRProvider | VolcanoASRProvider | OpenAIASRProvider:
    if isinstance(config, BaiduASRConfig):
        return BaiduASRProvider(config, client=client)
    if isinstance(config, VolcanoASRConfig):
        return VolcanoASRProvider(config, client=client)
    if isinstance(config, OpenAIASRConfig):
        return OpenAIASRProvider(config, client=client)
    raise ValueError(f"Unsupported ASR vendor: {type(config).__name__}")
