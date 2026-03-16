"""Shared configuration for CartSnitch services via pydantic-settings."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Environment-driven settings shared by all CartSnitch services."""

    model_config = SettingsConfigDict(env_prefix="CARTSNITCH_", env_file=".env")

    database_url: str = "postgresql+asyncpg://cartsnitch:cartsnitch@localhost:5432/cartsnitch"
    database_url_sync: str = "postgresql+psycopg2://cartsnitch:cartsnitch@localhost:5432/cartsnitch"
    redis_url: str = "redis://localhost:6379/0"
    debug: bool = False
    log_level: str = "INFO"


settings = Settings()
