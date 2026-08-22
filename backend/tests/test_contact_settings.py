"""Contact settings fail fast rather than deploying a broken or insecure flow.

A missing Resend key or a weak signing secret must surface on boot — in the
deploy log — not on the first visitor who tries to verify an address.
"""

import pytest

from app.core.config import Settings

STRONG_SECRET = "a" * 32


class TestSigningSecret:
    def test_absent_secret_is_allowed_in_development(self) -> None:
        # Local work must not require ceremony; the flow degrades instead.
        settings = Settings(app_env="development", contact_token_secret="")
        assert settings.contact_flow_enabled is False

    def test_production_rejects_an_absent_secret_when_the_flow_is_configured(self) -> None:
        with pytest.raises(ValueError, match="CONTACT_TOKEN_SECRET"):
            Settings(app_env="production", contact_token_secret="", resend_api_key="re_test")

    def test_production_boots_without_the_flow_configured(self) -> None:
        # A health-only deploy — what ships today — must not refuse to boot over
        # a feature it does not serve.
        settings = Settings(app_env="production", contact_token_secret="")
        assert settings.contact_flow_enabled is False

    def test_production_rejects_a_short_secret_even_alone(self) -> None:
        # A weak secret is always fatal: it signs tokens that authorise sending
        # email and fetching third-party sites.
        with pytest.raises(ValueError, match="32"):
            Settings(app_env="production", contact_token_secret="too-short")

    def test_production_accepts_a_strong_secret(self) -> None:
        settings = Settings(app_env="production", contact_token_secret=STRONG_SECRET)
        # Wrapped in SecretStr: reading it is deliberate, never accidental.
        assert settings.contact_token_secret.get_secret_value() == STRONG_SECRET


class TestFlowReadiness:
    def test_flow_is_enabled_only_when_every_dependency_is_configured(self) -> None:
        settings = Settings(
            contact_token_secret=STRONG_SECRET,
            resend_api_key="re_test",
            contact_from_email="noreply@code29.dev",
            contact_to_email="hola@code29.dev",
            turnstile_secret_key="1x0000000000000000000000000000000AA",
        )
        assert settings.contact_flow_enabled is True

    @pytest.mark.parametrize(
        "missing",
        ["resend_api_key", "contact_from_email", "contact_to_email", "turnstile_secret_key"],
    )
    def test_one_missing_dependency_disables_the_flow(self, missing: str) -> None:
        values = {
            "contact_token_secret": STRONG_SECRET,
            "resend_api_key": "re_test",
            "contact_from_email": "noreply@code29.dev",
            "contact_to_email": "hola@code29.dev",
            "turnstile_secret_key": "1x0000000000000000000000000000000AA",
        }
        values[missing] = ""

        assert Settings(**values).contact_flow_enabled is False

    def test_secrets_are_not_exposed_by_the_string_representation(self) -> None:
        # A settings object reaching a log must not carry the API key with it.
        settings = Settings(contact_token_secret=STRONG_SECRET, resend_api_key="re_supersecret")
        assert "re_supersecret" not in str(settings)
        assert STRONG_SECRET not in str(settings)
