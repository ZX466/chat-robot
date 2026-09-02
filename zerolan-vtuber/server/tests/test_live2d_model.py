"""Live2D 模型下发（方案 B）：/resource/file 支持 model:<name> + server_hello 携带 live2d_model。"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from zipfile import ZipFile

import pytest

from app.config import ASRConfig, LLMConfig, ServerConfig, Settings, TTSConfig


def make_settings(tmp_path: Path, *, live2d_model: str | None = None) -> Settings:
    return Settings(
        llm=LLMConfig(model="openai/gpt-4o-mini"),
        asr=ASRConfig(vendor="baidu"),
        tts=TTSConfig(vendor="baidu"),
        server=ServerConfig(
            audio_dir=tmp_path / "audio",
            models_dir=tmp_path / "models",
            live2d_model=live2d_model,
        ),
    )


@pytest.fixture()
def model_zip(tmp_path: Path) -> Path:
    """在临时 models_dir 放一个可下载的模型 zip。"""
    models = tmp_path / "models"
    models.mkdir(parents=True)
    zip_path = models / "rice.zip"
    with ZipFile(zip_path, "w") as zf:
        zf.writestr("Rice/Rice.model3.json", "{}")
    return zip_path


def _http_app(settings: Settings) -> Any:
    from fastapi import FastAPI

    from app.api.http import setup_http_routes

    app = FastAPI()
    setup_http_routes(app, orchestrator=None, settings=settings)  # type: ignore[arg-type]
    return app


@pytest.mark.asyncio
async def test_resource_file_serves_model_zip(tmp_path: Path, model_zip: Path) -> None:
    from httpx import ASGITransport, AsyncClient

    app = _http_app(make_settings(tmp_path))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        resp = await client.get("/resource/file", params={"file_id": "model:rice"})
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("application/zip")
    assert b"model3.json" in resp.content or len(resp.content) > 0


@pytest.mark.asyncio
async def test_resource_file_model_not_found(tmp_path: Path) -> None:
    from httpx import ASGITransport, AsyncClient

    app = _http_app(make_settings(tmp_path))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        resp = await client.get("/resource/file", params={"file_id": "model:ghost"})
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_resource_file_rejects_bad_model_name(tmp_path: Path) -> None:
    from httpx import ASGITransport, AsyncClient

    app = _http_app(make_settings(tmp_path))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        resp = await client.get("/resource/file", params={"file_id": "model:../etc"})
    assert resp.status_code == 400
