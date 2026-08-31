"""HTTP 端点：/playground/microphone 语音上传、/audio/{id}、/health（§7）。

multipart："audio"=WAV 文件、"metadata"=JSON{Channels,SampleRate}；
响应沿用客户端 HttpResponseBody{code,message} 风格。
"""

import json

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse

from app.config import Settings
from app.core.orchestrator import Orchestrator


def setup_http_routes(app: FastAPI, orchestrator: Orchestrator, settings: Settings) -> None:
    audio_dir = settings.server.audio_dir
    audio_dir.mkdir(parents=True, exist_ok=True)

    @app.post("/playground/microphone")
    async def playground_microphone(
        audio: UploadFile = File(...),  # noqa: B008 — FastAPI 注入约定
        metadata: str = Form(...),  # noqa: B008 — FastAPI 注入约定
    ) -> dict[str, object]:
        """客户端麦克风开关关闭时上传 16kHz WAV → ASR → 文本链路。"""
        orch: Orchestrator = app.state.orchestrator
        try:
            meta = json.loads(metadata)
            sample_rate = int(meta.get("SampleRate", meta.get("sample_rate", 16000)))
            channels = int(meta.get("Channels", meta.get("channels", 1)))
        except (ValueError, TypeError) as exc:
            raise HTTPException(
                status_code=400, detail={"code": 400, "message": "Invalid metadata"}
            ) from exc

        wave = await audio.read()
        if not wave:
            raise HTTPException(status_code=400, detail={"code": 400, "message": "Empty audio"})

        fmt = (audio.filename or "wav").rsplit(".", 1)[-1].lower()
        try:
            text = await orch.transcribe_audio(wave, fmt, sample_rate, channels)
        except Exception as exc:  # noqa: BLE001 — ASR 失败回错误码
            raise HTTPException(
                status_code=500, detail={"code": 500, "message": f"ASR failed: {exc}"}
            ) from exc
        # 语音识别文本走编排链路（字幕/音频经 orchestrator output_callback 广播到 WS）
        try:
            async for _evt in orch.process_text("voice", text):
                pass
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(
                status_code=500, detail={"code": 500, "message": f"Processing failed: {exc}"}
            ) from exc
        return {"code": 200, "message": "ok", "data": {"transcript": text}}

    @app.get("/audio/{audio_id}")
    async def get_audio(audio_id: str) -> FileResponse:
        path = audio_dir / f"{audio_id}.wav"
        if not path.exists():
            raise HTTPException(status_code=404, detail={"code": 404, "message": "Not found"})
        return FileResponse(path, media_type="audio/wav")
