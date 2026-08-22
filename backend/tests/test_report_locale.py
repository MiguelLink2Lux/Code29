"""The template report must speak the visitor's language.

The chat is Spanish-first and asks in Spanish, so emailing an English report is
a defect the visitor sees before we do. The Gemini connector honours `locale`
through its system instruction; the template generator has to do it too.
"""

import asyncio

import pytest

from app.services.report import (
    DiagnosisAxis,
    ReportFacts,
    SiteSignals,
    TemplateReportGenerator,
    WorkflowAnswers,
)
from app.services.report_copy import AXIS_COPY, PRACTICE_LABELS, SUPPORTED_LOCALES


def facts(locale: str, practices: list[str] | None = None) -> ReportFacts:
    return ReportFacts(
        contact_name="Ada",
        company="Analytical Engines",
        locale=locale,
        workflow=WorkflowAnswers(practices=practices or []),
        site=SiteSignals(available=True, https=True, url="https://example.com"),
    )


def generate(locale: str, practices: list[str] | None = None):
    return asyncio.run(TemplateReportGenerator().generate(facts(locale, practices)))


class TestSpanish:
    def test_writes_the_report_in_spanish(self) -> None:
        report = generate("es")

        assert "Diagnóstico" in report.title
        # A Spanish visitor must not receive English prose.
        assert "assessment of" not in report.summary
        assert "based on the answers" not in report.summary

    def test_translates_the_section_headings(self) -> None:
        report = generate("es")
        headings = " ".join(section.heading for section in report.sections)

        assert "Desarrollo" in headings or "desarrollo" in headings
        assert "Observabilidad" in headings

    def test_translates_the_evidence_labels(self) -> None:
        report = generate("es", practices=["automated_tests"])
        evidence = " ".join(item for section in report.sections for item in section.evidence)

        assert "En uso" in evidence or "en uso" in evidence
        assert "Reported in place" not in evidence

    def test_translates_the_recommendations(self) -> None:
        report = generate("es")
        actions = " ".join(r.action for r in report.recommendations)

        assert "Introduce an AI-first" not in actions


class TestEnglish:
    def test_still_writes_english_when_asked(self) -> None:
        report = generate("en")

        assert "assessment" in report.summary.lower()
        assert "Diagnóstico" not in report.title


class TestParity:
    def test_both_locales_cover_every_axis(self) -> None:
        for locale in SUPPORTED_LOCALES:
            assert set(AXIS_COPY[locale]) == set(DiagnosisAxis), f"{locale} is missing an axis"

    def test_both_locales_cover_every_practice_label(self) -> None:
        english = set(PRACTICE_LABELS["en"])
        for locale in SUPPORTED_LOCALES:
            assert set(PRACTICE_LABELS[locale]) == english, f"{locale} labels diverge"

    def test_every_axis_has_all_five_texts_in_both_locales(self) -> None:
        for locale in SUPPORTED_LOCALES:
            for axis, copy in AXIS_COPY[locale].items():
                for field in (
                    "heading",
                    "gap_action",
                    "gap_rationale",
                    "strength_action",
                    "strength_rationale",
                ):
                    assert copy[field].strip(), f"{locale}/{axis}/{field} is empty"

    @pytest.mark.parametrize("locale", ["fr", "", "klingon", None])
    def test_an_unknown_locale_resolves_to_the_fallback(self, locale: str | None) -> None:
        # ReportFacts pins locale to a Literal, so these never reach the
        # generator; the resolver is still the guard if that ever loosens.
        from app.services.report_copy import FALLBACK_LOCALE, resolve_locale

        assert resolve_locale(locale) == FALLBACK_LOCALE
