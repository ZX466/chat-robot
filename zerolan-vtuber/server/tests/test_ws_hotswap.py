"""热替换契约测试（§10 红线）：update_provider_config → 热替换 → 下次对话用新供应商。

覆盖：
- llm 槽位校验（base_url/api_key/model 必填、URL 合法性）
- llm 热替换：rebuild 参数到达 LLM 槽位，且下一轮对话继续由新配置服务
- asr/tts 槽位重建（vendor 换代、实例重建）
"""

import json
import os
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

os.environ.setdefault("LITELLM_LOCAL_MODEL_COST_MAP", "True")
os.environ.setdefault("LITELLM_LOG", "ERROR")

import pytest

from app.api.ws import (
    WSHub,
    _build_asr_config,
    _build_llm_config,
    _build_tts_config,
    _validate_provider_config,
)
from app.config import ASRConfig, LLMConfig, ServerConfig, Settings, TTSConfig
from app.core.agent_loop import AgentLoop
from app.core.history import History
from app.core.orchestrator import Orchestrator
from app.providers.config import BaiduASRConfig, BaiduTTSConfig
from app.providers.llm import LLMResponse


class FakeASR:
    async def transcribe(
        self, audio: bytes, fmt: str, *, sample_rate: int = 16000, channels: int = 1
    ) -> str:
        return "语音识别测试文本"


class FakeTTS:
    async def synthesize(self, text: str, voice: str) -> AsyncIterator[bytes]:
        yield b"\x00\x01" * 100  # 假音频块


class RebuildableFakeLLM:
    """记录 rebuild 调用：验证热替换参数真正到达 LLM 槽位。"""

    def __init__(self, reply: str = "你好，我是虚拟主播！") -> None:
        self._reply = reply
        self.rebuild_calls: list[dict[str, str]] = []

    def rebuild(
        self, *, base_url: str | None = None, api_key: str | None = None, model: str | None = None
    ) -> None:
        self.rebuild_calls.append(
            {"base_url": base_url or "", "api_key": api_key or "", "model": model or ""}
        )

    async def acompletion(
        self, messages: list[dict[str, str]], tools: list[dict[str, Any]] | None = None
    ) -> Any:
        return LLMResponse(content=self._reply)


async def make_orchestrator(tmp_path: Path) -> tuple[Orchestrator, RebuildableFakeLLM]:
    history = History(tmp_path / "test.db")
    await history.init()
    registry = type("R", (), {"litellm_tools": lambda self: []})()
    llm = RebuildableFakeLLM()
    loop = AgentLoop(llm, registry)  # type: ignore[arg-type]
    orch = Orchestrator(
        asr_config=BaiduASRConfig(api_key="fake", secret_key="fake"),
        tts_config=BaiduTTSConfig(api_key="fake", secret_key="fake"),
        agent_loop=loop,
        registry=registry,  # type: ignore[arg-type]
        history=history,
        system_prompt="test",
    )
    orch._asr = FakeASR()  # noqa: SLF001 — 白名单内替换为假实现
    orch._tts = FakeTTS()  # noqa: SLF001
    return orch, llm


def make_settings(tmp_path: Path) -> Settings:
    return Settings(
        llm=LLMConfig(model="openai/gpt-4o-mini"),
        asr=ASRConfig(vendor="baidu"),
        tts=TTSConfig(vendor="baidu"),
        server=ServerConfig(audio_dir=tmp_path / "audio"),
    )


def test_validate_provider_config_accepts_llm() -> None:
    payload = {
        "llm": {"base_url": "https://api.example.com/v1", "api_key": "k", "model": "m"},
        "asr": {"vendor": "baidu", "base_url": "http://x", "api_key": "k", "model": "m"},
        "tts": {"vendor": "mimo", "base_url": "http://x", "api_key": "k", "model": "m"},
    }
    assert _validate_provider_config(payload) == []


