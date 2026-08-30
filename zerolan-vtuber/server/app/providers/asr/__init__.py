"""ASR Provider 工厂：vendor → 具体实现。

§7 update_provider_config 热替换时按新配置重建实例。
"""

from typing import TYPE_CHECKING

from ..config import ASRSlotConfig, BaiduASRConfig, VolcanoASRConfig
from .baidu import BaiduASRError, BaiduASRProvider
from .volcano import VolcanoASRError, VolcanoASRProvider

if TYPE_CHECKING:
    import httpx

__all__ = [
    "BaiduASRError",
    "BaiduASRProvider",
    "VolcanoASRError",
    "VolcanoASRProvider",
    "create_asr_provider",
]


def create_asr_provider(config: ASRSlotConfig, *, client: "httpx.AsyncClient | None" = None):
    if isinstance(config, BaiduASRConfig):
        return BaiduASRProvider(config, client=client)
    if isinstance(config, VolcanoASRConfig):
        return VolcanoASRProvider(config, client=client)
    raise ValueError(f"Unsupported ASR vendor: {type(config).__name__}")
