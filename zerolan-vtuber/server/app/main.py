"""FastAPI 入口：挂载 WS 与 HTTP 路由，装配 providers/tools/orchestrator。"""

import asyncio
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

# .env → os.environ：pydantic-settings 的 env_file 只注入 Settings 字段，不会
# export 到进程环境；而 ddgs 读的是 os.environ["DDGS_PROXY"]（搜索引擎代理，
# 国内网络直连不可达时必填），litellm 供应商 key 兜底同理。必须在任何 provider
# 导入前加载（下方 E402 豁免即为此）。python-dotenv 由 litellm 传递依赖提供。
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

# 部署健壮性：litellm 导入时默认尝试联网拉模型价目表（无网环境会静默挂起）。
# 强制本地价目表回退；如需联网更新可显式设 LITELLM_LOCAL_MODEL_COST_MAP=False。
os.environ.setdefault("LITELLM_LOCAL_MODEL_COST_MAP", "True")
os.environ.setdefault("LITELLM_LOG", "ERROR")

from fastapi import FastAPI, WebSocket  # noqa: E402 — 需在 .env 加载后导入
from loguru import logger  # noqa: E402

from app.api.http import setup_http_routes  # noqa: E402
from app.api.ws import WSHub  # noqa: E402
from app.config import settings  # noqa: E402
from app.core.agent_loop import AgentLoop  # noqa: E402
from app.core.broadcast import BroadcastScheduler  # noqa: E402
from app.core.history import History  # noqa: E402
from app.core.orchestrator import Orchestrator  # noqa: E402
from app.providers.config import (  # noqa: E402 — 需在 .env 加载后导入
    ASRSlotConfig,
    BaiduASRConfig,
    BaiduTTSConfig,
    MimoTTSConfig,
    OpenAIASRConfig,
    OpenAITTSConfig,
    TTSSlotConfig,
    VolcanoASRConfig,
)
from app.providers.llm import LLMProvider  # noqa: E402
from app.tools.registry import ToolRegistry  # noqa: E402
from app.tools.sixty_api import register_sixty_api  # noqa: E402
from app.tools.web_search import register_web_search  # noqa: E402

SYSTEM_PROMPT = (
    "你是虚拟主播，用自然亲切的中文口语化回答用户。"
    "回答控制在 2-4 句以内，适合语音播报；需要事实信息时使用工具获取，并引用来源域名。"
)


def build_orchestrator() -> Orchestrator:
    """装配完整依赖：providers → tools → agent_loop → orchestrator。"""
    history = History(settings.history.db_path)

    # P1-2：按 settings 的 vendor 构建槽位（非法值换代默认走 baidu）
    asr_cfg = settings.asr
    if asr_cfg.vendor == "volcano":
        asr_config: ASRSlotConfig = VolcanoASRConfig(
            api_key=asr_cfg.api_key or "",
            base_url=asr_cfg.base_url or "",
            model=asr_cfg.model or "bigmodel",
        )
    elif asr_cfg.vendor == "openai":
        asr_config = OpenAIASRConfig(
            api_key=asr_cfg.api_key or "",
            base_url=asr_cfg.base_url or "https://api.openai.com",
            model=asr_cfg.model or "whisper-1",
        )
    else:
        asr_config = BaiduASRConfig(
            api_key=asr_cfg.api_key or "",
            secret_key=asr_cfg.secret_key or "",
        )

    tts_cfg = settings.tts
    if tts_cfg.vendor == "mimo":
        tts_config: TTSSlotConfig = MimoTTSConfig(
            api_key=tts_cfg.api_key or "",
            base_url=tts_cfg.base_url or "",
            model=tts_cfg.model or "mimo-v2.5-tts",
            voice=tts_cfg.voice or "Chloe",
        )
    elif tts_cfg.vendor == "openai":
        tts_config = OpenAITTSConfig(
            api_key=tts_cfg.api_key or "",
            base_url=tts_cfg.base_url or "https://api.openai.com",
            model=tts_cfg.model or "tts-1",
            voice=tts_cfg.voice or "alloy",
        )
    else:
        tts_config = BaiduTTSConfig(
            api_key=tts_cfg.api_key or "",
            secret_key=tts_cfg.secret_key or "",
        )

    llm = LLMProvider(settings.llm)

    registry = ToolRegistry()
    register_web_search(registry)
    register_sixty_api(registry)

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
    broadcast_task: asyncio.Task[None] | None = None
    if settings.broadcast.enabled:
        broker = BroadcastScheduler(
            orchestrator,
            cron=settings.broadcast.cron,
            text=settings.broadcast.text,
        )
        broadcast_task = asyncio.create_task(broker.run())
        logger.info(
            "broadcast scheduler enabled: cron={} text={!r}",
            settings.broadcast.cron,
            settings.broadcast.text,
        )
    yield
    if broadcast_task is not None:
        broadcast_task.cancel()
        try:
            await broadcast_task
        except asyncio.CancelledError:
            logger.info("broadcast scheduler stopped")
    await app.state.history.close()
    # P2(codex)：关停时释放 httpx 共享连接池（ASR/TTS/LLM/web_search 共用）
    from app.providers.http import close_shared_client

    await close_shared_client()


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
