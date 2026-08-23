"""The report built on the ten-point canon.

Two structural rules the report must obey, and both are about what the report is
*for*:

- **Ten sections, always, in canon order.** That is what makes one lead's report
  comparable to another's, and it is why the canon is fixed.
- **One closing proposal.** The canon is the instrument that leads to a single
  engagement — team training, environment preparation, quality criteria and
  their control. Ten separate recommendations would turn it into a menu, which
  ADR 0008 rejects.

And one tonal rule with teeth: an uncovered point is framed as a stage of the
flow the client has not built, never as an accusation. "You have no tests" when
nobody asked is the exact sentence this must never produce.
"""

import asyncio

import pytest

from app.services.canon import CANON_POINTS, EvidenceSource, PointState
from app.services.canon_report import (
    CanonReport,
    ClosingProposal,
    TemplateCanonGenerator,
    build_canon_report,
)
from app.services.report import SiteSignals


def facts(**overrides: object) -> dict:
    base: dict = {
        "contact_name": "Ada",
        "company": "Analytical Engines",
        "locale": "es",
        "team": "4 desarrolladores",
        "site": SiteSignals(available=True, https=True, url="https://example.com"),
        "reported": {},
        "cited": {},
    }
    base.update(overrides)
    return base


def build(**overrides: object) -> CanonReport:
    return build_canon_report(**facts(**overrides))  # type: ignore[arg-type]


class TestStructure:
    def test_has_exactly_ten_sections(self) -> None:
        assert len(build().sections) == 10

    def test_sections_follow_canon_order(self) -> None:
        report = build()

        assert [section.point.number for section in report.sections] == list(range(1, 11))

    def test_every_canon_point_appears_once(self) -> None:
        ids = [section.point.id for section in build().sections]

        assert sorted(ids) == sorted(point.id for point in CANON_POINTS)

    def test_the_transversal_points_stay_flagged(self) -> None:
        transversal = [s.point.number for s in build().sections if s.point.transversal]

        assert transversal == [2, 10]

    def test_a_report_cannot_be_built_with_nine_sections(self) -> None:
        report = build()

        with pytest.raises(ValueError, match="ten"):
            CanonReport(
                title=report.title,
                summary=report.summary,
                sections=report.sections[:9],
                proposal=report.proposal,
                generator="test",
            )

    def test_a_report_cannot_reorder_the_canon(self) -> None:
        report = build()
        shuffled = [report.sections[1], report.sections[0], *report.sections[2:]]

        with pytest.raises(ValueError, match="order"):
            CanonReport(
                title=report.title,
                summary=report.summary,
                sections=shuffled,
                proposal=report.proposal,
                generator="test",
            )


class TestSingleProposal:
    def test_closes_on_exactly_one_proposal(self) -> None:
        report = build()

        assert isinstance(report.proposal, ClosingProposal)

    def test_the_proposal_names_the_three_parts_of_the_engagement(self) -> None:
        # Training, environment, quality control: the offering, verbatim.
        proposal = build().proposal

        assert len(proposal.parts) == 3
        joined = " ".join(proposal.parts).lower()
        for pillar in ["formación", "entorno", "calidad"]:
            assert pillar in joined

    def test_the_report_has_no_per_point_recommendation_list(self) -> None:
        # A list of ten recommendations is a menu. The model of the report must
        # not even offer the field.
        assert "recommendations" not in CanonReport.model_fields

    def test_the_proposal_is_the_same_engagement_regardless_of_findings(self) -> None:
        nothing_known = build(site=SiteSignals(available=False), team=None, reported={})
        much_known = build(
            reported={
                point.id: [{"text": "lo hacemos", "source": "reported"}] for point in CANON_POINTS
            }
        )

        assert nothing_known.proposal.parts == much_known.proposal.parts


