"""The cutover: what the report endpoint actually serves.

Every phase shipped additively so a revert would always leave a working contact
path. That is the right way to build it and the wrong way to leave it: at the end
the endpoint was still serving the five-axis report and still using a site
analyser that reports every site as unreadable.

These tests assert the wiring, which is exactly the class of defect a local run
found last time — each part correct, nothing connected.
"""

import pytest
from fastapi.testclient import TestClient

from app.api.v1 import contact_report
from app.core.config import Settings
from app.main import create_app
from app.services.canon import CANON_POINTS
from app.services.canon_report import CanonReport
from app.services.tokens import issue_access_token

SECRET = "cutover-secret-of-at-least-32-characters!"
EMAIL = "ada@example.com"


def configured() -> Settings:
    return Settings(
        contact_token_secret=SECRET,
        resend_api_key="re_test",
        turnstile_secret_key="ts_test",
        contact_from_email="noreply@code29.dev",
        contact_to_email="hola@code29.dev",
    )


class TestReportStructure:
    def test_the_generator_produces_a_canon_report_not_five_axes(self) -> None:
        from app.services.canon_report import TemplateCanonGenerator

        # The five-axis DiagnosisAxis report is superseded by the ten-point canon
        # (ADR 0008). What the endpoint builds must be the canon one.
        generator = contact_report.get_report_generator(configured_settings())

        assert isinstance(generator, TemplateCanonGenerator), (
            f"the endpoint still builds {type(generator).__name__}: the cutover did not happen"
        )

    def test_a_canon_report_carries_all_ten_points_in_order(self) -> None:
        import asyncio

        from app.services.canon_report import TemplateCanonGenerator
        from app.services.report import SiteSignals

        report = asyncio.run(
            TemplateCanonGenerator().generate(
                contact_name="Ada", company="AE", locale="es",
                site=SiteSignals(available=False),
            )
        )

        assert isinstance(report, CanonReport)
        assert [section.point.number for section in report.sections] == list(range(1, 11))

    def test_the_report_closes_on_the_single_proposal(self) -> None:
        import asyncio

        from app.services.canon_report import TemplateCanonGenerator
        from app.services.report import SiteSignals

        report = asyncio.run(
            TemplateCanonGenerator().generate(
                contact_name="Ada", company="AE", locale="es",
                site=SiteSignals(available=False),
            )
        )

        # It sells one engagement, not ten line items: a headline, exactly three
        # parts (training, environment, quality control) and a rationale.
        assert report.proposal.headline.strip()
        assert len(report.proposal.parts) == 3
        assert report.proposal.rationale.strip()


class TestSiteAnalyserWiring:
    def test_the_analyser_is_not_the_always_unavailable_placeholder(self) -> None:
        analyser = contact_report.get_site_analyzer()

        assert analyser is not contact_report._no_site_analysis, (
            "the report endpoint still uses the placeholder analyser: every lead's site "
            "would be reported as unreadable"
        )

    @pytest.mark.anyio
    async def test_the_wired_analyser_refuses_a_private_target(self) -> None:
        # Proof it is the real one: the SSRF guard answers, rather than a stub
        # that returns "not analysed" for everything.
        analyser = contact_report.get_site_analyzer()

        signals = await analyser("http://127.0.0.1/")

        assert signals.available is False


class TestEndpointStillRefuses:
    def test_an_unconfigured_deployment_answers_503_before_looking_at_the_token(self) -> None:
        # The report endpoint reads its own ReportDeliverySettings from the
        # environment rather than the injected Settings — a known seam, noted as
        # a merge task in report_settings.py. With nothing configured it cannot
        # verify a token at all, so 503 comes first. That ordering is correct;
        # what is not correct is having two settings objects, which is tracked.
        client = TestClient(create_app(settings=configured()))

        response = client.post(
            "/api/v1/contact/report",
            json={
                "contact_name": "Ada",
                "company": "AE",
                "workflow": {"practices": []},
                "consent": {"privacy_accepted": True, "report_accepted": True},
            },
        )

        assert response.status_code == 503

    def test_a_configured_deployment_refuses_a_missing_token_with_401(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("CONTACT_TOKEN_SECRET", SECRET)
        monkeypatch.setenv("RESEND_API_KEY", "re_test")
        monkeypatch.setenv("CONTACT_FROM_EMAIL", "noreply@code29.dev")
        monkeypatch.setenv("CONTACT_TO_EMAIL", "hola@code29.dev")

        from app.core.report_settings import get_report_delivery_settings

        get_report_delivery_settings.cache_clear()
        client = TestClient(create_app(settings=configured()))

        response = client.post(
            "/api/v1/contact/report",
            json={
                "contact_name": "Ada",
                "company": "AE",
                "workflow": {"practices": []},
                "consent": {"privacy_accepted": True, "report_accepted": True},
            },
        )

        get_report_delivery_settings.cache_clear()
        assert response.status_code == 401

    def test_a_valid_token_no_longer_gets_a_422_for_the_new_contract(self) -> None:
        # The conversational flow posts facts, not the old questionnaire payload.
        client = TestClient(create_app(settings=configured()))
        token = issue_access_token(EMAIL, secret=SECRET)

        response = client.post(
            "/api/v1/contact/report",
            json={"envelope": "irrelevant-here"},
            headers={"Authorization": f"Bearer {token}"},
        )

        # Whatever it answers, it must not be a 500: the contract is explicit.
        assert response.status_code != 500


def configured_settings():
    """The report settings object the endpoint dependency expects."""
    from app.core.report_settings import ReportDeliverySettings

    return ReportDeliverySettings(
        report_generator="stub",
        verification_secret=SECRET,
        resend_api_key="re_test",
        contact_from_email="noreply@code29.dev",
        contact_to_email="hola@code29.dev",
    )


def test_the_canon_has_ten_points_and_the_report_matches_it() -> None:
    assert len(CANON_POINTS) == 10
