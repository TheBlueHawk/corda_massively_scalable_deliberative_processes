"""Application configuration helpers."""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Typed application settings loaded from the environment."""

    database_url: str = Field(alias="DATABASE_URL")
    telegram_bot_token: str = Field(alias="TELEGRAM_BOT_TOKEN")
    telegram_supergroup_id: int = Field(alias="TELEGRAM_SUPERGROUP_ID")
    anthropic_api_key: str = Field(alias="ANTHROPIC_API_KEY")
    x_admin_key: str = Field(alias="X_ADMIN_KEY")
    telegram_bot_username: str = Field(alias="TELEGRAM_BOT_USERNAME")
    summary_model: str = Field(default="claude-3-5-haiku-latest", alias="SUMMARY_MODEL")
    group_capacity: int = Field(default=8, alias="GROUP_CAPACITY")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached settings for the running process."""
    return Settings()  # ty: ignore[missing-argument]
