"""WebSocket 端点：Zerolan 协议（§7 兼容红线）。

- client_hello → server_hello（含 provider 掩码）
- 文本 → orchestrator → show_user_text_input/add_history → play_speech(url)
- update_provider_config → 校验 → 热替换 → ack
- ping → pong 心跳协作
"""

import uuid
from typing import Any

from fastapi import WebSocket, WebSocketDisconnect
from loguru import logger

from app.config import Settings
from app.core.orchestrator import Orchestrator
from app.protocol.models import ZerolanProtocol


def mask_key(key: str | None) -> str:
    """掩码 API key 供客户端回显：保留前 4 字符 + 尾部 3 字符，如 deepseek/k***。"""
    if not key:
        return "未配置"
    if len(key) <= 7:
        return key[0] + "***"
    return f"{key[:6]}{'*' * (len(key) - 9)}{key[-3:]}"


class WSHub:
    def __init__(self, orchestrator: Orchestrator, settings: Settings) -> None:
        self._orchestrator = orchestrator
        self._settings = settings
        self._audio_dir = settings.server.audio_dir
        self._audio_dir.mkdir(parents=True, exist_ok=True)
        self._connections: dict[str, WebSocket] = {}
        orchestrator.set_output_callback(self._on_orchestrator_output)

    async def _on_orchestrator_output(self, session_id: str, evt: dict[str, object]) -> None:
        """orchestrator 事件 → 协议消息下发（字幕/音频）。"""
        evt_type = evt.get("type")
        if evt_type == "user_text":
            text = str(evt.get("text", ""))
            await self._broadcast(
                {
                    "message": "User text",
                    "action": "show_user_text_input",
                    "code": 0,
                    "data": {"text": text},
                }
            )
            await self._broadcast(
                {
                    "message": "History",
                    "action": "add_history",
                    "code": 0,
                    "data": {"role": "user", "content": text},
                }
            )
        elif evt_type == "speech":
            wave = evt.get("bytes")
            if not isinstance(wave, bytes):
                return
            audio_id = uuid.uuid4().hex
            (self._audio_dir / f"{audio_id}.wav").write_bytes(wave)
            http_url = f"http://{self._settings.server.ws_host}:{self._settings.server.http_port}"
            await self._broadcast(
                {
                    "message": "Speech",
                    "action": "play_speech",
                    "code": 0,
                    "data": {"url": f"{http_url}/audio/{audio_id}"},
                }
            )

    async def handle(self, ws: WebSocket) -> None:
        await ws.accept()
        session_id = str(uuid.uuid4())
        self._connections[session_id] = ws
        logger.info("ws connected: session={}", session_id)
        try:
            while True:
                raw = await ws.receive_text()
                await self._dispatch(ws, session_id, raw)
        except WebSocketDisconnect:
            logger.info("ws disconnected: session={}", session_id)
        finally:
            self._connections.pop(session_id, None)

    async def _dispatch(self, ws: WebSocket, session_id: str, raw: str) -> None:
        try:
            msg = ZerolanProtocol.model_validate_json(raw)
        except Exception as exc:  # noqa: BLE001 — 非法消息回错误码
            logger.warning("invalid protocol message: {}", exc)
            await self._send(
                ws,
                {
                    "message": "Malformed protocol message",
                    "action": "remote_error",
                    "code": 400,
                    "data": None,
                },
            )
            return

        handler = {
            "client_hello": self._on_client_hello,
            "update_provider_config": self._on_update_provider_config,
            "ping": self._on_ping,
        }.get(msg.action)
        if handler is not None:
            await handler(ws, session_id, msg)
            return

        # 客户端无专用文本 action：宽松兜底——任何 action 携带 data.text/content 视为用户文本
        data = msg.data if isinstance(msg.data, dict) else {}
        text = str(data.get("text") or data.get("content") or "")
        if text:
            logger.debug("treating action {} as user text", msg.action)
            await self._on_user_text(ws, session_id, text)
            return
        await self._send(
            ws,
            {
                "message": f"Unhandled action: {msg.action}",
                "action": "remote_error",
                "code": 400,
                "data": None,
            },
        )

    async def _send(self, ws: WebSocket, payload: dict[str, Any]) -> None:
        await ws.send_text(ZerolanProtocol(**payload).model_dump_json())

    async def _on_ping(self, ws: WebSocket, session_id: str, msg: ZerolanProtocol) -> None:
        await self._send(ws, {"message": "pong", "action": "ping", "code": 0, "data": None})

    async def _on_user_text(self, ws: WebSocket, session_id: str, text: str) -> None:
        """用户文本 → orchestrator（字幕/音频经 output_callback 广播）。"""
        logger.info("user text (session {}): {}", session_id, text[:80])
        try:
            async for _evt in self._orchestrator.process_text(session_id, text):
                pass  # 输出事件已由 _on_orchestrator_output 广播
        except Exception as exc:  # noqa: BLE001 — 编排失败回错误码
            logger.error("orchestrator failed: {}", exc)
            await self._send(
                ws,
                {
                    "message": f"Processing failed: {exc}",
                    "action": "remote_error",
                    "code": 500,
                    "data": None,
                },
            )

    async def _broadcast(self, payload: dict[str, Any]) -> None:
        for ws in list(self._connections.values()):
            try:
                await self._send(ws, payload)
            except Exception:  # noqa: BLE001 — 单连接失败不影响其他
                logger.debug("broadcast failed to a connection")

    async def _on_client_hello(self, ws: WebSocket, session_id: str, msg: ZerolanProtocol) -> None:
        s = self._settings
        asr_key = getattr(s.asr, "api_key", None) or None
        data = {
            "ws_url": f"ws://{s.server.ws_host}:{s.server.ws_port}/ws",
            "http_url": f"http://{s.server.ws_host}:{s.server.http_port}",
            "llm_provider": f"{s.llm.model}",
            "asr_provider": f"{mask_key(asr_key) if asr_key else s.asr.vendor}",
            "tts_provider": f"{s.tts.vendor}",
        }
        await self._send(
            ws,
            {"message": "Server hello!", "action": "server_hello", "code": 200, "data": data},
        )
        logger.info("server_hello sent to session {}", session_id)

    async def _on_update_provider_config(
        self, ws: WebSocket, session_id: str, msg: ZerolanProtocol
    ) -> None:
        data = msg.data or {}
        errors = _validate_provider_config(data)
        if errors:
            await self._send(
                ws,
                {
                    "message": "; ".join(errors),
                    "action": "update_provider_config",
                    "code": 400,
                    "data": None,
                },
            )
            return
        # 热替换：asr/tts 槽位重建
        try:
            await self._orchestrator.hot_swap(
                asr_config=_build_asr_config(data.get("asr")),
                tts_config=_build_tts_config(data.get("tts")),
            )
        except Exception as exc:  # noqa: BLE001 — 热替换失败回错误码
            logger.error("hot swap failed: {}", exc)
            await self._send(
                ws,
                {
                    "message": f"Provider rebuild failed: {exc}",
                    "action": "update_provider_config",
                    "code": 400,
                    "data": None,
                },
            )
            return
        await self._send(
            ws,
            {
                "message": "Provider config updated",
                "action": "update_provider_config",
                "code": 200,
                "data": None,
            },
        )
        logger.info("provider config hot-swapped for session {}", session_id)


