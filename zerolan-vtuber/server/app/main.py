"""FastAPI 入口：挂载 WS 与 HTTP 路由（骨架，功能逐步填充）。"""

from fastapi import FastAPI

from app.config import settings
from app.core.history import History

app = FastAPI(title="zerolan-vtuber", version="0.1.0")

history = History(settings.history.db_path)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.on_event("startup")
async def startup() -> None:
    await history.init()


@app.on_event("shutdown")
async def shutdown() -> None:
    await history.close()
