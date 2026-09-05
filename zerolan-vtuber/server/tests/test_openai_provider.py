"""OpenAI 兼容 ASR/TTS provider 契约测试（respx mock httpx，风格与既有 provider 测试一致）。

覆盖：transcribe 三种 response_format / synthesize 单块字节流 / 错误包解析 /
fmt 白名单 / api_path 注入拒绝 / ws 层 vendor=openai 热替换（见 test_ws_hotswap.py）。
"""

import json

import httpx  # noqa: F401 — 类型标注保留
import pytest
import respx
from pydantic import ValidationError

from app.providers.asr.openai import OpenAIASRError, OpenAIASRProvider
from app.providers.config import OpenAIASRConfig, OpenAITTSConfig
from app.providers.tts.openai import OpenAIITSError, OpenAITTSProvider

AUDIO = b"fake-audio-bytes"
BASE = "https://api.openai.com"
TRANSCRIBE_URL = f"{BASE}/v1/audio/transcriptions"
SPEECH_URL = f"{BASE}/v1/audio/speech"


def _asr(**overrides: str) -> OpenAIASRProvider:
    config = OpenAIASRConfig(api_key="sk-test", **overrides)
    return OpenAIASRProvider(config)


def _tts(**overrides: str) -> OpenAITTSProvider:
    config = OpenAITTSConfig(api_key="sk-test", **overrides)
    return OpenAITTSProvider(config)


# --- ASR ---


@respx.mock
async def test_transcribe_text_format() -> None:
    route = respx.post(TRANSCRIBE_URL).respond(
        content=b"  Hello world  ", headers={"Content-Type": "text/plain; charset=utf-8"}
    )
    provider = _asr(response_format="text")

    transcript = await provider.transcribe(AUDIO, "wav")

    assert transcript == "Hello world"
    request = route.calls[0].request
    assert request.headers["Authorization"] == "Bearer sk-test"
    body = request.content
    assert b'name="model"' in body and b"whisper-1" in body
    assert b"name=\"response_format\"" in body and b"text" in body
    assert AUDIO in body


@respx.mock
async def test_transcribe_json_format() -> None:
    respx.post(TRANSCRIBE_URL).respond(json={"text": "你好世界"})
    provider = _asr()  # 默认 response_format=json

    assert await provider.transcribe(AUDIO, "mp3") == "你好世界"


@respx.mock
async def test_transcribe_verbose_json_format() -> None:
    respx.post(TRANSCRIBE_URL).respond(json={"text": "分段文本", "segments": [{"id": 0}]})
    provider = _asr(response_format="verbose_json")

    assert await provider.transcribe(AUDIO, "flac") == "分段文本"


@respx.mock
async def test_transcribe_http_error_raises() -> None:
    respx.post(TRANSCRIBE_URL).respond(
        401,
        json={
            "error": {
                "message": "Incorrect API key provided",
                "type": "invalid_request_error",
                "code": "invalid_api_key",
            }
        },
    )
    provider = _asr()

    with pytest.raises(OpenAIASRError, match="Incorrect API key provided"):
        await provider.transcribe(AUDIO, "wav")


@respx.mock
async def test_transcribe_empty_text_raises() -> None:
    respx.post(TRANSCRIBE_URL).respond(json={"text": ""})
    provider = _asr()

    with pytest.raises(OpenAIASRError, match="empty transcript"):
        await provider.transcribe(AUDIO, "wav")


@respx.mock
async def test_transcribe_fmt_whitelist_rejects() -> None:
    route = respx.post(TRANSCRIBE_URL).respond(json={"text": "x"})
    provider = _asr()

    with pytest.raises(OpenAIASRError, match="unsupported audio format"):
        await provider.transcribe(AUDIO, "wma")

    assert route.call_count == 0  # 白名单拒绝发生在请求发出前


async def test_transcribe_missing_api_key_raises() -> None:
    provider = OpenAIASRProvider(OpenAIASRConfig(api_key=""))
    with pytest.raises(ValueError, match="api_key"):
        await provider.transcribe(AUDIO, "wav")


# --- TTS ---


