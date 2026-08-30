"""Contact settings fail fast rather than deploying a broken or insecure flow.

A missing Resend key or a weak signing secret must surface on boot — in the
deploy log — not on the first visitor who tries to verify an address.
"""

import pytest

from app.core.config import Settings
from app.services.turnstile import TEST_SECRET_KEY as TURNSTILE_TEST_SECRET_KEY

STRONG_SECRET = "a" * 32


def configured(**overrides: object) -> Settings:
    """A fully configured flow, so a test only has to state what it is about."""
    defaults: dict[str, object] = {
        "app_env": "production",
        "contact_token_secret": STRONG_SECRET,
        "resend_api_key": "re_test",
        "turnstile_secret_key": "0x4realsecret",
        "contact_from_email": "noreply@code29.dev",
        "contact_to_email": "hola@code29.dev",
    }

    return Settings(**{**defaults, **overrides})  # type: ignore[arg-type]


class TestSigningSecret:
    def test_absent_secret_is_allowed_in_development(self) -> None:
        # Local work must not require ceremony; the flow degrades instead.
        settings = Settings(app_env="development", contact_token_secret="")
        assert settings.contact_flow_enabled is False

    def test_production_disables_the_flow_when_the_secret_is_absent(self) -> None:
        # This used to assert a raise. Raising happens during the import of
        # app.main, so it did not refuse a feature — it stopped the service from
        # starting, /health included, with no HTTP answer naming the variable.
        settings = Settings(app_env="production", contact_token_secret="", resend_api_key="re_test")

        assert settings.contact_flow_enabled is False
        assert "CONTACT_TOKEN_SECRET" in (settings.contact_flow_disabled_reason or "")

    def test_production_boots_without_the_flow_configured(self) -> None:
        # A health-only deploy — what ships today — must not refuse to boot over
        # a feature it does not serve.
        settings = Settings(app_env="production", contact_token_secret="")
        assert settings.contact_flow_enabled is False

    def test_production_disables_the_flow_on_a_short_secret(self) -> None:
        # A weak secret must never sign anything — that part is unchanged. What
        # changed is how: the flow is disabled and every endpoint refuses with
        # 503 before reaching a signing path, instead of the process refusing to
        # start. See test_startup_resilience.py for the assertion that no route
        # issues a token in this state.
        settings = configured(contact_token_secret="too-short")

        assert settings.contact_flow_enabled is False
        assert "32" in (settings.contact_flow_disabled_reason or "")

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


class TestTurnstileTestSecret:
    """Cloudflare's test secret approves every token, so in production it is an
    open gate wearing the clothes of a configured one. COD-49: it was live."""

    def _values(self, **overrides: object) -> dict[str, object]:
        values: dict[str, object] = {
            "contact_token_secret": STRONG_SECRET,
            "resend_api_key": "re_test",
            "contact_from_email": "noreply@code29.dev",
            "contact_to_email": "hola@code29.dev",
            "turnstile_secret_key": TURNSTILE_TEST_SECRET_KEY,
        }
        values.update(overrides)
        return values

    def test_production_does_not_count_the_test_secret_as_configuration(self) -> None:
        settings = Settings(app_env="production", **self._values())

        assert settings.contact_flow_enabled is False
        assert "test secret" in (settings.contact_flow_disabled_reason or "")

    def test_the_reason_names_the_variable_at_fault(self) -> None:
        settings = Settings(app_env="production", **self._values())

        # An operator reading the 503 must learn which variable to change.
        assert "TURNSTILE_SECRET_KEY" in (settings.contact_flow_disabled_reason or "")

    def test_previews_and_local_work_keep_the_test_secret(self) -> None:
        # Preview deployments live on *.vercel.app, a hostname no real widget can
        # claim, so there the test pair is the only thing that works.
        settings = Settings(app_env="development", **self._values())

        assert settings.contact_flow_enabled is True
        assert settings.contact_flow_disabled_reason is None

    def test_a_real_secret_enables_the_flow_in_production(self) -> None:
        settings = Settings(app_env="production", **self._values(turnstile_secret_key="0x_real"))

        assert settings.contact_flow_enabled is True
        assert settings.contact_flow_disabled_reason is None

    def test_a_missing_variable_is_still_reported_by_name(self) -> None:
        settings = Settings(**self._values(resend_api_key=""))

        assert "RESEND_API_KEY" in (settings.contact_flow_disabled_reason or "")


class TestSecretExposure:
    def test_secrets_are_not_exposed_by_the_string_representation(self) -> None:
        # A settings object reaching a log must not carry the API key with it.
        settings = Settings(contact_token_secret=STRONG_SECRET, resend_api_key="re_supersecret")
        assert "re_supersecret" not in str(settings)
        assert STRONG_SECRET not in str(settings)


class TestSenderDomain:
    """A sender on a public mailbox domain cannot deliver, and the code knows it.

    Resend — like every transactional provider — only sends from a domain the
    account has verified, and nobody verifies gmail.com. So a sender there is
    not a risky configuration, it is one that fails every single time.

    The check that existed asked whether CONTACT_FROM_EMAIL was non-empty.
    `someone@gmail.com` is non-empty, so by every measure the system had, the
    flow was configured. It failed only when a real visitor handed over their
    address — the exact moment the lead is lost — with a 502 that reads like a
    transport blip.

    Same lesson as the Turnstile test secret, written down once already: a value
    that cannot work must be recognisable to the code, not only to the person
    who typed it.
    """

    @pytest.mark.parametrize(
        "sender",
        [
            "hola@gmail.com",
            "Hola@GMail.com",
            "code29@hotmail.com",
            "info@outlook.com",
            "contacto@yahoo.es",
            "hey@icloud.com",
            "team@proton.me",
        ],
    )
    def test_a_public_mailbox_sender_disables_the_flow_in_production(self, sender: str) -> None:
        settings = configured(app_env="production", contact_from_email=sender)

        assert settings.contact_flow_enabled is False
        assert "CONTACT_FROM_EMAIL" in (settings.contact_flow_disabled_reason or "")

    def test_a_domain_of_your_own_is_fine(self) -> None:
        settings = configured(app_env="production", contact_from_email="noreply@code29.dev")

        assert settings.contact_flow_enabled is True

    def test_a_display_name_around_the_address_is_still_read(self) -> None:
        # Resend accepts "CODE29 <noreply@code29.dev>", so the check has to see
        # through that form as well.
        blocked = configured(app_env="production", contact_from_email="CODE29 <hola@gmail.com>")
        allowed = configured(app_env="production", contact_from_email="CODE29 <n@code29.dev>")

        assert blocked.contact_flow_enabled is False
        assert allowed.contact_flow_enabled is True

    def test_local_development_is_left_alone(self) -> None:
        # A personal address is how you try the flow on your own machine.
        settings = configured(app_env="development", contact_from_email="hola@gmail.com")

        assert settings.contact_flow_enabled is True
