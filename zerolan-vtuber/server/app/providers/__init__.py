"""ASR/TTS Provider 层（REFACTOR_PROMPT.md §4.2 迁移草案，cline）。

每家厂商一个类，禁止万能通用类；共享 httpx.AsyncClient 单例连接池（§3）。
"""

from .config import (
    ASRSlotConfig,
    BaiduASRConfig,
    BaiduTTSConfig,
    MimoTTSConfig,
    TTSSlotConfig,
    VolcanoASRConfig,
)
from .protocols import ASRProvider, TTSProvider

__all__ = [
    "ASRProvider",
    "ASRSlotConfig",
    "BaiduASRConfig",
    "BaiduTTSConfig",
    "MimoTTSConfig",
    "TTSProvider",
    "TTSSlotConfig",
    "VolcanoASRConfig",
]
