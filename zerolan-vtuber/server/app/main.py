"""FastAPI 入口：挂载 WS 与 HTTP 路由，装配 providers/tools/orchestrator。"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket
from loguru import logger

from app.api.http import setup_http_routes
from app.api.ws import WSHub
from app.config import settings
from app.core.agent_loop import AgentLoop
from app.core.history import History
from app.core.orchestrator import Orchestrator
from app.providers.config import ASRSlotConfig, BaiduASRConfig, BaiduTTSConfig, TTSSlotConfig
from app.providers.llm import LLMProvider
from app.tools.registry import ToolRegistry
from app.tools.web_search import register_web_search

SYSTEM_PROMPT = (
    "你是虚拟主播，用自然亲切的中文口语化回答用户。"
    "回答控制在 2-4 句以内，适合语音播报；需要事实信息时使用工具获取，并引用来源域名。"
)


def build_orchestrator() -> Orchestrator:
    """装配完整依赖：providers → tools → agent_loop → orchestrator。"""
    history = History(settings.history.db_path)

    asr_config: ASRSlotConfig = BaiduASRConfig(
        api_key=settings.asr.api_key or "",
        secret_key=settings.asr.api_key or "",
    )
    tts_config: TTSSlotConfig = BaiduTTSConfig(
        api_key=settings.tts.api_key or "",
        secret_key=settings.tts.api_key or "",
    )

    llm = LLMProvider(settings.llm)

    registry = ToolRegistry()
    register_web_search(registry)

    agent_loop = AgentLoop(llm, registry)
    return Orchestrator(
        asr_config=asr_config,
        tts_config=tts_config,
        agent_loop=agent_loop,
        registry=registry,
        history=history,
        system_prompt=SYSTEM_PROMPT,
    )


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    await app.state.history.init()
    logger.info(
        "zerolan-vtuber server started: ws={} http={}",
        settings.server.ws_port,
        settings.server.http_port,
    )
    yield
    await app.state.history.close()


app = FastAPI(title="zerolan-vtuber", version="0.1.0", lifespan=lifespan)

orchestrator = build_orchestrator()
app.state.orchestrator = orchestrator
app.state.history = orchestrator._history  # noqa: SLF001 — 装配期访问

hub = WSHub(orchestrator, settings)
setup_http_routes(app, orchestrator, settings)


@app.websocket("/ws")
async def ws_endpoint(websocket: WebSocket) -> None:
    await hub.handle(websocket)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
