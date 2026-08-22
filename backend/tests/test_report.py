"""The report generator port, its deterministic stub, and the factory.

Two properties matter more than the prose the report contains:

1. **Grounding.** The generator receives measured facts and nothing else. It may
   not claim a signal that was not measured — an unreachable site must not
   produce confident statements about that site.
2. **Substitutability.** The stub and a future Genkit implementation sit behind
   the same Protocol, selected by one environment variable, so enabling a real
   model is a configuration change and not a refactor.
"""

import asyncio

import pytest

from app.services.report import (
    DiagnosisAxis,
    ReportFacts,
    ServiceOffering,
    SiteSignals,
    TemplateReportGenerator,
    UnusableReportGenerator,
    WorkflowAnswers,
    build_report_generator,
)

MEASURED_SITE = SiteSignals(
    available=True,
    url="https://acme.example",
    https=True,
    security_headers=["strict-transport-security"],
    missing_security_headers=["content-security-policy"],
    title="ACME — logistics software",
    description=None,
    canonical="https://acme.example/",
    robots_txt=True,
    sitemap=False,
    framework="Next.js",
    page_weight_bytes=1_800_000,
    resource_count=84,
)

UNAVAILABLE_SITE = SiteSignals(available=False, url="https://unreachable.example")


def generate(generator: object, report_facts: ReportFacts) -> object:
    """Drive the async port from a sync test without pulling in an asyncio plugin.

    The port is async because the implementation that matters later — a model
    call — is network I/O; the stub simply returns immediately.
    """
    return asyncio.run(generator.generate(report_facts))  # type: ignore[attr-defined]


def facts(**overrides: object) -> ReportFacts:
    """A complete set of facts; individual fields overridable per test."""
    base: dict[str, object] = {
        "contact_name": "Ada Lovelace",
        "company": "ACME Logistics",
        "locale": "es",
        "workflow": WorkflowAnswers(
            team_size="6-15",
            practices=["code_review", "ci_pipeline"],
            notes="Deploys are manual and happen on Fridays.",
        ),
        "site": MEASURED_SITE,
    }
    base.update(overrides)
    return ReportFacts(**base)  # type: ignore[arg-type]


class TestDeterminism:
    def test_same_facts_produce_an_identical_report(self) -> None:
        generator = TemplateReportGenerator()

        first = generate(generator, facts())
        second = generate(generator, facts())

        assert first == second

    def test_the_report_carries_no_timestamp_of_its_own(self) -> None:
        # A timestamp inside the report would break determinism; it belongs to
        # the delivery layer, which stamps the email.
        dumped = generate(TemplateReportGenerator(), facts()).model_dump_json()

        assert "generated_at" not in dumped

    def test_different_facts_produce_a_different_report(self) -> None:
        generator = TemplateReportGenerator()
        with_gaps = generate(generator, facts(workflow=WorkflowAnswers(practices=[])))
        with_practices = generate(generator, facts())

        assert with_gaps != with_practices


class TestAxisCoverage:
    def test_every_diagnosis_axis_is_present(self) -> None:
        report = generate(TemplateReportGenerator(), facts())

        assert {section.axis for section in report.sections} == set(DiagnosisAxis)

    def test_the_axes_the_user_asked_for_are_covered(self) -> None:
        # Continuous AI-assisted development, AI bug management, automated
        # deploys, dependency security (Snyk-style) and observability.
        assert {
            DiagnosisAxis.AI_DEVELOPMENT,
            DiagnosisAxis.AI_QUALITY,
            DiagnosisAxis.DELIVERY_AUTOMATION,
            DiagnosisAxis.SECURITY_DEPENDENCIES,
            DiagnosisAxis.OBSERVABILITY,
        } == set(DiagnosisAxis)

    def test_each_section_states_a_diagnosis(self) -> None:
        for section in generate(TemplateReportGenerator(), facts()).sections:
            assert section.diagnosis.strip()


