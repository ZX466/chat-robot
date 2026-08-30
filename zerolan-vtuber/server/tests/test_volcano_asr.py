import json

import httpx
import pytest
import respx

from app.providers.asr.volcano import VolcanoASRError, VolcanoASRProvider
from app.providers.config import VolcanoASRConfig

AUDIO = b"fake-raw-pcm-audio"
SUBMIT_URL = "https://openspeech.bytedance.com/api/v3/auc/bigmodel/submit"
QUERY_URL = "https://openspeech.bytedance.com/api/v3/auc/bigmodel/query"


def _provider() -> VolcanoASRProvider:
    return VolcanoASRProvider(
        VolcanoASRConfig(api_key="ak", poll_interval=0.0, max_poll_times=5)
    )


@respx.mock
async def test_transcribe_done_from_utterances(load_fixture):
    submit_route = respx.post(SUBMIT_URL).respond(
        headers={"X-Api-Status-Code": "20000001"}, json={}
    )
    query_route = respx.post(QUERY_URL).mock(
        side_effect=[
            httpx.Response(200, headers={"X-Api-Status-Code": "20000001"}, json={}),
            httpx.Response(
                200,
                headers={"X-Api-Status-Code": "20000000"},
                json=load_fixture("volcano_query_done.json"),
            ),
        ]
    )
    provider = _provider()

    transcript = await provider.transcribe(AUDIO, "wav")

    assert transcript == "今天天气 怎么样"
    assert submit_route.call_count == 1
    assert query_route.call_count == 2

    submit_request = json.loads(submit_route.calls[0].request.content)
    assert submit_request["audio"]["format"] == "wav"
    assert submit_request["audio"]["rate"] == 16000
    assert submit_request["request"]["model_name"] == "bigmodel"
    assert submit_route.calls[0].request.headers["x-api-key"] == "ak"
    assert submit_route.calls[0].request.headers["X-Api-Resource-Id"] == "volc.bigasr.auc"


@respx.mock
async def test_transcribe_text_result():
    respx.post(SUBMIT_URL).respond(headers={"X-Api-Status-Code": "20000001"}, json={})
    respx.post(QUERY_URL).mock(
        side_effect=[
            httpx.Response(
                200,
                headers={"X-Api-Status-Code": "20000000"},
                json={"result": {"text": "直接文本", "utterances": []}},
            )
        ]
    )
    provider = _provider()

    assert await provider.transcribe(AUDIO, "wav") == "直接文本"


@respx.mock
async def test_transcribe_silent_audio_returns_empty():
    respx.post(SUBMIT_URL).respond(headers={"X-Api-Status-Code": "20000001"}, json={})
    respx.post(QUERY_URL).mock(
        side_effect=[
            httpx.Response(200, headers={"X-Api-Status-Code": "20000003"}, json={})
        ]
    )
    provider = _provider()

    assert await provider.transcribe(AUDIO, "wav") == ""


@respx.mock
async def test_transcribe_failure_raises():
    respx.post(SUBMIT_URL).respond(headers={"X-Api-Status-Code": "20000001"}, json={})
    respx.post(QUERY_URL).mock(
        side_effect=[
            httpx.Response(
                200,
                headers={"X-Api-Status-Code": "45000001", "X-Api-Message": "bad request"},
                json={},
            )
        ]
    )
    provider = _provider()

    with pytest.raises(VolcanoASRError):
        await provider.transcribe(AUDIO, "wav")


@respx.mock
async def test_transcribe_timeout():
    respx.post(SUBMIT_URL).respond(headers={"X-Api-Status-Code": "20000001"}, json={})
    respx.post(QUERY_URL).mock(
        side_effect=[
            httpx.Response(200, headers={"X-Api-Status-Code": "20000001"}, json={})
        ]
        * 10
    )
    provider = _provider()

    with pytest.raises(TimeoutError):
        await provider.transcribe(AUDIO, "wav")


async def test_empty_audio_raises():
    provider = _provider()
    with pytest.raises(ValueError):
        await provider.transcribe(b"", "wav")
