"""Centralized configuration using pydantic-settings."""

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )

    # Required
    ebird_api_key: str = Field(description="eBird API key from ebird.org/api/keygen")

    # Optional with defaults
    log_level: str = Field(default="INFO", description="Logging level")

    # Timeouts
    ebird_timeout: float = Field(default=15.0, description="eBird API timeout in seconds")
    ebird_taxonomy_timeout: float = Field(default=30.0, description="Taxonomy endpoint timeout")
    nominatim_timeout: float = Field(default=10.0, description="Nominatim geocoding timeout")

    # Paths
    cache_file: Path = Field(
        default=Path(__file__).parent.parent / "geocode_cache.json",
        description="Path to geocoding cache file",
    )


settings = Settings()