@respx.mock
async def test_synthesize_single_chunk() -> None:
    route = respx.post(SPEECH_URL).respond(
        content=b"fake-mp3-bytes", headers={"Content-Type": "audio/mpeg"}
    )
    provider = _tts(model="tts-1", voice="alloy")

    chunks = [chunk async for chunk in provider.synthesize("你好", "")]

    assert chunks == [b"fake-mp3-bytes"]
    request_body = json.loads(route.calls[0].request.content)
    assert request_body == {
        "model": "tts-1",
        "input": "你好",
        "voice": "alloy",  # voice 为空 → 配置默认音色
        "response_format": "mp3",
    }
    assert route.calls[0].request.headers["Authorization"] == "Bearer sk-test"


@respx.mock
async def test_synthesize_voice_override() -> None:
    route = respx.post(SPEECH_URL).respond(content=b"x", headers={"Content-Type": "audio/mpeg"})
    provider = _tts(voice="alloy")

    _ = [chunk async for chunk in provider.synthesize("你好", "nova")]

    assert json.loads(route.calls[0].request.content)["voice"] == "nova"


@respx.mock
async def test_synthesize_http_error_raises() -> None:
    respx.post(SPEECH_URL).respond(
        429,
        json={"error": {"message": "rate limited", "type": "rate_limit_error", "code": "429"}},
    )
    provider = _tts()

    with pytest.raises(OpenAIITSError, match="rate limited"):
        async for _ in provider.synthesize("你好", "alloy"):
            pass


@respx.mock
async def test_synthesize_non_audio_body_raises() -> None:
    # 200 但 Content-Type 非 audio → 按错误包处理
    respx.post(SPEECH_URL).respond(
        json={"error": {"message": "model rejected the request", "type": "invalid_request_error"}}
    )
    provider = _tts()

    with pytest.raises(OpenAIITSError, match="model rejected the request"):
        async for _ in provider.synthesize("你好", "alloy"):
            pass


@respx.mock
async def test_synthesize_error_does_not_echo_input() -> None:
    # codex 安全反馈：错误消息不得回显完整请求 input
    secret_text = "这是一段不应出现在错误消息里的长文本"
    respx.post(SPEECH_URL).respond(
        500, json={"error": {"message": "server exploded", "type": "server_error"}}
    )
    provider = _tts()

    with pytest.raises(OpenAIITSError) as excinfo:
        async for _ in provider.synthesize(secret_text, "alloy"):
            pass

    assert secret_text not in str(excinfo.value)


async def test_synthesize_missing_api_key_raises() -> None:
    provider = OpenAITTSProvider(OpenAITTSConfig(api_key=""))
    with pytest.raises(ValueError, match="api_key"):
        async for _ in provider.synthesize("你好", "alloy"):
            pass


# --- api_path 白名单（安全：codex 反馈） ---


@pytest.mark.parametrize(
    "bad_path", ["/../v1/audio/speech", "/audio/speech", "v1/audio/speech"]
)
def test_asr_config_rejects_bad_api_path(bad_path: str) -> None:
    with pytest.raises(ValidationError, match="api_path"):
        OpenAIASRConfig(api_key="k", api_path=bad_path)


@pytest.mark.parametrize("bad_path", ["/x/../v1/audio/speech", "/audio", ""])
def test_tts_config_rejects_bad_api_path(bad_path: str) -> None:
    with pytest.raises(ValidationError, match="api_path"):
        OpenAITTSConfig(api_key="k", api_path=bad_path)


def test_config_accepts_custom_gateway_path() -> None:
    # 自建网关可自定义 /v1/ 命名空间内的路径（如 siliconflow 代理）
    config = OpenAIASRConfig(api_key="k", api_path="/v1/my-gateway/transcriptions")
    assert config.api_path == "/v1/my-gateway/transcriptions"


def test_shared_client_used_by_default() -> None:
    # 未注入 client 时复用全局单例连接池（§3）
    from app.providers.http import get_shared_client

    assert _asr()._client is get_shared_client()  # noqa: SLF001
    assert _tts()._client is get_shared_client()  # noqa: SLF001