def _validate_provider_config(data: Any) -> list[str]:
    """校验 update_provider_config：vendor 合法、URL 合法、必填非空。"""
    errors: list[str] = []
    for slot in ("asr", "tts"):
        cfg = data.get(slot) if isinstance(data, dict) else None
        if cfg is None:
            continue
        vendor = cfg.get("vendor")
        if vendor not in ("baidu", "volcano", "mimo"):
            errors.append(f"{slot}.vendor must be one of baidu/volcano/mimo")
        url = cfg.get("base_url")
        if url and not str(url).startswith(("http://", "https://")):
            errors.append(f"{slot}.base_url must be http(s) URL")
        for key in ("api_key", "base_url", "model", "vendor"):
            if cfg.get(key) is None:
                errors.append(f"{slot}.{key} is required")
    return errors


def _build_asr_config(data: Any) -> Any:
    from app.providers.config import BaiduASRConfig, VolcanoASRConfig

    vendor = data.get("vendor")
    common: dict[str, object] = {
        k: v
        for k, v in data.items()
        if k in ("base_url", "api_key", "model") and v is not None
    }
    if vendor == "volcano":
        return VolcanoASRConfig.model_validate(common)
    return BaiduASRConfig.model_validate(common)


def _build_tts_config(data: Any) -> Any:
    from app.providers.config import BaiduTTSConfig, MimoTTSConfig

    vendor = data.get("vendor")
    common: dict[str, object] = {
        k: v
        for k, v in data.items()
        if k in ("base_url", "api_key", "model", "voice") and v is not None
    }
    if vendor == "mimo":
        return MimoTTSConfig.model_validate(common)
    return BaiduTTSConfig.model_validate(common)
