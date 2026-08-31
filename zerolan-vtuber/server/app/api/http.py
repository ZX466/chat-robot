"""HTTP 端点：/playground/microphone 语音上传、/resource/file、/health（§7）。

multipart："audio"=WAV 文件、"metadata"=JSON{Channels,SampleRate}；
响应沿用客户端 HttpResponseBody{code,message} 风格（D4：code 0=Success/1=Failed，
HTTP status 与 body.code 解耦，http status 保留 200/4xx/5xx）。
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
                status_code=400, detail={"code": 1, "message": "Invalid metadata"}
            ) from exc

        wave = await audio.read()
        if not wave:
            raise HTTPException(status_code=400, detail={"code": 1, "message": "Empty audio"})

        fmt = (audio.filename or "wav").rsplit(".", 1)[-1].lower()
        try:
            text = await orch.transcribe_audio(wave, fmt, sample_rate, channels)
        except Exception as exc:  # noqa: BLE001 — ASR 失败回错误码
            raise HTTPException(
                status_code=500, detail={"code": 1, "message": f"ASR failed: {exc}"}
            ) from exc
        # 语音识别文本走编排链路（字幕/音频经 orchestrator output_callback 广播到 WS）
        try:
            async for _evt in orch.process_text("voice", text):
                pass
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(
                status_code=500, detail={"code": 1, "message": f"Processing failed: {exc}"}
            ) from exc
        return {"code": 0, "message": "ok", "data": {"transcript": text}}

    @app.get("/resource/file")
    async def resource_file(file_id: str) -> FileResponse:
        """客户端下载凭据：file_id 即 play_speech 的 file_id（D1 对齐 GetAudioClipAsync）。"""
        if not file_id.isalnum():
            raise HTTPException(status_code=400, detail={"code": 1, "message": "Invalid file_id"})
        path = audio_dir / f"{file_id}.wav"
        if not path.exists():
            raise HTTPException(status_code=404, detail={"code": 1, "message": "Not found"})
        return FileResponse(path, media_type="audio/wav")
