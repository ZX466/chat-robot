import json

import pytest
import respx

from app.providers.asr.baidu import BaiduASRError, BaiduASRProvider
from app.providers.config import BaiduASRConfig

AUDIO = b"RIFF\x24\x00\x00\x00WAVEfmt fake-pcm-audio"
TOKEN_URL = "https://aip.baidubce.com/oauth/2.0/token"


def _provider() -> BaiduASRProvider:
    return BaiduASRProvider(BaiduASRConfig(api_key="ak", secret_key="sk"))


@respx.mock
async def test_transcribe_ok(load_fixture):
    token_route = respx.post(TOKEN_URL).respond(
        json={"access_token": "tok-1", "expires_in": 2592000}
    )
    asr_route = respx.post("https://vop.baidu.com/server_api").respond(
        json=load_fixture("baidu_asr_ok.json")
    )
    provider = _provider()

    transcript = await provider.transcribe(AUDIO, "wav")

    assert transcript == "你好世界"
    assert token_route.call_count == 1
    request_body = json.loads(asr_route.calls[0].request.content)
    assert request_body["token"] == "tok-1"
    assert request_body["format"] == "wav"
    assert request_body["rate"] == 16000
    assert request_body["channel"] == 1
    assert request_body["len"] == len(AUDIO)
    assert request_body["cuid"] == provider._cuid


@respx.mock
async def test_transcribe_err_no_raises(load_fixture):
    respx.post(TOKEN_URL).respond(json={"access_token": "tok-1", "expires_in": 2592000})
    respx.post("https://vop.baidu.com/server_api").respond(json=load_fixture("baidu_asr_err.json"))
    provider = _provider()

    with pytest.raises(BaiduASRError):
        await provider.transcribe(AUDIO, "wav")


@respx.mock
async def test_transcribe_empty_result_raises(load_fixture):
    respx.post(TOKEN_URL).respond(json={"access_token": "tok-1", "expires_in": 2592000})
    respx.post("https://vop.baidu.com/server_api").respond(
        json={"err_no": 0, "err_msg": "OK.", "result": [], "sn": "sn-003"}
    )
    provider = _provider()

    with pytest.raises(BaiduASRError):
        await provider.transcribe(AUDIO, "wav")


async def test_empty_audio_raises():
    provider = _provider()
    with pytest.raises(ValueError):
        await provider.transcribe(b"", "wav")
