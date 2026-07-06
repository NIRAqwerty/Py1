import os
from typing import Any, Dict, List, Optional
import yaml
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class AppConfig(BaseModel):
    name: str = "Telegram AI Publisher"
    env: str = "production"
    debug: bool = False

class DBConfig(BaseModel):
    embedding_dimension: int = 1536

class RedisConfig(BaseModel):
    url: str = "redis://localhost:6379/0"

class LLMProviderConfig(BaseModel):
    model: str

class OllamaConfig(BaseModel):
    url: str
    model: str

class LLMConfig(BaseModel):
    active_provider: str = "gemini"
    temperature: float = 0.2
    max_tokens: int = 1500
    gemini: LLMProviderConfig = Field(default_factory=lambda: LLMProviderConfig(model="gemini-1.5-pro"))
    openai: LLMProviderConfig = Field(default_factory=lambda: LLMProviderConfig(model="gpt-4o"))
    claude: LLMProviderConfig = Field(default_factory=lambda: LLMProviderConfig(model="claude-3-5-sonnet"))
    ollama: OllamaConfig = Field(default_factory=lambda: OllamaConfig(url="http://localhost:11434", model="llama3"))

class TelegramScraperConfig(BaseModel):
    channels: List[str] = []

class ScraperConfig(BaseModel):
    check_interval: int = 300
    telegram: TelegramScraperConfig = Field(default_factory=TelegramScraperConfig)

class TelegramPublisherConfig(BaseModel):
    channel_id: str

class PublisherConfig(BaseModel):
    telegram: TelegramPublisherConfig

class ThresholdsConfig(BaseModel):
    ad_score: float = 0.75
    spam_score: float = 0.75
    toxicity_score: float = 0.60
    duplicate_cosine: float = 0.85
    human_review_confidence: float = 0.90

class SecurityConfig(BaseModel):
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 1440

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    app: AppConfig = Field(default_factory=AppConfig)
    db: DBConfig = Field(default_factory=DBConfig)
    redis: RedisConfig = Field(default_factory=RedisConfig)
    llm: LLMConfig = Field(default_factory=LLMConfig)
    scraper: ScraperConfig = Field(default_factory=ScraperConfig)
    publisher: PublisherConfig = Field(default_factory=lambda: PublisherConfig(telegram=TelegramPublisherConfig(channel_id="@my_channel")))
    thresholds: ThresholdsConfig = Field(default_factory=ThresholdsConfig)
    security: SecurityConfig = Field(default_factory=SecurityConfig)

    # Secrets from .env (overwriting variables directly in Settings)
    database_url: str = Field(default="postgresql+asyncpg://postgres:postgres@localhost:5432/telegram_ai")
    gemini_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None
    claude_api_key: Optional[str] = None
    openrouter_api_key: Optional[str] = None
    telegram_api_id: Optional[int] = None
    telegram_api_hash: Optional[str] = None
    telegram_session_string: Optional[str] = None
    telegram_bot_token: Optional[str] = None
    telegram_allowed_users: Optional[str] = None
    jwt_secret: str = "your_super_secret_jwt_key_here"

    @classmethod
    def load(cls) -> "Settings":
        config_path = os.getenv("CONFIG_PATH", "config.yaml")
        yaml_data: Dict[str, Any] = {}
        if os.path.exists(config_path):
            with open(config_path, "r", encoding="utf-8") as f:
                yaml_data = yaml.safe_load(f) or {}

        # Merge yaml properties with settings constructor
        return cls(**yaml_data)

settings = Settings.load()
