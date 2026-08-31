"""全链路 E2E：mock ASR/LLM/TTS，文本进 → 分句 → play_speech 协议消息出（§10 红线）。

- 测试 WS 端点 + HTTP 语音上传路径。
- 不联网：HUB 内部 provider 全部 mock。
"""

import json
import os
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

os.environ.setdefault("LITELLM_LOCAL_MODEL_COST_MAP", "True")
os.environ.setdefault("LITELLM_LOG", "ERROR")

# import main 会立即 build_orchestrator（用 settings 单例），需先注入占位 key
from app.config import settings as _settings  # noqa: E402

_settings.asr.api_key = "fake"
_settings.tts.api_key = "fake"

import pytest  # noqa: E402

from app.api.ws import (  # noqa: E402
    WSHub,
    _build_asr_config,
    _build_tts_config,
    _validate_provider_config,
)
from app.config import ASRConfig, LLMConfig, ServerConfig, Settings, TTSConfig  # noqa: E402
from app.core.agent_loop import AgentLoop  # noqa: E402
from app.core.history import History  # noqa: E402
from app.core.orchestrator import Orchestrator  # noqa: E402
from app.main import app  # noqa: E402 — 依赖上方注入
from app.providers.config import BaiduASRConfig, BaiduTTSConfig  # noqa: E402

FakeWS = None  # 占位防止编辑器误报；真实 FakeWS 定义在测试函数内


class FakeASR:
    async def transcribe(
        self, audio: bytes, fmt: str, *, sample_rate: int = 16000, channels: int = 1
    ) -> str:
        return "语音识别测试文本"


class FakeTTS:
    async def synthesize(self, text: str, voice: str) -> AsyncIterator[bytes]:
        yield b"\x00\x01" * 100  # 假音频块


class FakeLLM:
    def __init__(self, reply: str = "你好，我是虚拟主播！") -> None:
        self._reply = reply

    async def acompletion(
        self, messages: list[dict[str, str]], tools: list[dict[str, Any]] | None = None
    ) -> Any:
        from app.providers.llm import LLMResponse

        return LLMResponse(content=self._reply)


async def make_orchestrator(tmp_path: Path) -> Orchestrator:
    history = History(tmp_path / "test.db")
    await history.init()
    registry = type("R", (), {"litellm_tools": lambda self: []})()
    loop = AgentLoop(FakeLLM(), registry)  # type: ignore[arg-type]
    orch = Orchestrator(
        asr_config=BaiduASRConfig(api_key="fake", secret_key="fake"),
        tts_config=BaiduTTSConfig(api_key="fake", secret_key="fake"),
        agent_loop=loop,
        registry=registry,  # type: ignore[arg-type]
        history=history,
        system_prompt="test",
    )
    orch._asr = FakeASR()  # noqa: SLF001
    orch._tts = FakeTTS()  # noqa: SLF001
    return orch


def make_settings(tmp_path: Path) -> Settings:
    return Settings(
        llm=LLMConfig(model="openai/gpt-4o-mini"),
        asr=ASRConfig(vendor="baidu"),
        tts=TTSConfig(vendor="baidu"),
        server=ServerConfig(audio_dir=tmp_path / "audio"),
    )


@pytest.mark.asyncio
async def test_ws_text_flow_emits_play_speech(tmp_path: Path) -> None:
    """文本进 → 字幕/历史 + play_speech（url）协议消息出。"""
    orch = await make_orchestrator(tmp_path)
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
    hub._connections["s1"] = fake_ws  # noqa: SLF001 — 注册测试连接以接收广播
    await hub._on_user_text(fake_ws, "s1", "你好")  # noqa: SLF001
    actions = [m["action"] for m in sent]
    assert "play_speech" in actions
    assert "show_user_text_input" in actions
    assert "add_history" in actions
    speech = next(m for m in sent if m["action"] == "play_speech")
    assert "audio/" in speech["data"]["url"]
    assert speech["data"]["url"].endswith(".wav") is False  # {id} 无扩展名


@pytest.mark.parametrize(
    "payload,expected",
    [
        (
            {
                "llm": {"base_url": "http://x", "api_key": "k", "model": "m"},
                "asr": {"vendor": "baidu", "base_url": "http://x", "api_key": "k", "model": "m"},
                "tts": {"vendor": "mimo", "base_url": "http://x", "api_key": "k", "model": "m"},
            },
            [],
        ),
        (
            {"asr": {"vendor": "nope", "base_url": "http://x", "api_key": "k", "model": "m"}},
            ["asr.vendor"],
        ),
        (
            {"asr": {"vendor": "baidu", "base_url": "ftp://bad", "api_key": "k", "model": "m"}},
            ["asr.base_url"],
        ),
        ({"asr": {"vendor": "baidu"}}, ["asr.base_url", "asr.api_key", "asr.model"]),
    ],
)
def test_validate_provider_config(payload: dict[str, Any], expected: list[str]) -> None:
    errors = _validate_provider_config(payload)
    if not expected:
        assert errors == []
    else:
        for fragment in expected:
            assert any(fragment in e for e in errors), errors


def test_mask_key() -> None:
    from app.api.ws import mask_key

    key = "sk-abcdef1234567890"
    masked = mask_key(key)
    assert masked.startswith("sk-abc")
    assert masked.endswith("890")
    assert "*******" in masked
    assert key not in masked
    assert "k" not in masked.replace("sk-abc", "").replace("890", "")
    assert mask_key("abc") == "a***"
    assert mask_key("") == "未配置"
    assert mask_key(None) == "未配置"


def test_build_configs() -> None:
    asr = _build_asr_config(
        {"vendor": "volcano", "base_url": "http://v", "api_key": "kk", "model": "m"}
    )
    assert asr.vendor == "volcano"
    tts = _build_tts_config(
        {"vendor": "mimo", "base_url": "http://t", "api_key": "kk", "model": "m"}
    )
    assert tts.vendor == "mimo"


@pytest.mark.asyncio
async def test_http_microphone_flow(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """multipart POST /playground/microphone → ASR → 文本 → 编排 → 200。"""
    orch = await make_orchestrator(tmp_path)
    # 替换 app 全局路由引用，避免连真 provider（todo：注入式重构后去除）
    app.state.orchestrator = orch
    app.state.history = orch._history  # noqa: SLF001
    WSHub(orch, make_settings(tmp_path))  # 注册输出回调

    from httpx import ASGITransport, AsyncClient

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/playground/microphone",
            files={"audio": ("voice.wav", b"\x00\x01" * 100, "audio/wav")},
            data={"metadata": json.dumps({"Channels": 1, "SampleRate": 16000})},
        )
        health = await client.get("/health")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["code"] == 200
    assert body["data"]["transcript"] == "语音识别测试文本"
    assert health.status_code == 200
