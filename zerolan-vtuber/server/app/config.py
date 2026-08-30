"""配置：单一 config.yaml + 环境变量覆盖（pydantic-settings）。

key 来源优先级：config.yaml（UI 保存）> 环境变量（headless/CI）。
config.yaml / .env 均不入 git（server/.gitignore）。
"""

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_DIR = Path(__file__).resolve().parents[2]


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
    model: str | None = None


class TTSConfig(BaseModel):
    vendor: Literal["baidu", "mimo"] = "baidu"
    base_url: str | None = None
    api_key: str | None = None
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


class BroadcastConfig(BaseModel):
    enabled: bool = False
    cron: str | None = None  # "HH:MM"


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
        """载入 config.yaml（存在则优先），环境变量覆盖之。"""
        config_file = PROJECT_DIR / "config.yaml"
        if config_file.exists():
            return cls(_env_file=(config_file, PROJECT_DIR / ".env"))  # type: ignore[call-arg]  # noqa: PGH003
        return cls()


settings = Settings.load()
