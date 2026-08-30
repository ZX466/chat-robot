import json

import pytest
import respx

from app.providers.config import MimoTTSConfig
from app.providers.tts.mimo import MimoTTSError, MimoTTSProvider

API_URL = "https://token-plan-cn.xiaomimimo.com/v1/chat/completions"


@respx.mock
async def test_synthesize_audio_content_type():
    route = respx.post(API_URL).respond(
        headers={"Content-Type": "audio/wav"}, content=b"fake-wav-bytes"
    )
    provider = MimoTTSProvider(MimoTTSConfig(api_key="mk"))

    chunks = [chunk async for chunk in provider.synthesize("你好", "Chloe")]

    assert chunks == [b"fake-wav-bytes"]
    request_body = json.loads(route.calls[0].request.content)
    assert request_body["model"] == "mimo-v2.5-tts"
    assert request_body["audio"] == {"format": "wav", "voice": "Chloe"}
    assert route.calls[0].request.headers["authorization"] == "Bearer mk"
    assert route.calls[0].request.headers["api-key"] == "mk"


@respx.mock
async def test_synthesize_base64_json_response(load_fixture):
    respx.post(API_URL).respond(json=load_fixture("mimo_tts_audio_json.json"))
    provider = MimoTTSProvider(MimoTTSConfig(api_key="mk"))

    chunks = [chunk async for chunk in provider.synthesize("你好", "Chloe")]

    assert chunks == [b"fake-wav-from-b64"]


@respx.mock
async def test_synthesize_missing_audio_raises():
    respx.post(API_URL).respond(json={"choices": [{"message": {}}]})
    provider = MimoTTSProvider(MimoTTSConfig(api_key="mk"))

    with pytest.raises(MimoTTSError):
        async for _ in provider.synthesize("你好", "Chloe"):
            pass


async def test_missing_api_key_raises():
    provider = MimoTTSProvider(MimoTTSConfig(api_key=""))
    with pytest.raises(ValueError):
        async for _ in provider.synthesize("你好", "Chloe"):
            pass