class TestServiceMapping:
    def test_every_recommendation_names_one_of_the_four_services(self) -> None:
        report = generate(TemplateReportGenerator(), facts())

        assert report.recommendations
        for recommendation in report.recommendations:
            assert recommendation.service in set(ServiceOffering)

    def test_all_four_services_are_reachable_from_the_axes(self) -> None:
        # A report that never mentions a service means that service can never be
        # sold from this funnel.
        report = generate(TemplateReportGenerator(), facts(workflow=WorkflowAnswers(practices=[])))

        assert {r.service for r in report.recommendations} == set(ServiceOffering)

    def test_recommendations_are_ordered_by_priority(self) -> None:
        report = generate(TemplateReportGenerator(), facts(workflow=WorkflowAnswers(practices=[])))
        ranks = [r.priority.rank for r in report.recommendations]

        assert ranks == sorted(ranks)

    def test_a_reported_practice_lowers_its_priority(self) -> None:
        generator = TemplateReportGenerator()
        without = generate(generator, facts(workflow=WorkflowAnswers(practices=[])))
        with_ci = generate(generator, facts(workflow=WorkflowAnswers(practices=["ci_pipeline"])))

        def priority_for(report: object, axis: DiagnosisAxis) -> int:
            return next(
                r.priority.rank
                for r in report.recommendations  # type: ignore[attr-defined]
                if r.axis is axis
            )

        assert priority_for(with_ci, DiagnosisAxis.DELIVERY_AUTOMATION) > priority_for(
            without, DiagnosisAxis.DELIVERY_AUTOMATION
        )


class TestGrounding:
    def test_measured_signals_appear_as_evidence(self) -> None:
        report = generate(TemplateReportGenerator(), facts())
        evidence = " ".join(item for section in report.sections for item in section.evidence)

        assert "content-security-policy" in evidence
        assert "Next.js" in evidence

    def test_an_unavailable_site_is_never_described(self) -> None:
        report = generate(TemplateReportGenerator(), facts(site=UNAVAILABLE_SITE))
        body = report.model_dump_json()

        # Nothing may be asserted about a site that was never read.
        for invented in ["Next.js", "content-security-policy", "strict-transport-security"]:
            assert invented not in body

    def test_an_unavailable_site_is_reported_as_unavailable(self) -> None:
        report = generate(TemplateReportGenerator(), facts(site=UNAVAILABLE_SITE))
        evidence = " ".join(item for section in report.sections for item in section.evidence)

        assert "not analysed" in evidence.lower() or "no analizada" in evidence.lower()

    def test_absent_signals_are_not_guessed(self) -> None:
        # sitemap=False must read as absent, never be upgraded to present.
        report = generate(TemplateReportGenerator(), facts())
        evidence = " ".join(item for section in report.sections for item in section.evidence)

        assert "sitemap: absent" in evidence.lower()

    def test_the_visitor_notes_are_quoted_not_paraphrased(self) -> None:
        report = generate(TemplateReportGenerator(), facts())

        assert "Deploys are manual and happen on Fridays." in report.model_dump_json()


class TestPiiBoundary:
    def test_facts_have_no_field_for_an_email_address(self) -> None:
        # The generator never needs the address, so the model cannot carry it:
        # the delivery layer holds it instead. This is what keeps a future model
        # call free of the one piece of PII we must not hand to a third party.
        assert "email" not in ReportFacts.model_fields

    def test_facts_have_no_free_text_prompt_field(self) -> None:
        # Prompt injection surface is bounded by shape: the client cannot supply
        # instructions, only answers that the generator quotes.
        assert "prompt" not in ReportFacts.model_fields
        assert "instructions" not in ReportFacts.model_fields


class TestFactory:
    def test_stub_is_the_default(self) -> None:
        assert isinstance(build_report_generator(""), TemplateReportGenerator)
        assert isinstance(build_report_generator("stub"), TemplateReportGenerator)

    def test_selection_is_case_and_space_insensitive(self) -> None:
        assert isinstance(build_report_generator("  STUB "), TemplateReportGenerator)

    def test_an_unknown_generator_fails_loudly(self) -> None:
        with pytest.raises(UnusableReportGenerator, match="banana"):
            build_report_generator("banana")

    def test_genkit_without_a_key_names_the_missing_variable(self) -> None:
        with pytest.raises(UnusableReportGenerator, match="GEMINI_API_KEY"):
            build_report_generator("genkit", model_api_key="")

    def test_genkit_with_a_key_is_still_unavailable_but_says_why(self) -> None:
        # Phase F lands the dependency; until then the error must be explicit
        # rather than silently falling back to the stub, which would ship a
        # template report while the operator believes a model wrote it.
        with pytest.raises(UnusableReportGenerator, match="not installed|Phase F|unavailable"):
            build_report_generator("genkit", model_api_key="AIza-test-key")
