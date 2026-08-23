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
)
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


def measured_evidence(signals: SiteSignals) -> list[Evidence]:
    """Our own signals as evidence.

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
            )
        )

    if signals.security_headers:
        evidence.append(
            Evidence(
                text=f"Security headers present: {', '.join(signals.security_headers)}",
                source=EvidenceSource.MEASURED,
                ref=ref,
            )
        )

    if signals.missing_security_headers:
        evidence.append(
            Evidence(
                text=f"Security headers absent: {', '.join(signals.missing_security_headers)}",
                source=EvidenceSource.MEASURED,
                ref=ref,
            )
        )

    if signals.framework:
        evidence.append(
            Evidence(
                text=f"Framework detected: {signals.framework}",
                source=EvidenceSource.MEASURED,
                ref=ref,
            )
        )

    if signals.sitemap is not None or signals.robots_txt is not None:
        found = [
            name
            for name, present in (("robots.txt", signals.robots_txt), ("sitemap", signals.sitemap))
            if present
        ]
        evidence.append(
            Evidence(
                text=f"Crawlability files found: {', '.join(found)}" if found
                else "Neither robots.txt nor a sitemap was found",
                source=EvidenceSource.MEASURED,
                ref=ref,
            )
        )

    return evidence


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

    if any(item.partial for item in ordered) and not measured_items:
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