def test_validate_provider_config_rejects_bad_llm() -> None:
    errors = _validate_provider_config(
        {"llm": {"base_url": "ftp://bad", "api_key": "k", "model": "m"}}
    )
    assert any("llm.base_url" in e for e in errors)
    errors2 = _validate_provider_config({"llm": {"base_url": "http://ok"}})
    assert any("llm.api_key" in e for e in errors2)
    assert any("llm.model" in e for e in errors2)


def test_build_llm_config_none_is_safe() -> None:
    # 槽位未提供 → 不重建（None），不会用默认配置误覆盖现网模型
    assert _build_llm_config(None) is None
    assert _build_llm_config({}) is None
    cfg = _build_llm_config({"base_url": "https://x", "api_key": "k", "model": "m"})
    assert cfg is not None and cfg.model == "m"
    # P3(codex)：空串不得变成 "None" 字面量（校验层拦截兜底 + 构造防御）
    cfg2 = _build_llm_config({"base_url": "", "api_key": " ", "model": "m"})
    assert cfg2 is not None and cfg2.base_url is None and cfg2.api_key is None


@pytest.mark.asyncio
async def test_hot_swap_llm_applies_to_next_conversation(tmp_path: Path) -> None:
    """发送 update_provider_config(llm) → ack 200 → rebuild 到达 LLM 槽位 → 下一轮对话正常。"""
    orch, llm = await make_orchestrator(tmp_path)
    hub = WSHub(orch, make_settings(tmp_path))
    sent: list[dict[str, Any]] = []

    class FakeWS:
        async def accept(self) -> None:
            pass

        async def receive_text(self) -> str:
            raise AssertionError("no more messages")

        async def send_text(self, data: str) -> None:
            sent.append(json.loads(data))

    fake_ws = FakeWS()
    hub._connections["s1"] = fake_ws  # noqa: SLF001
    try:
        from app.protocol.models import ZerolanProtocol

        await hub._dispatch(  # noqa: SLF001
            fake_ws,
            "s1",
            ZerolanProtocol(
                action="update_provider_config",
                message="update provider config",
                code=0,
                data={
                    "llm": {
                        "base_url": "https://new.test/v1",
                        "api_key": "new-key",
                        "model": "openai/gpt-5",
                    },
                },
            ).model_dump_json(),
        )
        ack = sent[-1]
        assert ack["action"] == "update_provider_config"
        assert ack["code"] == 200, ack
        assert ack["data"]["message"]  # ack 带原因文案供客户端 Toast 反馈
        # 热替换参数到达 LLM 槽位
        assert llm.rebuild_calls == [
            {"base_url": "https://new.test/v1", "api_key": "new-key", "model": "openai/gpt-5"}
        ]
        # 下一轮对话由热替换后的实例正常服务（play_speech 照常产出）
        await hub._on_user_text(fake_ws, "s1", "你好")  # noqa: SLF001
        actions = [m["action"] for m in sent]
        assert "play_speech" in actions
    finally:
        await orch.close()


@pytest.mark.asyncio
async def test_hot_swap_rebuilds_asr_tts_slots(tmp_path: Path) -> None:
    """asr/tts 槽位重建：vendor 换代生效，旧实例被替换。"""
    orch, _llm = await make_orchestrator(tmp_path)
    old_asr = orch._asr  # noqa: SLF001
    old_tts = orch._tts  # noqa: SLF001
    try:
        await orch.hot_swap(
            llm_config=_build_llm_config(None),
            asr_config=_build_asr_config(
                {"vendor": "volcano", "base_url": "http://v", "api_key": "kk", "model": "m"}
            ),
            tts_config=_build_tts_config(
                {"vendor": "mimo", "base_url": "http://t", "api_key": "kk", "model": "m"}
            ),
        )
        assert orch._asr_config.vendor == "volcano"  # noqa: SLF001
        assert orch._tts_config.vendor == "mimo"  # noqa: SLF001
        assert orch._asr is not old_asr  # noqa: SLF001 — 实例已重建
        assert orch._tts is not old_tts  # noqa: SLF001
    finally:
        await orch.close()
