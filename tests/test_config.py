"""Tests for backend/config.py - centralized configuration."""

import pytest


class TestSettings:
    """Tests for the Settings configuration class."""

    def test_default_values_applied(self):
        """Test that default values are used when env vars not set."""
        from pydantic import Field
        from pydantic_settings import BaseSettings

        class TestableSettings(BaseSettings):
            """Test version of Settings without env_file."""

            model_config = {"env_file": None}
            ebird_api_key: str
            log_level: str = Field(default="INFO")
            ebird_timeout: float = Field(default=15.0)
            nominatim_timeout: float = Field(default=10.0)

        settings = TestableSettings(ebird_api_key="test_key")

        assert settings.ebird_api_key == "test_key"
        assert settings.log_level == "INFO"
        assert settings.ebird_timeout == 15.0
        assert settings.nominatim_timeout == 10.0

    def test_custom_values_override_defaults(self):
        """Test that custom values override defaults."""
        from pydantic import Field
        from pydantic_settings import BaseSettings

        class TestableSettings(BaseSettings):
            model_config = {"env_file": None}
            ebird_api_key: str
            log_level: str = Field(default="INFO")
            ebird_timeout: float = Field(default=15.0)

        settings = TestableSettings(
            ebird_api_key="custom_key",
            log_level="DEBUG",
            ebird_timeout=30.0,
        )

        assert settings.ebird_api_key == "custom_key"
        assert settings.log_level == "DEBUG"
        assert settings.ebird_timeout == 30.0

    def test_missing_required_field_raises_error(self):
        """Test that missing required field raises ValidationError."""
        from pydantic import BaseModel, ValidationError

        class TestableModel(BaseModel):
            """Test model without settings behavior."""

            ebird_api_key: str

        with pytest.raises(ValidationError, match="ebird_api_key"):
            TestableModel()

    def test_actual_settings_loads_from_env(self):
        """Test that the actual Settings class loads correctly."""
        from backend.config import settings

        assert settings.ebird_api_key is not None
        assert len(settings.ebird_api_key) > 0
