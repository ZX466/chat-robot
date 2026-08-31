from urllib.parse import parse_qs

import pytest
import respx

from app.providers.config import BaiduTTSConfig
from app.providers.tts.baidu import BaiduTTSError, BaiduTTSProvider

TOKEN_URL = "https://aip.baidubce.com/oauth/2.0/token"


def _provider() -> BaiduTTSProvider:
    return BaiduTTSProvider(BaiduTTSConfig(api_key="ak", secret_key="sk"))


@respx.mock
async def test_synthesize_audio_response():
    respx.post(TOKEN_URL).respond(json={"access_token": "tok-1", "expires_in": 2592000})
    tts_route = respx.post("https://tsn.baidu.com/text2audio").respond(
        headers={"Content-Type": "audio/mp3"}, content=b"fake-mp3-bytes"
    )
    provider = _provider()

    chunks = [chunk async for chunk in provider.synthesize("你好", "1")]

    assert chunks == [b"fake-mp3-bytes"]
    form = parse_qs(tts_route.calls[0].request.content.decode())
    assert form["tok"] == ["tok-1"]
    assert form["tex"] == ["你好"]
    assert form["per"] == ["1"]
    assert form["aue"] == ["3"]  # mp3
    assert form["lan"] == ["zh"]


@respx.mock
async def test_synthesize_voice_mapped_to_per():
    respx.post(TOKEN_URL).respond(json={"access_token": "tok-1", "expires_in": 2592000})
    tts_route = respx.post("https://tsn.baidu.com/text2audio").respond(
        headers={"Content-Type": "audio/mp3"}, content=b"x"
    )
    provider = _provider()

    _ = [chunk async for chunk in provider.synthesize("你好", "4")]

    form = parse_qs(tts_route.calls[0].request.content.decode())
    assert form["per"] == ["4"]


@respx.mock
async def test_synthesize_json_error_raises(load_fixture):
    respx.post(TOKEN_URL).respond(json={"access_token": "tok-1", "expires_in": 2592000})
    respx.post("https://tsn.baidu.com/text2audio").respond(json=load_fixture("baidu_tts_err.json"))
    provider = _provider()

    with pytest.raises(BaiduTTSError):
        async for _ in provider.synthesize("你好", "1"):
            pass


async def test_empty_text_raises():
    provider = _provider()
    with pytest.raises(ValueError):
        async for _ in provider.synthesize("", "1"):
            pass
