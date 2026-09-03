"""配置：单一 config.yaml + 环境变量覆盖（pydantic-settings）。

key 来源优先级：config.yaml（UI 保存）> 环境变量（headless/CI）。
config.yaml / .env 均不入 git（server/.gitignore）。
"""

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_DIR = Path(__file__).resolve().parents[2]  # zerolan-vtuber/
SERVER_DIR = Path(__file__).resolve().parents[1]  # zerolan-vtuber/server/


class LLMConfig(BaseModel):
    base_url: str | None = None
    api_key: str | None = None
    model: str = "deepseek/deepseek-chat"
    fallback_models: list[str] = Field(default_factory=list)
    temperature: float = 0.8


class ASRConfig(BaseModel):
    vendor: Literal["baidu", "volcano"] = "baidu"
    base_url: str | None = None
    api_key: str | None = None
    secret_key: str | None = None  # 百度 AK/SK 双 key（P1-1）
    model: str | None = None


class TTSConfig(BaseModel):
    vendor: Literal["baidu", "mimo"] = "baidu"
    base_url: str | None = None
    api_key: str | None = None
    secret_key: str | None = None  # 百度 AK/SK 双 key（P1-1）
    model: str | None = None
    voice: str | None = None


class WebSearchConfig(BaseModel):
    provider: Literal["tavily", "ddgs"] = "tavily"


class SixtyApiConfig(BaseModel):
    base_url: str = "https://60s.viki.moe"


class ToolsConfig(BaseModel):
    web_search: WebSearchConfig = WebSearchConfig()
    sixty_api: SixtyApiConfig = SixtyApiConfig()


class ServerConfig(BaseModel):
    ws_host: str = "127.0.0.1"
    ws_port: int = 8090
    http_port: int = 8091
    audio_dir: Path = PROJECT_DIR / "audio_assets"
    models_dir: Path = PROJECT_DIR / "models"
    live2d_model: str | None = None  # models_dir 下的模型名（不含 .zip），非空时 server_hello 下发


class BroadcastConfig(BaseModel):
    enabled: bool = False
    cron: str | None = None  # "HH:MM"
    text: str = "大家好，欢迎回来！"  # 定时播报文案（§9-9）


class HistoryConfig(BaseModel):
    db_path: Path = PROJECT_DIR / "data" / "history.db"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=PROJECT_DIR / ".env",
        env_nested_delimiter="__",
        extra="ignore",
        protected_namespaces=(),
    )

    llm: LLMConfig = LLMConfig()
    asr: ASRConfig = ASRConfig()
    tts: TTSConfig = TTSConfig()
    tools: ToolsConfig = ToolsConfig()
    server: ServerConfig = ServerConfig()
    broadcast: BroadcastConfig = BroadcastConfig()
    history: HistoryConfig = HistoryConfig()

    @classmethod
    def load(cls) -> "Settings":
        """载入 config.yaml（server/ 优先，兼容仓库根），环境变量覆盖之。

        注意：pydantic-settings 的 _env_file 只认 dotenv 格式，YAML 必须手动
        解析后以 kwargs 注入（否则静默失效，server_hello 永远不带 live2d_model）。
        """
        for base in (SERVER_DIR, PROJECT_DIR):
            config_file = base / "config.yaml"
            if config_file.exists():
                data = yaml.safe_load(config_file.read_text(encoding="utf-8")) or {}
                return cls(**data)
        return cls()


settings = Settings.load()
