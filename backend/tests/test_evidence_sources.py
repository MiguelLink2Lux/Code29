"""Parsing model-produced evidence: unsourced claims are dropped, not fatal.

`canon.Evidence` refuses construction without a source, which protects our own
code. This module is the boundary where a *model* hands us claims, and the rule
there is different: one bad item must not destroy a whole report, so invalid
items are dropped and the rest survive.

That asymmetry is the point. A hard failure would tempt a future fallback to the
template ("the model answered, mostly"), and a lead would receive a template
report believing a model wrote it. Dropping keeps the report honest and useful.
"""

import pytest

from app.services.canon import CANON_POINTS, Evidence, EvidenceSource, PointState
from app.services.evidence import (
    dropped_claim_count,
    measured_evidence,
    parse_model_evidence,
    resolve_with_sources,
)
from app.services.report import SiteSignals


class TestParsingModelEvidence:
    def test_keeps_a_well_formed_claim(self) -> None:
        parsed = parse_model_evidence(
            [{"text": "CI pipeline visible in their repo", "source": "cited",
              "ref": "https://example.com/repo"}]
        )

        assert len(parsed) == 1
        assert parsed[0].source is EvidenceSource.CITED

    def test_drops_a_claim_with_no_source(self) -> None:
        # The shape a hallucination takes: a confident sentence with nothing behind it.
        parsed = parse_model_evidence(
            [{"text": "they probably deploy manually"},
             {"text": "HSTS header present", "source": "measured", "ref": "site"}]
        )

        assert len(parsed) == 1
        assert parsed[0].text == "HSTS header present"

    def test_drops_a_claim_with_an_invented_source(self) -> None:
        parsed = parse_model_evidence(
            [{"text": "industry knowledge says so", "source": "intuition"}]
        )

        assert parsed == []

    def test_drops_a_cited_claim_with_no_reference(self) -> None:
        # "cited" without a URL is an appeal to authority with no authority.
        parsed = parse_model_evidence([{"text": "their blog says so", "source": "cited"}])

        assert parsed == []

    def test_keeps_a_reported_claim_without_a_reference(self) -> None:
        # Only `cited` needs a URL; the visitor saying it IS the reference.
        parsed = parse_model_evidence(
            [{"text": "we deploy by hand", "source": "reported"}]
        )

        assert len(parsed) == 1

    def test_drops_an_empty_text(self) -> None:
        assert parse_model_evidence([{"text": "   ", "source": "measured"}]) == []

    def test_survives_garbage_instead_of_a_list(self) -> None:
        for garbage in [None, "a string", {"text": "x"}, 42]:
            assert parse_model_evidence(garbage) == []  # type: ignore[arg-type]

    def test_survives_a_non_dict_item(self) -> None:
        parsed = parse_model_evidence(
            ["just a string", {"text": "real", "source": "reported"}]  # type: ignore[list-item]
        )

        assert len(parsed) == 1

    def test_reports_how_many_claims_it_dropped(self) -> None:
        # Silent dropping hides a model that is misbehaving; the count is what a
        # log line or a metric can act on.
        items = [
            {"text": "unsourced", "source": None},
            {"text": "bad source", "source": "vibes"},
            {"text": "fine", "source": "reported"},
        ]

        assert dropped_claim_count(items) == 2


class TestMeasuredEvidence:
    def test_turns_a_measured_signal_into_sourced_evidence(self) -> None:
        signals = SiteSignals(available=True, https=True, url="https://example.com")

        evidence = measured_evidence(signals)

        assert evidence
        assert all(item.source is EvidenceSource.MEASURED for item in evidence)

    def test_an_unreadable_site_yields_nothing_rather_than_a_negative(self) -> None:
        # available=False means we never read the page. Emitting "no HTTPS" here
        # would be inventing a finding out of our own failure to fetch.
        evidence = measured_evidence(SiteSignals(available=False))

        assert evidence == []

    def test_every_measured_item_references_the_site(self) -> None:
        signals = SiteSignals(available=True, https=True, url="https://example.com",
                              missing_security_headers=["Content-Security-Policy"])

        for item in measured_evidence(signals):
            assert item.ref


class TestResolutionWithSources:
    def test_a_contradiction_resolves_to_not_evaluated(self) -> None:
        assessment = resolve_with_sources(
            CANON_POINTS[7],
            reported=[Evidence(text="no tenemos CI", source=EvidenceSource.REPORTED, ref="chat")],
            cited=[Evidence(text="CI badge in their README", source=EvidenceSource.CITED,
                            ref="https://example.com", contradicts_reported=True)],
            measured=[],
        )

        assert assessment.state is PointState.NOT_EVALUATED
        assert assessment.diagnosis == ""

    def test_measured_wins_over_a_contradicting_citation(self) -> None:
        assessment = resolve_with_sources(
            CANON_POINTS[7],
            reported=[],
            cited=[Evidence(text="blog says no pipeline", source=EvidenceSource.CITED,
                            ref="https://example.com", contradicts_reported=True)],
            measured=[Evidence(text="pipeline config served publicly",
                               source=EvidenceSource.MEASURED, ref="site")],
        )

        assert assessment.state is PointState.COVERED

    def test_nothing_at_all_is_not_evaluated_and_an_opportunity(self) -> None:
        assessment = resolve_with_sources(CANON_POINTS[5], reported=[], cited=[], measured=[])

        assert assessment.state is PointState.NOT_EVALUATED
        assert assessment.is_opportunity is True

    def test_measured_evidence_is_listed_before_the_rest(self) -> None:
        # The measured signals are what give the report its credibility, so they
        # lead. A citation supporting the same point comes after.
        assessment = resolve_with_sources(
            CANON_POINTS[9],
            reported=[Evidence(text="reported", source=EvidenceSource.REPORTED, ref="chat")],
            cited=[Evidence(text="cited", source=EvidenceSource.CITED, ref="https://x.test")],
            measured=[Evidence(text="measured", source=EvidenceSource.MEASURED, ref="site")],
        )

        assert [item.source for item in assessment.evidence][0] is EvidenceSource.MEASURED


def test_parse_then_resolve_never_produces_an_unsourced_verdict() -> None:
    # The end-to-end property this module exists for: whatever the model says,
    # a delivered verdict is always backed by evidence that names its origin.
    raw = [{"text": "no source at all"}, {"text": "we run tests", "source": "reported"}]

    parsed = parse_model_evidence(raw)
    assessment = resolve_with_sources(CANON_POINTS[5], reported=parsed, cited=[], measured=[])

    assert assessment.state is PointState.COVERED
    assert all(item.source for item in assessment.evidence)


def test_a_report_built_only_from_unsourced_claims_evaluates_nothing() -> None:
    parsed = parse_model_evidence([{"text": "a"}, {"text": "b"}, {"text": "c"}])

    assessments = [
        resolve_with_sources(point, reported=parsed, cited=[], measured=[])
        for point in CANON_POINTS
    ]

    assert all(a.state is PointState.NOT_EVALUATED for a in assessments)


@pytest.mark.parametrize("source", ["measured", "reported", "cited"])
def test_the_three_sources_are_the_only_ones_accepted(source: str) -> None:
    ref = "https://example.com" if source == "cited" else "chat"
    parsed = parse_model_evidence([{"text": "claim", "source": source, "ref": ref}])

    assert len(parsed) == 1
