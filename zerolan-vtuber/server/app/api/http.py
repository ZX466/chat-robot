"""HTTP 端点：/playground/microphone 语音上传、/resource/file、/health（§7）。

multipart："audio"=WAV 文件、"metadata"=JSON{Channels,SampleRate}；
响应沿用客户端 HttpResponseBody{code,message} 风格（D4：code 0=Success/1=Failed，
HTTP status 与 body.code 解耦，http status 保留 200/4xx/5xx）。
"""

import json
import re

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse

from app.config import Settings
from app.core.orchestrator import Orchestrator

# codex P2-5:session_id 白名单——字母数字下划线连字符,8-64 位
_SESSION_ID_RE = re.compile(r"[A-Za-z0-9_-]{8,64}")


def setup_http_routes(app: FastAPI, orchestrator: Orchestrator, settings: Settings) -> None:
    audio_dir = settings.server.audio_dir
    audio_dir.mkdir(parents=True, exist_ok=True)
    models_dir = settings.server.models_dir
    models_dir.mkdir(parents=True, exist_ok=True)

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

        # 会话透传（口子）：客户端可携 SessionId/session_id 复用同一语音上下文；
        # 缺省仍为 "voice"（单会话语义，客户端配合由 opencode 负责）。
        # 校验（codex P2-5）：session_id 直进 history 键与日志——限 字母数字下划线连字符，
        # 防日志注入（换行伪造日志行）、超大键内存放大、ws 会话槽位覆写。
        session_id = str(meta.get("SessionId") or meta.get("session_id") or "").strip()
        if not _SESSION_ID_RE.fullmatch(session_id):
            session_id = "voice"

        fmt = (audio.filename or "wav").rsplit(".", 1)[-1].lower()
        try:
            text = await orch.transcribe_audio(wave, fmt, sample_rate, channels)
        except Exception as exc:  # noqa: BLE001 — ASR 失败回错误码
            raise HTTPException(
                status_code=500, detail={"code": 1, "message": f"ASR failed: {exc}"}
            ) from exc
        # 语音识别文本走编排链路（字幕/音频经 orchestrator output_callback 广播到 WS）
        try:
            async for _evt in orch.process_text(session_id, text, source="voice"):
                pass
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(
                status_code=500, detail={"code": 1, "message": f"Processing failed: {exc}"}
            ) from exc
        return {"code": 0, "message": "ok", "data": {"transcript": text}}

    @app.get("/resource/file")
    async def resource_file(file_id: str) -> FileResponse:
        """客户端下载凭据：file_id 即 play_speech 的 file_id（D1 对齐 GetAudioClipAsync）。

        file_id 形如 ``model:rice`` 时从 Live2D 模型目录取 zip（Content-Disposition
        交由客户端按扩展名落盘），其余按音频 WAV 处理。
        """
        if file_id.startswith("model:"):
            model_name = file_id.split(":", 1)[1]
            if not model_name.isalnum():
                raise HTTPException(status_code=400, detail={"code": 1, "message": "Invalid model"})
            path = models_dir / f"{model_name}.zip"
            if not path.exists():
                raise HTTPException(
                    status_code=404, detail={"code": 1, "message": "Model not found"}
                )
            return FileResponse(path, media_type="application/zip", filename=path.name)
        if not file_id or not file_id.replace("_", "").replace("-", "").isalnum():
            raise HTTPException(status_code=400, detail={"code": 1, "message": "Invalid file_id"})
        # 文件扩展名随合成格式（5296f91 起 ws 层按 TTS audio_format 落盘，默认 mp3）；
        # 逐个探测，media_type 与实际格式对齐（客户端按字节流解码不依赖此值，但语义正确）
        for fmt, media_type in (
            ("mp3", "audio/mpeg"),
            ("wav", "audio/wav"),
            ("opus", "audio/opus"),
            ("aac", "audio/aac"),
            ("flac", "audio/flac"),
            ("pcm", "application/octet-stream"),
        ):
            path = audio_dir / f"{file_id}.{fmt}"
            if path.exists():
                return FileResponse(path, media_type=media_type)
        raise HTTPException(status_code=404, detail={"code": 1, "message": "Not found"})
