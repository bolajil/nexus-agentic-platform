"""
NEXUS Platform — Application Configuration
Pydantic-settings based configuration with environment variable support.
"""
from __future__ import annotations

from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── LLM ──────────────────────────────────────────────────────────────
    OPENAI_API_KEY: str = Field(default="", description="OpenAI API key")
    MODEL_NAME: str = Field(default="gpt-4o", description="LLM model name")
    EMBEDDING_MODEL: str = Field(
        default="text-embedding-3-small", description="Embedding model name"
    )

    # ── Redis ─────────────────────────────────────────────────────────────
    REDIS_URL: str = Field(
        default="redis://localhost:6379", description="Redis connection URL"
    )

    # ── ChromaDB ──────────────────────────────────────────────────────────
    CHROMA_HOST: str = Field(default="localhost", description="ChromaDB host")
    CHROMA_PORT: int = Field(default=8000, description="ChromaDB port")
    CHROMA_COLLECTION: str = Field(
        default="nexus_engineering_kb", description="ChromaDB collection name"
    )

    # ── LangFuse ──────────────────────────────────────────────────────────
    LANGFUSE_PUBLIC_KEY: Optional[str] = Field(default=None)
    LANGFUSE_SECRET_KEY: Optional[str] = Field(default=None)
    LANGFUSE_HOST: str = Field(default="https://cloud.langfuse.com")

    # ── OpenTelemetry ─────────────────────────────────────────────────────
    OTEL_ENABLED: bool = Field(default=False, description="Enable OpenTelemetry tracing")
    OTEL_EXPORTER_OTLP_ENDPOINT: str = Field(default="http://localhost:4317")

    # ── Application ───────────────────────────────────────────────────────
    APP_ENV: str = Field(default="development", description="Application environment")
    APP_NAME: str = Field(default="NEXUS Agentic Engineering Intelligence Platform")
    APP_VERSION: str = Field(default="1.0.0")
    DEBUG: bool = Field(default=False)

    # ── Simulation ────────────────────────────────────────────────────────
    MAX_SIMULATION_TIMEOUT: int = Field(
        default=30, description="Maximum simulation timeout in seconds"
    )

    # ── Agent ─────────────────────────────────────────────────────────────
    CONFIDENCE_THRESHOLD: float = Field(
        default=0.75, description="Minimum agent confidence score to proceed"
    )
    MAX_AGENT_RETRIES: int = Field(default=2, description="Maximum agent retry attempts")

    # ── CORS ──────────────────────────────────────────────────────────────
    CORS_ORIGINS: list[str] = Field(
        default=["http://localhost:3002", "http://localhost:3000"]
    )


# Singleton settings instance
settings = Settings()


def get_settings() -> Settings:
    return settings


# Lowercase property aliases used by routers and main.py
Settings.openai_api_key = property(lambda self: self.OPENAI_API_KEY)
Settings.redis_url = property(lambda self: self.REDIS_URL)
Settings.chroma_host = property(lambda self: self.CHROMA_HOST)
Settings.chroma_port = property(lambda self: self.CHROMA_PORT)
Settings.environment = property(lambda self: self.APP_ENV)
Settings.cors_origins = property(lambda self: self.CORS_ORIGINS)
Settings.app_version = property(lambda self: self.APP_VERSION)
Settings.app_name = property(lambda self: self.APP_NAME)
Settings.otlp_endpoint = property(lambda self: self.OTEL_EXPORTER_OTLP_ENDPOINT)
