"""Application settings loaded from the environment via pydantic-settings."""

from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Environment-driven configuration.

    `cors_origins` defaults to the local Astro dev server and is never `*`.
    """

    app_env: str = "development"
    cors_origins: list[str] = ["http://localhost:4321"]

    # enable_decoding=False stops pydantic-settings from JSON-decoding complex
    # fields (list[str]) at the source level, so CORS_ORIGINS reaches the
    # validator below as a raw comma-separated string instead of crashing.
    model_config = SettingsConfigDict(
        env_file=".env", extra="ignore", enable_decoding=False
    )

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_cors_origins(cls, value: object) -> object:
        # pydantic-settings would otherwise try to JSON-decode a plain
        # comma-separated env string and fail. Accept "a,b" and lists alike.
        if isinstance(value, str):
            origins = [origin.strip() for origin in value.split(",") if origin.strip()]
        else:
            origins = value

        # Fail fast on boot instead of deploying an open CORS policy: credentials
        # aside, `*` would let any site call the API from a visitor's browser.
        if isinstance(origins, list) and "*" in origins:
            raise ValueError("CORS_ORIGINS must list explicit origins; wildcard `*` is not allowed")

        return origins


@lru_cache
def get_settings() -> Settings:
    """Cached settings singleton (DIP injection point; tests use cache_clear())."""
    return Settings()
