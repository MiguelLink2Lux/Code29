"""The ten-point improvement canon, as a model.

Source of truth for the text and the doctrine: `docs/architecture/improvement-canon.md`
and ADR 0008. Two things that document settles and this module enforces:

- **The canon is not a catalogue.** No point maps to a service. `CanonPoint` has
  no field for one, deliberately: adding it would invite the mapping the
  doctrine rejects.
- **An absence is an opportunity, not a hole.** A point with no evidence resolves
  to `no evaluado` with an empty diagnosis — and is flagged as an opportunity,
  because silence is the clearest indication the client does not contemplate that
  part of the flow. What stays forbidden is turning silence into an accusation.

Evidence carries its source so every claim in the report is attributable. An
unsourced claim cannot be constructed, which is how a model's invention about a
real company is kept out of a lead's inbox.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator


class EvidenceSource(StrEnum):
    """Where a claim came from. There is no fourth option on purpose."""

    MEASURED = "measured"  # our own signal, e.g. the SSRF-guarded site analysis
    REPORTED = "reported"  # the visitor said it in the conversation
    CITED = "cited"  # the model found it and cited a source


class PointState(StrEnum):
    COVERED = "cubierto"
    PARTIAL = "parcial"
    NOT_EVALUATED = "no evaluado"


class Evidence(BaseModel):
    """One attributable fact. `source` is required: an unsourced claim is refused."""

    model_config = ConfigDict(frozen=True)

    text: str = Field(min_length=1)
    source: EvidenceSource
    ref: str = ""
    #: The practice exists but without a gate, or only in part.
    partial: bool = False
    #: A citation that disagrees with what the visitor reported.
    contradicts_reported: bool = False


class CanonPoint(BaseModel):
    """A point of the canon. No service field — see the module docstring."""

    model_config = ConfigDict(frozen=True)

    number: int = Field(ge=1, le=10)
    id: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    title: str = Field(min_length=1)
    #: What can be checked to decide the state, per the canon document.
    signal: str = Field(min_length=1)
    #: Permanent condition rather than a step that gets finished (points 2 and 10).
    transversal: bool = False


class PointAssessment(BaseModel):
    """The verdict for one point, with the evidence that justifies it."""

    point: CanonPoint
    state: PointState
    evidence: list[Evidence] = Field(default_factory=list)
    #: Empty whenever the state is NOT_EVALUATED: no evidence, no diagnosis.
    diagnosis: str = ""

    @model_validator(mode="after")
    def _state_must_be_justified(self) -> PointAssessment:
        if self.state is not PointState.NOT_EVALUATED and not self.evidence:
            raise ValueError(
                f"state {self.state!r} requires evidence: an unjustified verdict is a "
                "fabricated diagnosis"
            )

        if self.state is PointState.NOT_EVALUATED and self.diagnosis:
            raise ValueError("a not-evaluated point must carry no diagnosis")

        return self

    @property
    def is_opportunity(self) -> bool:
        """True when the point is not covered — the part of the flow to propose."""
        return self.state is not PointState.COVERED


CANON_POINTS: tuple[CanonPoint, ...] = (
    CanonPoint(
        number=1,
        id="structured_planning",
        title="Planificación estructurada y contexto profundo",
        signal="Requisitos, esquemas y documentación de arquitectura accesibles al equipo "
        "y a las herramientas de IA",
    ),
    CanonPoint(
        number=2,
        id="team_training",
        title="Capacitación continua de los equipos",
        signal="Formación declarada en ingeniería de prompts y arquitecturas de agentes, "
        "no sólo en el uso de herramientas",
        transversal=True,
    ),
    CanonPoint(
        number=3,
        id="work_management",
        title="Sistemas de gestión de trabajo inteligentes",
        signal="Gestor de tareas con agentes integrados: refinamiento de backlog, "
        "predicción de cuellos de botella",
    ),
    CanonPoint(
        number=4,
        id="engineer_in_the_loop",
        title="Desarrollo asistido por IA — el ingeniero en el bucle",
        signal="Responsabilidad humana explícita sobre el código que llega a producción",
    ),
    CanonPoint(
        number=5,
        id="iterative_automation",
        title="Automatización iterativa y modular",
        signal="Trabajo descompuesto en lotes pequeños y verificables, no generaciones "
        "de sistemas completos de una vez",
    ),
    CanonPoint(
        number=6,
        id="ai_guided_testing",
        title="Testing guiado por IA (test-first)",
        signal="Suite de tests automatizados que bloquea el merge",
    ),
    CanonPoint(
        number=7,
        id="code_review_filter",
        title="Revisión de código como primer filtro",
        signal="Revisión obligatoria en las pull requests, con agentes como primera línea",
    ),
    CanonPoint(
        number=8,
        id="predictive_cicd",
        title="CI/CD y DevOps predictivo",
        signal="Pipeline de integración y despliegue, con rollback automatizado y "
        "detección de anomalías",
    ),
    CanonPoint(
        number=9,
        id="living_documentation",
        title="Documentación viva y contexto histórico",
        signal="Documentación y decisiones versionadas junto al código, consultables por "
        "agentes",
    ),
    CanonPoint(
        number=10,
        id="data_governance",
        title="Gobernanza de datos, secretos y dependencias",
        signal="Política de uso de LLMs, gestión de secretos y escaneo de dependencias "
        "en el pipeline",
        transversal=True,
    ),
)

_BY_NUMBER = {point.number: point for point in CANON_POINTS}


def point_by_number(number: int) -> CanonPoint:
    """The point with that number, or KeyError. The canon has exactly ten."""
    return _BY_NUMBER[number]


def resolve_point(point: CanonPoint, *, evidence: list[Evidence]) -> PointAssessment:
    """Resolve one point from its evidence, refusing to invent a verdict.

    Precedence, and why:

    - **No evidence → not evaluated**, with no diagnosis. Silence is not a finding.
    - **A citation that contradicts a reported answer → not evaluated.** Telling a
      lead their own answer was wrong, on the strength of a search result, is
      worse than saying nothing. Unless we measured it ourselves: our own signal
      outranks a citation.
    - **Partial evidence → partial**, so "some tests but no gate" does not read as
      covered.
    """
    if not evidence:
        return PointAssessment(point=point, state=PointState.NOT_EVALUATED)

    measured = [item for item in evidence if item.source is EvidenceSource.MEASURED]
    contradicted = any(item.contradicts_reported for item in evidence)

    if contradicted and not measured:
        return PointAssessment(point=point, state=PointState.NOT_EVALUATED, evidence=evidence)

    if any(item.partial for item in evidence) and not measured:
        return PointAssessment(
            point=point,
            state=PointState.PARTIAL,
            evidence=evidence,
            diagnosis=evidence[0].text,
        )

    return PointAssessment(
        point=point,
        state=PointState.COVERED,
        evidence=evidence,
        diagnosis=evidence[0].text,
    )
