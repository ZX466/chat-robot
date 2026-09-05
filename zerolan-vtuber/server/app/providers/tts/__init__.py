"""TTS Provider 工厂：vendor → 具体实现。

§7 update_provider_config 热替换时按新配置重建实例。
"""

import httpx

from ..config import BaiduTTSConfig, MimoTTSConfig, OpenAITTSConfig, TTSSlotConfig
from .baidu import BaiduTTSError, BaiduTTSProvider
from .mimo import MimoTTSError, MimoTTSProvider
from .openai import OpenAITTSError, OpenAITTSProvider

__all__ = [
    "BaiduTTSError",
    "BaiduTTSProvider",
    "MimoTTSError",
    "MimoTTSProvider",
    "OpenAITTSError",
    "OpenAITTSProvider",
    "create_tts_provider",
]


def create_tts_provider(
    config: TTSSlotConfig, *, client: httpx.AsyncClient | None = None
) -> BaiduTTSProvider | MimoTTSProvider | OpenAITTSProvider:
    if isinstance(config, BaiduTTSConfig):
        return BaiduTTSProvider(config, client=client)
    if isinstance(config, MimoTTSConfig):
        return MimoTTSProvider(config, client=client)
    if isinstance(config, OpenAITTSConfig):
        return OpenAITTSProvider(config, client=client)
    raise ValueError(f"Unsupported TTS vendor: {type(config).__name__}")
