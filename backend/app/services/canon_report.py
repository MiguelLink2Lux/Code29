"""The report built on the ten-point canon.

Structure is enforced by the model, not by convention: ten sections, always, in
canon order, and exactly one closing proposal. The first rule is what makes two
leads' reports comparable; the second is what stops the canon becoming a menu of
ten purchasable items, which ADR 0008 rejects.

The tone rule matters as much as the structure. An uncovered point is a stage of
the flow the client has not built — the thing we get to propose — and never an
accusation. "You have no tests" when nobody asked is the sentence this module
exists to make impossible: an unevaluated point carries no diagnosis at all, and
its narrative is written from a fixed phrase per point rather than composed from
the absence.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.services.canon import (
    CANON_POINTS,
    CanonPoint,
    Evidence,
    PointState,
)
from app.services.evidence import (
    measured_evidence_for,
    parse_model_evidence,
    resolve_with_sources,
)
from app.services.report import SiteSignals

TEMPLATE_GENERATOR_NAME = "template:canon"


class ClosingProposal(BaseModel):
    """The single engagement every report closes on.

    Fixed on purpose: the offering does not change with the findings. What
    changes is the order of the roadmap, which the sections carry.
    """

    model_config = ConfigDict(frozen=True)

    headline: str = Field(min_length=1)
    parts: tuple[str, str, str]
    rationale: str = Field(min_length=1)


class CanonSection(BaseModel):
    """One canon point as it appears in the report."""

    point: CanonPoint
    state: PointState
    heading: str = Field(min_length=1)
    #: Always present: even an unevaluated point must say something useful.
    narrative: str = Field(min_length=1)
    #: Empty whenever the state is NOT_EVALUATED — silence is not a finding.
    diagnosis: str = ""
    evidence: list[Evidence] = Field(default_factory=list)
    is_opportunity: bool

    @model_validator(mode="after")
    def _unevaluated_carries_no_diagnosis(self) -> CanonSection:
        if self.state is PointState.NOT_EVALUATED and self.diagnosis:
            raise ValueError(
                f"point {self.point.number} is not evaluated and must carry no diagnosis"
            )
        return self


class CanonReport(BaseModel):
    """The delivered artefact: ten sections in canon order, one proposal."""

    title: str = Field(min_length=1)
    summary: str = Field(min_length=1)
    sections: list[CanonSection]
    proposal: ClosingProposal
    generator: str = Field(min_length=1)

    @model_validator(mode="after")
    def _ten_sections_in_canon_order(self) -> CanonReport:
        if len(self.sections) != len(CANON_POINTS):
            raise ValueError(
                f"a canon report has ten sections, got {len(self.sections)}: the fixed "
                "canon is what makes two reports comparable"
            )

        numbers = [section.point.number for section in self.sections]
        if numbers != [point.number for point in CANON_POINTS]:
            raise ValueError(f"sections must follow canon order, got {numbers}")

        return self


# --- Copy ------------------------------------------------------------------
#
# The unevaluated narrative is a fixed phrase per locale, deliberately. Composing
# it from the absence is how "not reported" becomes "you don't have it".

_COPY: dict[str, dict[str, str]] = {
    "es": {
        "title": "Diagnóstico de flujo de trabajo — {company}",
        "summary": (
            "{name}, esta hoja de ruta recorre los diez puntos del flujo de desarrollo "
            "asistido por IA y sitúa en qué estado está cada uno en {company}."
        ),
        "covered": "Cubierto según lo observado.",
        "partial": "Presente de forma parcial o sin una puerta que lo garantice.",
        "not_evaluated": (
            "Sin información en esta conversación. Es una de las partes del flujo que "
            "conviene plantear desde el principio."
        ),
        "proposal_headline": "Preparación del flujo de desarrollo asistido por IA",
        "proposal_parts": (
            "Formación del equipo",
            "Preparación del entorno de desarrollo",
            "Definición y control de criterios de calidad",
        ),
        "proposal_rationale": (
            "Los diez puntos no se contratan por separado: son la hoja de ruta de una "
            "única implantación, y su orden lo marca el estado en que está hoy cada uno."
        ),
    },
    "en": {
        "title": "Workflow assessment — {company}",
        "summary": (
            "{name}, this roadmap walks the ten points of an AI-assisted development "
            "workflow and places where {company} stands on each."
        ),
        "covered": "Covered, according to what was observed.",
        "partial": "Present in part, or without a gate that guarantees it.",
        "not_evaluated": (
            "Not covered in this conversation. It is one of the parts of the flow worth "
            "putting on the table from the start."
        ),
        "proposal_headline": "Preparing the AI-assisted development workflow",
        "proposal_parts": (
            "Team training",
            "Development environment preparation",
            "Quality criteria definition and control",
        ),
        "proposal_rationale": (
            "The ten points are not bought separately: they are the roadmap of a single "
            "engagement, and their order follows where each one stands today."
        ),
    },
}


def _locale(value: str) -> str:
    return value if value in _COPY else "es"


def _narrative(state: PointState, locale: str) -> str:
    copy = _COPY[locale]

    if state is PointState.COVERED:
        return copy["covered"]
    if state is PointState.PARTIAL:
        return copy["partial"]

    return copy["not_evaluated"]


def _proposal(locale: str) -> ClosingProposal:
    copy = _COPY[locale]

    return ClosingProposal(
        headline=copy["proposal_headline"],
        parts=copy["proposal_parts"],  # type: ignore[arg-type]
        rationale=copy["proposal_rationale"],
    )


def build_canon_report(
    *,
    contact_name: str,
    company: str,
    locale: str = "es",
    team: str | None = None,
    site: SiteSignals,
    reported: dict[str, Any] | None = None,
    cited: dict[str, Any] | None = None,
    generator: str = TEMPLATE_GENERATOR_NAME,
) -> CanonReport:
    """Assemble the report from evidence grouped per canon point.

    `reported` and `cited` are keyed by canon point id and hold raw claim dicts —
    they arrive from a model, so they go through `parse_model_evidence` and
    anything unsourced is dropped before it can reach a section.
    """
    resolved_locale = _locale(locale)
    reported = reported or {}
    cited = cited or {}

    sections: list[CanonSection] = []

    for point in CANON_POINTS:
        assessment = resolve_with_sources(
            point,
            # Only the signals that genuinely evidence THIS point: a sourced
            # claim attached to the wrong point is still a falsehood.
            measured=measured_evidence_for(point, site),
            reported=parse_model_evidence(reported.get(point.id, [])),
            cited=parse_model_evidence(cited.get(point.id, [])),
        )

        sections.append(
            CanonSection(
                point=point,
                state=assessment.state,
                heading=f"{point.number}. {point.title}",
                narrative=_narrative(assessment.state, resolved_locale),
                diagnosis=assessment.diagnosis,
                evidence=assessment.evidence,
                is_opportunity=assessment.is_opportunity,
            )
        )

    copy = _COPY[resolved_locale]

    return CanonReport(
        title=copy["title"].format(company=company),
        summary=copy["summary"].format(name=contact_name, company=company),
        sections=sections,
        proposal=_proposal(resolved_locale),
        generator=generator,
    )


class TemplateCanonGenerator:
    """Deterministic canon report: same evidence in, byte-identical report out.

    The generator that runs without a key, and the one every test uses. It writes
    no prose of its own beyond the fixed copy above, which is exactly why it
    cannot fabricate a finding.
    """

    name = TEMPLATE_GENERATOR_NAME

    async def generate(
        self,
        *,
        contact_name: str,
        company: str,
        locale: str = "es",
        team: str | None = None,
        site: SiteSignals,
        reported: dict[str, Any] | None = None,
        cited: dict[str, Any] | None = None,
    ) -> CanonReport:
        return build_canon_report(
            contact_name=contact_name,
            company=company,
            locale=locale,
            team=team,
            site=site,
            reported=reported,
            cited=cited,
            generator=self.name,
        )
