"""
Configuration management for GEXA using Pydantic Settings.
"""

from functools import lru_cache
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Database
    database_url: str = Field(
        default="postgresql://postgres:9311@localhost:5432/gexa",
        description="PostgreSQL connection URL",
    )
    database_async_url: str = Field(
        default="postgresql+asyncpg://postgres:9311@localhost:5432/gexa",
        description="Async PostgreSQL connection URL",
    )

    # Gemini API
    gemini_api_key: str = Field(
        default="",
        description="Google Gemini API key",
    )

    # Redis
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection URL",
    )

    # API Settings
    api_host: str = Field(default="0.0.0.0", description="API host")
    api_port: int = Field(default=8000, description="API port")
    api_debug: bool = Field(default=True, description="Debug mode")

    # Security
    secret_key: str = Field(
        default="gexa-dev-secret-key-2024",
        description="Secret key for JWT signing",
    )
    api_key_salt: str = Field(
        default="gexa-api-key-salt",
        description="Salt for API key hashing",
    )

    # Crawler Settings
    crawler_max_concurrent: int = Field(
        default=5,
        description="Maximum concurrent crawl requests",
    )
    crawler_timeout: int = Field(
        default=30,
        description="Crawler timeout in seconds",
    )
    crawler_user_agent: str = Field(
        default="GexaBot/1.0 (+https://gexa.ai)",
        description="User agent for crawler",
    )

    # Embedding Settings
    embedding_model: str = Field(
        default="models/text-embedding-004",
        description="Gemini embedding model",
    )
    embedding_dimension: int = Field(
        default=768,
        description="Embedding vector dimension",
    )
    chunk_size: int = Field(
        default=1000,
        description="Text chunk size for embeddings",
    )
    chunk_overlap: int = Field(
        default=200,
        description="Overlap between chunks",
    )
    
    # LLM Model
    llm_model: str = Field(
        default="gemini-2.5-flash",
        description="Gemini model for answer generation",
    )


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# Global settings instance
settings = get_settings()
