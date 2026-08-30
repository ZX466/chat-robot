"""Provider 协议定义（任务书 §4.2 原文，接口归属 Claude 骨架，此处保持一致以便合并）。"""

from collections.abc import AsyncIterator
from typing import Protocol


class ASRProvider(Protocol):
    async def transcribe(
        self,
        audio: bytes,
        fmt: str,
        *,
        sample_rate: int = 16000,
        channels: int = 1,
    ) -> str: ...


class TTSProvider(Protocol):
    async def synthesize(self, text: str, voice: str) -> AsyncIterator[bytes]:
        """音频块流式产出。"""
        ...