class TestOpportunityFraming:
    def test_an_unevaluated_point_is_marked_an_opportunity(self) -> None:
        report = build(site=SiteSignals(available=False), reported={})

        unevaluated = [s for s in report.sections if s.state is PointState.NOT_EVALUATED]

        assert unevaluated
        assert all(section.is_opportunity for section in unevaluated)

    def test_an_unevaluated_point_carries_no_diagnosis(self) -> None:
        report = build(site=SiteSignals(available=False), reported={})

        for section in report.sections:
            if section.state is PointState.NOT_EVALUATED:
                assert section.diagnosis == ""

    def test_an_unevaluated_point_is_never_phrased_as_an_absence_of_practice(self) -> None:
        # The forbidden jump from silence to accusation.
        report = build(site=SiteSignals(available=False), reported={})
        forbidden = ["no tenéis", "no teneis", "carecen", "carecéis", "falta de", "no disponen"]

        for section in report.sections:
            if section.state is PointState.NOT_EVALUATED:
                text = (section.narrative + section.diagnosis).lower()
                for phrase in forbidden:
                    assert phrase not in text, f"point {section.point.number}: {text!r}"

    def test_an_unevaluated_section_still_says_something_useful(self) -> None:
        # "Not evaluated" must not render as a blank: it is the part of the flow
        # we get to propose, so the narrative has to carry that.
        report = build(site=SiteSignals(available=False), reported={})

        for section in report.sections:
            if section.state is PointState.NOT_EVALUATED:
                assert section.narrative.strip()

    def test_a_covered_point_is_not_an_opportunity(self) -> None:
        report = build(
            reported={CANON_POINTS[5].id: [{"text": "tests en cada merge", "source": "reported"}]}
        )
        section = next(s for s in report.sections if s.point.number == 6)

        assert section.state is PointState.COVERED
        assert section.is_opportunity is False


class TestEvidenceInSections:
    def test_measured_signals_reach_the_section_that_uses_them(self) -> None:
        report = build(
            site=SiteSignals(
                available=True,
                https=True,
                url="https://example.com",
                missing_security_headers=["Content-Security-Policy"],
            )
        )
        governance = next(s for s in report.sections if s.point.number == 10)

        assert any(item.source is EvidenceSource.MEASURED for item in governance.evidence)

    def test_every_piece_of_evidence_in_the_report_names_its_source(self) -> None:
        report = build(
            reported={CANON_POINTS[0].id: [{"text": "documentamos requisitos",
                                            "source": "reported"}]},
            cited={CANON_POINTS[2].id: [{"text": "usan Linear",
                                         "source": "cited",
                                         "ref": "https://example.com/about"}]},
        )

        for section in report.sections:
            for item in section.evidence:
                assert item.source in EvidenceSource
                if item.source is EvidenceSource.CITED:
                    assert item.ref

    def test_unsourced_model_claims_never_reach_a_section(self) -> None:
        report = build(reported={CANON_POINTS[3].id: [{"text": "seguro que sí"}]})
        section = next(s for s in report.sections if s.point.number == 4)

        assert section.evidence == []
        assert section.state is PointState.NOT_EVALUATED


class TestTemplateGenerator:
    def test_is_deterministic(self) -> None:
        generator = TemplateCanonGenerator()
        first = asyncio.run(generator.generate(**facts()))  # type: ignore[arg-type]
        second = asyncio.run(generator.generate(**facts()))  # type: ignore[arg-type]

        assert first.model_dump_json() == second.model_dump_json()

    def test_declares_itself_as_the_template(self) -> None:
        report = asyncio.run(TemplateCanonGenerator().generate(**facts()))  # type: ignore[arg-type]

        assert "template" in report.generator.lower()

    def test_writes_spanish_for_a_spanish_lead(self) -> None:
        report = build(locale="es")

        assert "Diagnóstico" in report.title or "diagnóstico" in report.summary

    def test_writes_english_when_asked(self) -> None:
        report = build(locale="en")

        assert "Diagnóstico" not in report.title
