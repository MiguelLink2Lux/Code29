"""Application settings loaded from the environment via pydantic-settings."""

from functools import lru_cache

from pydantic import SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

MIN_SECRET_LENGTH = 32


class Settings(BaseSettings):
    """Environment-driven configuration.

    `cors_origins` defaults to the local Astro dev server and is never `*`.

    The contact-flow settings are optional so local work needs no ceremony:
    when any of them is missing, `contact_flow_enabled` is False and the
    endpoints answer 503 instead of half-working. In production a weak or
    absent signing secret is a hard boot failure — it protects the tokens that
    authorise sending email and fetching third-party sites.
    """

    app_env: str = "development"
    cors_origins: list[str] = ["http://localhost:4321"]

    # Secrets use SecretStr so a settings object reaching a log does not carry
    # them along. Read them with .get_secret_value() at the point of use.
    contact_token_secret: SecretStr = SecretStr("")
    resend_api_key: SecretStr = SecretStr("")
    turnstile_secret_key: SecretStr = SecretStr("")
    contact_from_email: str = ""
    contact_to_email: str = ""

    @property
    def is_production(self) -> bool:
        return self.app_env.strip().lower() in {"production", "prod"}

    @property
    def contact_flow_enabled(self) -> bool:
        """True only when every dependency the guided contact flow needs is set."""
        return all(
            [
                self.contact_token_secret.get_secret_value(),
                self.resend_api_key.get_secret_value(),
                self.turnstile_secret_key.get_secret_value(),
                self.contact_from_email,
                self.contact_to_email,
            ]
        )

    @property
    def _contact_flow_intended(self) -> bool:
        """True when any contact-flow variable is set, i.e. someone meant to enable it."""
        return any(
            [
                self.contact_token_secret.get_secret_value(),
                self.resend_api_key.get_secret_value(),
                self.turnstile_secret_key.get_secret_value(),
                self.contact_from_email,
                self.contact_to_email,
            ]
        )

    @model_validator(mode="after")
    def _require_strong_secret_in_production(self) -> "Settings":
        # A weak secret is always a hard failure: it would authorise outbound
        # email and third-party fetches with a guessable signature.
        secret = self.contact_token_secret.get_secret_value()

        if secret and self.is_production and len(secret) < MIN_SECRET_LENGTH:
            raise ValueError(
                f"CONTACT_TOKEN_SECRET must be at least {MIN_SECRET_LENGTH} characters long"
            )

        # An absent secret only fails when the flow was clearly meant to run.
        # Otherwise a health-only production deploy — which is what ships today —
        # would refuse to boot over a feature it does not serve.
        if self.is_production and self._contact_flow_intended and not secret:
            raise ValueError("CONTACT_TOKEN_SECRET is required when the contact flow is configured")

        return self

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
