"""Application configuration helpers."""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Typed application settings loaded from the environment."""

    database_url: str = Field(alias="DATABASE_URL")
    x_admin_key: str = Field(alias="X_ADMIN_KEY")
    openai_api_key: str = Field(alias="OPENAI_API_KEY")
    summary_model: str = Field(default="gpt-4o-mini", alias="SUMMARY_MODEL")
    cover_image_model: str = Field(default="gpt-image-1", alias="COVER_IMAGE_MODEL")
    group_capacity: int = Field(default=8, alias="GROUP_CAPACITY")
    summary_check_interval_seconds: int = Field(
        default=300,
        alias="SUMMARY_CHECK_INTERVAL_SECONDS",
    )
    blob_read_write_token: str | None = Field(default=None, alias="BLOB_READ_WRITE_TOKEN")

    model_config = SettingsConfigDict(
        env_file=(".env", "../../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached settings for the running process."""
    return Settings()  # ty: ignore[missing-argument]
