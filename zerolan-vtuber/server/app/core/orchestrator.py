"""ConversationPipeline：文本/语音 → ASR→LLM(带工具)→分句→TTS 编排（§7）。

音频写盘为唯一允许的阻塞 IO；其余全 asyncio。
"""

import re
from collections.abc import AsyncIterator, Awaitable, Callable

from loguru import logger

from app.core.agent_loop import AgentLoop
from app.core.history import History
from app.providers.asr import create_asr_provider
from app.providers.config import ASRSlotConfig, TTSSlotConfig
from app.providers.tts import create_tts_provider
from app.tools.registry import ToolRegistry

_SENTENCE_SPLIT = re.compile(r"(?<=[。！？!?；;])")


def split_sentences(text: str) -> list[str]:
    """按句末标点分句，过滤空白。"""
    parts = _SENTENCE_SPLIT.split(text)
    sentences = [p.strip() for p in parts if p.strip()]
    # 过短片段合并到前句（避免一条标点单独成句）
    merged: list[str] = []
    for s in sentences:
        if merged and len(s) <= 1:
            merged[-1] += s
        else:
            merged.append(s)
    return merged


class Orchestrator:
    def __init__(
        self,
        *,
        asr_config: ASRSlotConfig,
        tts_config: TTSSlotConfig,
        agent_loop: AgentLoop,
        registry: ToolRegistry,
        history: History,
        system_prompt: str,
    ) -> None:
        self._asr_config = asr_config
        self._tts_config = tts_config
        self._asr = create_asr_provider(asr_config)
        self._tts = create_tts_provider(tts_config)
        self._agent_loop = agent_loop
        self._registry = registry
        self._history = history
        self._system_prompt = system_prompt
        self._output_callback: Callable[[str, dict[str, object]], Awaitable[None]] | None = None

    def set_output_callback(
        self, callback: Callable[[str, dict[str, object]], Awaitable[None]] | None
    ) -> None:
        """注册输出事件回调（WS 层注入，用于广播字幕/音频）。"""
        self._output_callback = callback

    async def _messages(self, session_id: str, user_text: str) -> list[dict[str, str]]:
        try:
            history = await self._history.recent(session_id)
        except Exception:  # noqa: BLE001 — 历史加载失败不阻断对话
            logger.warning("history recall failed for session {}", session_id)
            history = []
        base = [{"role": c["role"], "content": c["content"]} for c in history]
        return [{"role": "system", "content": self._system_prompt}, *base]

    async def transcribe_audio(
        self, audio: bytes, fmt: str, sample_rate: int, channels: int
    ) -> str:
        """语音入口：ASR 转文字。

        协议槽位通用调用（vendor 差异由 provider 实现吸收）：
        百度/火山均接受 sample_rate；channels 仅火山使用（默认 1）。
        """
        logger.info("asr transcribing {} bytes ({}Hz {}ch)", len(audio), sample_rate, channels)
        return await self._asr.transcribe(audio, fmt, sample_rate=sample_rate, channels=channels)

    async def process_text(self, session_id: str, text: str) -> AsyncIterator[dict[str, object]]:
        """文本入口：LLM(带工具) → 逐句 TTS 产出。

        每个产出事件同时触发 output_callback（WS 广播），再 yield 给调用方。
        """
        await self._history.add(session_id, "user", text)
        user_evt: dict[str, object] = {"type": "user_text", "text": text}
        await self._emit(session_id, user_evt)
        yield user_evt

        messages = await self._messages(session_id, text)
        messages.append({"role": "user", "content": text})

        result = await self._agent_loop.run(messages)
        answer = result.content.strip()
        if not answer:
            logger.warning("agent loop returned empty answer")
            return
        await self._history.add(session_id, "assistant", answer)

        for sentence in split_sentences(answer):
            audio: list[bytes] = []
            async for chunk in self._tts.synthesize(sentence, voice=""):
                audio.append(chunk)
            wave = b"".join(audio)
            if not wave:
                logger.warning("TTS produced empty audio for: {}", sentence)
                continue
            evt: dict[str, object] = {"type": "speech", "text": sentence, "bytes": wave}
            await self._emit(session_id, evt)
            yield evt

    async def _emit(self, session_id: str, evt: dict[str, object]) -> None:
        if self._output_callback is not None:
            await self._output_callback(session_id, evt)

    async def hot_swap(
        self, asr_config: ASRSlotConfig | None = None, tts_config: TTSSlotConfig | None = None
    ) -> None:
        """§7 热替换：重建 ASR/TTS 实例，无重启。"""
        if asr_config is not None:
            self._asr_config = asr_config
            self._asr = create_asr_provider(asr_config)
            logger.info("ASR provider hot-swapped: {}", asr_config.vendor)
        if tts_config is not None:
            self._tts_config = tts_config
            self._tts = create_tts_provider(tts_config)
            logger.info("TTS provider hot-swapped: {}", tts_config.vendor)
