"""Settings for report generation and delivery.

Deliberately separate from `Settings` so this phase could be built and reviewed
without touching the file the verification phase is editing. **Merge task:** fold
these fields into `app.core.config.Settings` once both have landed — one settings
object is the convention, two is a smell.

The verification secret accepts either name because the specification and the
implementation chose different ones; whichever is set in the environment wins.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic import AliasChoices, Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class ReportDeliveryUnavailable(Exception):
    """The flow is not configured: a missing key or address, not a bad request.

    Surfaces as 503 so an operator reading the response knows it is their
    configuration, not the caller's payload.
    """


class ReportDeliverySettings(BaseSettings):
    report_generator: str = "stub"
    gemini_api_key: SecretStr = SecretStr("")
    resend_api_key: SecretStr = SecretStr("")
    contact_from_email: str = ""
    contact_to_email: str = ""
    verification_secret: SecretStr = Field(
        default=SecretStr(""),
        validation_alias=AliasChoices(
            "CONTACT_TOKEN_SECRET",
            "EMAIL_VERIFICATION_SECRET",
        ),
    )

    # populate_by_name: the aliased field is also settable by its own name,
    # which tests and the future merge into Settings both rely on.
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", populate_by_name=True)

    def require_mail_configuration(self) -> tuple[str, str, str]:
        """Return (api_key, sender, owner) or refuse to build a mailer."""
        api_key = self.resend_api_key.get_secret_value()

        missing = [
            name
            for name, value in (
                ("RESEND_API_KEY", api_key),
                ("CONTACT_FROM_EMAIL", self.contact_from_email),
                ("CONTACT_TO_EMAIL", self.contact_to_email),
            )
            if not value
        ]
        if missing:
            raise ReportDeliveryUnavailable(f"not configured: {', '.join(missing)}")

        return api_key, self.contact_from_email, self.contact_to_email

    def require_verification_secret(self) -> str:
        secret = self.verification_secret.get_secret_value()
        if not secret:
            raise ReportDeliveryUnavailable("not configured: CONTACT_TOKEN_SECRET")
        return secret


@lru_cache
def get_report_delivery_settings() -> ReportDeliverySettings:
    """Cached singleton; tests clear it or override the dependency."""
    return ReportDeliverySettings()
