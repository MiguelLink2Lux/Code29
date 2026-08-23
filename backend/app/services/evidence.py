"""The boundary where model-produced claims become evidence, or get dropped.

`canon.Evidence` refuses construction without a source: that protects our own
code from writing an unattributable claim. Here the input comes from a *model*,
and the rule has to be different — one malformed item must not destroy a whole
report, because a hard failure invites the worst possible fallback: shipping the
template report while a lead believes a model wrote it.

So invalid items are dropped and the rest survive. `dropped_claim_count` exists
so that dropping is observable: a model quietly emitting unsourced claims is
worth a metric, not a shrug.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from typing import Any

from app.services.canon import (
    CanonPoint,
    Evidence,
    EvidenceSource,
    PointAssessment,
    PointState,
)  # noqa: I001 — grouped deliberately, CanonPoint is used in the signatures below
from app.services.report import SiteSignals

_VALID_SOURCES = {source.value for source in EvidenceSource}


def _coerce(item: Any) -> Evidence | None:
    """One raw item to Evidence, or None. Never raises: the caller is a parser."""
    if not isinstance(item, dict):
        return None

    text = item.get("text")
    source = item.get("source")
    ref = item.get("ref") or ""

    if not isinstance(text, str) or not text.strip():
        return None

    if not isinstance(source, str) or source not in _VALID_SOURCES:
        return None

    # A citation without a reference is an appeal to an authority that is never
    # named — exactly the shape of an invented source.
    if source == EvidenceSource.CITED.value and not (isinstance(ref, str) and ref.strip()):
        return None

    try:
        return Evidence(
            text=text.strip(),
            source=EvidenceSource(source),
            ref=str(ref).strip(),
            partial=bool(item.get("partial", False)),
            contradicts_reported=bool(item.get("contradicts_reported", False)),
        )
    except ValueError:
        return None


def parse_model_evidence(items: Any) -> list[Evidence]:
    """Every claim the model produced that names a usable source. Drops the rest."""
    if not isinstance(items, Sequence) or isinstance(items, str | bytes):
        return []

    parsed = (_coerce(item) for item in items)

    return [item for item in parsed if item is not None]


def dropped_claim_count(items: Any) -> int:
    """How many claims were discarded — worth logging when it is not zero."""
    if not isinstance(items, Sequence) or isinstance(items, str | bytes):
        return 0

    return sum(1 for item in items if _coerce(item) is None)


#: The only canon point a home page can say anything about, and even then weakly.
#: Everything else a page reveals — framework, sitemap, page weight — is context
#: about their stack, not evidence of how they work.
_SECURITY_POINT = 10


def measured_evidence(signals: SiteSignals) -> list[Evidence]:
    """Every signal we measured, regardless of which point it speaks to.

    Kept for callers that want the raw pool (report context, for instance). To
    resolve a canon point, use `measured_evidence_for`: a signal attached to the
    wrong point is a false statement about the lead even though it is sourced.

    Returns nothing when the page was never read. Emitting "no HTTPS" because we
    failed to fetch would turn our own failure into a finding about the lead.
    """
    if not signals.available:
        return []

    ref = signals.url or "site"
    evidence: list[Evidence] = []

    if signals.https is not None:
        evidence.append(
            Evidence(
                text="HTTPS enabled" if signals.https else "HTTPS not enabled",
                source=EvidenceSource.MEASURED,
                ref=ref,
                partial=True,
            )
        )

    if signals.security_headers:
        evidence.append(
            Evidence(
                text=f"Security headers present: {', '.join(signals.security_headers)}",
                source=EvidenceSource.MEASURED,
                ref=ref,
                partial=True,
            )
        )

    if signals.missing_security_headers:
        evidence.append(
            Evidence(
                text=f"Security headers absent: {', '.join(signals.missing_security_headers)}",
                source=EvidenceSource.MEASURED,
                ref=ref,
                partial=True,
            )
        )

    return evidence


def measured_evidence_for(point: CanonPoint, signals: SiteSignals) -> list[Evidence]:
    """The measured signals that genuinely evidence *this* point.

    Only the security signals map to a canon point, and only to governance —
    marked `partial`, because a present HSTS header is a hint about security
    posture, not proof that secret management and dependency scanning exist.

    Nothing on a home page proves a pipeline exists or that documentation lives
    beside the code, so points 8 and 9 get no measured evidence at all. The live
    run that prompted this returned "Framework detected: Next.js" as grounds for
    marking CI/CD *covered*, which is exactly the kind of sourced falsehood this
    module is supposed to prevent.
    """
    if point.number != _SECURITY_POINT:
        return []

    return measured_evidence(signals)


def resolve_with_sources(
    point: CanonPoint,
    *,
    measured: Iterable[Evidence],
    reported: Iterable[Evidence],
    cited: Iterable[Evidence],
) -> PointAssessment:
    """Resolve a point from evidence grouped by origin.

    Measured evidence leads the list: our own signals are what give the report
    its credibility, so they are what the reader sees first.

    A citation contradicting what the visitor reported collapses the point to
    `no evaluado` — unless we measured it ourselves. Telling a lead their own
    answer was wrong on the strength of a search result is worse than saying
    nothing; telling them so on the strength of our own measurement is fair.
    """
    measured_items = list(measured)
    ordered = [*measured_items, *reported, *cited]

    if not ordered:
        return PointAssessment(point=point, state=PointState.NOT_EVALUATED)

    contradicted = any(item.contradicts_reported for item in ordered)

    if contradicted and not measured_items:
        return PointAssessment(point=point, state=PointState.NOT_EVALUATED, evidence=ordered)

    # Partial stays partial whatever its source. Measured evidence is more
    # trustworthy than reported evidence, which is why it outranks a
    # contradiction above — but that does not make weak evidence strong. A
    # present HSTS header is a hint about security posture, not proof that
    # secret management and dependency scanning exist.
    if all(item.partial for item in ordered):
        return PointAssessment(
            point=point,
            state=PointState.PARTIAL,
            evidence=ordered,
            diagnosis=ordered[0].text,
        )

    return PointAssessment(
        point=point,
        state=PointState.COVERED,
        evidence=ordered,
        diagnosis=ordered[0].text,
    )
