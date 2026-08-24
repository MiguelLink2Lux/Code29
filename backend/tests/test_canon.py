"""The ten-point canon as a model, and the tri-state resolver.

The canon (docs/architecture/improvement-canon.md, ADR 0008) is the instrument
for analysing a lead's project and the roadmap of the deliverable. It is NOT a
catalogue: no point maps to a service.

The resolver's whole job is factual honesty. It must never turn silence into an
accusation, and it must never invent a state — but an uncovered point is a
first-class, commercially valuable outcome, not a hole to be filled.
"""

import pytest

from app.services.canon import (
    CANON_POINTS,
    CanonPoint,
    Evidence,
    EvidenceSource,
    PointAssessment,
    PointState,
    resolve_point,
)


class TestCanonShape:
    def test_has_exactly_ten_points(self) -> None:
        assert len(CANON_POINTS) == 10

    def test_points_are_numbered_one_to_ten_in_order(self) -> None:
        assert [point.number for point in CANON_POINTS] == list(range(1, 11))

    def test_every_point_has_a_stable_identifier(self) -> None:
        identifiers = [point.id for point in CANON_POINTS]

        assert len(set(identifiers)) == 10
        for identifier in identifiers:
            assert identifier.islower()
            assert " " not in identifier

    def test_the_two_transversal_points_are_marked(self) -> None:
        # Training and governance are permanent conditions, not steps that get
        # finished — see the canon document.
        transversal = [point.number for point in CANON_POINTS if point.transversal]

        assert transversal == [2, 10]

    def test_the_other_eight_are_sequential(self) -> None:
        sequential = [point.number for point in CANON_POINTS if not point.transversal]

        assert sequential == [1, 3, 4, 5, 6, 7, 8, 9]

    def test_every_point_carries_its_title_and_observable_signal(self) -> None:
        for point in CANON_POINTS:
            assert point.title.strip()
            assert point.signal.strip(), f"point {point.number} has no observable signal"

    def test_no_point_declares_a_service(self) -> None:
        # ADR 0008: the canon is an analysis instrument, not a menu. A field for
        # a service would invite exactly the mapping the doctrine rejects.
        assert not hasattr(CanonPoint, "service")
        assert "service" not in CanonPoint.model_fields


class TestResolver:
    @staticmethod
    def measured(text: str = "CI pipeline detected") -> Evidence:
        return Evidence(text=text, source=EvidenceSource.MEASURED, ref="site")

    @staticmethod
    def reported(text: str = "we run tests on every merge") -> Evidence:
        return Evidence(text=text, source=EvidenceSource.REPORTED, ref="chat")

    @staticmethod
    def cited(text: str = "engineering blog describes their pipeline") -> Evidence:
        return Evidence(text=text, source=EvidenceSource.CITED, ref="https://example.com/blog")

    def test_no_evidence_resolves_to_not_evaluated(self) -> None:
        assessment = resolve_point(CANON_POINTS[0], evidence=[])

        assert assessment.state is PointState.NOT_EVALUATED

    def test_not_evaluated_carries_no_diagnosis(self) -> None:
        # The forbidden jump: silence must never become "you have no tests".
        assessment = resolve_point(CANON_POINTS[5], evidence=[])

        assert assessment.diagnosis == ""

    def test_a_measured_signal_covers_the_point(self) -> None:
        assessment = resolve_point(CANON_POINTS[7], evidence=[self.measured()])

        assert assessment.state is PointState.COVERED

    def test_a_reported_answer_covers_the_point(self) -> None:
        assessment = resolve_point(CANON_POINTS[5], evidence=[self.reported()])

        assert assessment.state is PointState.COVERED

    def test_partial_evidence_resolves_to_partial(self) -> None:
        assessment = resolve_point(
            CANON_POINTS[5],
            evidence=[Evidence(text="we have some tests but nothing blocks a merge",
                               source=EvidenceSource.REPORTED, ref="chat", partial=True)],
        )

        assert assessment.state is PointState.PARTIAL

    def test_evidence_without_a_source_is_refused(self) -> None:
        # An unsourced claim is exactly how a model gets a falsehood about a real
        # company into a report.
        with pytest.raises(ValueError):
            Evidence(text="they probably deploy manually", source=None, ref="")  # type: ignore[arg-type]

    def test_a_citation_contradicting_a_reported_answer_falls_back_to_not_evaluated(self) -> None:
        # Better to say nothing than to tell a lead their own answer was wrong.
        assessment = resolve_point(
            CANON_POINTS[7],
            evidence=[
                Evidence(text="no CI", source=EvidenceSource.REPORTED, ref="chat"),
                Evidence(text="CI badge on their README",
                         source=EvidenceSource.CITED, ref="https://example.com",
                         contradicts_reported=True),
            ],
        )

        assert assessment.state is PointState.NOT_EVALUATED
        assert assessment.diagnosis == ""

    def test_the_assessment_keeps_its_evidence_for_the_report(self) -> None:
        evidence = [self.measured(), self.cited()]

        assessment = resolve_point(CANON_POINTS[7], evidence=evidence)

        assert assessment.evidence == evidence

    def test_measured_evidence_outranks_a_citation(self) -> None:
        # We measured it ourselves; a search result cannot overrule that.
        assessment = resolve_point(
            CANON_POINTS[7],
            evidence=[
                self.measured("HSTS header present"),
                Evidence(text="blog says otherwise", source=EvidenceSource.CITED,
                         ref="https://example.com", contradicts_reported=True),
            ],
        )

        assert assessment.state is PointState.COVERED


class TestAssessmentInventory:
    def test_an_assessment_exists_for_every_point_even_with_no_evidence(self) -> None:
        # Ten points always present: that is what makes the canon comparable
        # between leads.
        assessments = [resolve_point(point, evidence=[]) for point in CANON_POINTS]

        assert len(assessments) == 10
        assert all(a.state is PointState.NOT_EVALUATED for a in assessments)

    def test_uncovered_points_are_reported_as_opportunities(self) -> None:
        # Doctrine (ADR 0008 revision): an absence is the clearest indication the
        # client does not contemplate that part of the flow, and that is what we
        # get to propose. The flag exists so the generator can say so.
        assessment = resolve_point(CANON_POINTS[0], evidence=[])

        assert assessment.is_opportunity is True

    def test_a_covered_point_is_not_an_opportunity(self) -> None:
        assessment = resolve_point(CANON_POINTS[0], evidence=[TestResolver.measured()])

        assert assessment.is_opportunity is False


def test_point_lookup_by_number() -> None:
    from app.services.canon import point_by_number

    assert point_by_number(6).number == 6
    with pytest.raises(KeyError):
        point_by_number(11)


def test_assessment_rejects_a_state_it_cannot_justify() -> None:
    # Constructing "covered" with no evidence is a programming error, not a
    # judgement call: it is how a fabricated diagnosis would enter.
    with pytest.raises(ValueError, match="evidence"):
        PointAssessment(point=CANON_POINTS[0], state=PointState.COVERED, evidence=[])
