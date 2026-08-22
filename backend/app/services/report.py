"""Workflow report: the generator port, a deterministic stub, and the factory.

The report is a lead magnet, so its credibility is the product. Two rules keep it
credible and are enforced by tests rather than by discipline:

* **Grounded.** A generator receives `ReportFacts` — the visitor's answers plus
  signals actually measured from their home page — and nothing else. A site that
  could not be read produces "not analysed", never a confident claim.
* **Bounded input.** `ReportFacts` has no field for an email address and no field
  for free text instructions. When a real model replaces the stub, the client
  cannot smuggle a prompt into it and the one piece of PII we hold never leaves.

The port is async because the implementation that matters later — a model call —
is network I/O. The stub ignores that and returns immediately, which keeps
enabling Genkit an environment change rather than a refactor.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Literal, Protocol

from pydantic import BaseModel, Field

from app.services.report_copy import (
    AXIS_COPY,
    PRACTICE_LABELS,
    TEMPLATE_COPY,
    resolve_locale,
)

STUB_GENERATOR = "stub"
GENKIT_GENERATOR = "genkit"
GEMINI_GENERATOR = "gemini"


class UnusableReportGenerator(Exception):
    """Raised when the configured generator cannot be built.

    Never falls back to the stub: shipping a template report while the operator
    believes a model wrote it is worse than failing.
    """


class DiagnosisAxis(StrEnum):
    """The five axes every report diagnoses, in report order."""

    AI_DEVELOPMENT = "ai_development"
    AI_QUALITY = "ai_quality"
    DELIVERY_AUTOMATION = "delivery_automation"
    SECURITY_DEPENDENCIES = "security_dependencies"
    OBSERVABILITY = "observability"


class ServiceOffering(StrEnum):
    """The four services the site actually sells. Recommendations map onto these."""

    CTO_AS_A_SERVICE = "cto-as-a-service"
    AI_ANALYSIS = "ai-analysis-and-transformation"
    AI_PROJECT_MANAGER = "ai-project-manager"
    DEVOPS_AI = "devops-ai-automation"


class Priority(StrEnum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

    @property
    def rank(self) -> int:
        """Sort key: 0 is most urgent."""
        return {Priority.HIGH: 0, Priority.MEDIUM: 1, Priority.LOW: 2}[self]


class WorkflowAnswers(BaseModel):
    """How the company works today, as reported by the visitor."""

    practices: list[str] = Field(default_factory=list)
    team_size: str | None = None
    notes: str | None = None


class SiteSignals(BaseModel):
    """Measured facts about the lead's home page.

    `available=False` means the page was never read: every other field must then
    be ignored rather than treated as a negative finding.
    """

    available: bool
    url: str | None = None
    https: bool | None = None
    security_headers: list[str] = Field(default_factory=list)
    missing_security_headers: list[str] = Field(default_factory=list)
    title: str | None = None
    description: str | None = None
    canonical: str | None = None
    robots_txt: bool | None = None
    sitemap: bool | None = None
    framework: str | None = None
    page_weight_bytes: int | None = None
    resource_count: int | None = None


class ReportFacts(BaseModel):
    """Everything a generator is allowed to see. No email, no free-text prompt."""

    contact_name: str
    company: str
    locale: Literal["es", "en"] = "es"
    workflow: WorkflowAnswers
    site: SiteSignals


class ReportSection(BaseModel):
    axis: DiagnosisAxis
    heading: str
    diagnosis: str
    evidence: list[str]


class Recommendation(BaseModel):
    axis: DiagnosisAxis
    action: str
    rationale: str
    service: ServiceOffering
    priority: Priority


class ContactReport(BaseModel):
    """The delivered artefact. Carries no timestamp: delivery stamps the email."""

    title: str
    summary: str
    sections: list[ReportSection]
    recommendations: list[Recommendation]
    generator: str


class ReportGenerator(Protocol):
    """Port. One method, so a model implementation is a drop-in replacement."""

    async def generate(self, facts: ReportFacts) -> ContactReport: ...


# --- Axis definitions ------------------------------------------------------
#
# Each axis names the practices that evidence it and the service that fixes the
# gap. Every one of the four services is reachable, so no offering is invisible
# to this funnel.

_PRACTICE_LABELS = {
    "ai_assisted_coding": "AI-assisted coding in the daily loop",
    "ai_bug_triage": "AI-assisted bug triage",
    "automated_tests": "automated test suite",
    "code_review": "peer code review",
    "ci_pipeline": "continuous integration pipeline",
    "automated_deploys": "automated deploys",
    "dependency_scanning": "dependency and vulnerability scanning",
    "error_monitoring": "error monitoring and alerting",
}


class _AxisSpec(BaseModel):
    heading: str
    practices: list[str]
    service: ServiceOffering
    gap_action: str
    gap_rationale: str
    strength_action: str
    strength_rationale: str


_AXES: dict[DiagnosisAxis, _AxisSpec] = {
    DiagnosisAxis.AI_DEVELOPMENT: _AxisSpec(
        heading="Continuous AI-assisted development",
        practices=["ai_assisted_coding"],
        service=ServiceOffering.AI_ANALYSIS,
        gap_action="Introduce an AI-first development loop and train the team on it",
        gap_rationale=(
            "No AI assistance was reported in the daily development loop, which is where "
            "the largest and fastest gains sit."
        ),
        strength_action="Measure and standardise the existing AI-assisted workflow",
        strength_rationale=(
            "AI assistance is already in use; the next gain comes from making it consistent "
            "across the team rather than from adopting more tools."
        ),
    ),
    DiagnosisAxis.AI_QUALITY: _AxisSpec(
        heading="Bug management and quality with AI",
        practices=["ai_bug_triage", "automated_tests", "code_review"],
        service=ServiceOffering.AI_PROJECT_MANAGER,
        gap_action="Automate bug triage and regression coverage with AI-assisted workflows",
        gap_rationale=(
            "Defects are handled manually, so the cost of every bug is paid twice: once in "
            "triage and once in the fix."
        ),
        strength_action="Extend the existing quality practice with AI triage and prioritisation",
        strength_rationale=(
            "Quality practices are in place; AI can now cut the time between a defect "
            "appearing and the right person seeing it."
        ),
    ),
    DiagnosisAxis.DELIVERY_AUTOMATION: _AxisSpec(
        heading="CI/CD and automated deployment",
        practices=["ci_pipeline", "automated_deploys"],
        service=ServiceOffering.DEVOPS_AI,
        gap_action="Build an AI-assisted CI/CD pipeline with automated deploys and rollback",
        gap_rationale=(
            "Releases depend on manual steps, which makes them rare, risky and hard to "
            "reverse when something breaks."
        ),
        strength_action="Harden the pipeline with automated rollback and release gates",
        strength_rationale=(
            "Delivery is already automated; the remaining risk is what happens when a bad "
            "release reaches production."
        ),
    ),
    DiagnosisAxis.SECURITY_DEPENDENCIES: _AxisSpec(
        heading="Security and dependency management",
        practices=["dependency_scanning"],
        service=ServiceOffering.CTO_AS_A_SERVICE,
        gap_action="Put continuous dependency and vulnerability scanning in the pipeline",
        gap_rationale=(
            "Nothing reported watches third-party dependencies, which is where most "
            "exploitable risk enters a modern codebase."
        ),
        strength_action="Turn scanning results into an owned, prioritised remediation backlog",
        strength_rationale=(
            "Scanning exists; value now comes from deciding what actually gets fixed and "
            "when, which is an architecture and ownership question."
        ),
    ),
    DiagnosisAxis.OBSERVABILITY: _AxisSpec(
        heading="Observability and operational feedback",
        practices=["error_monitoring"],
        service=ServiceOffering.DEVOPS_AI,
        gap_action="Add error monitoring and actionable alerting across environments",
        gap_rationale=(
            "Without monitoring, production problems are reported by users before they are "
            "seen by the team."
        ),
        strength_action="Tune alerting so it reflects user impact rather than raw error volume",
        strength_rationale=(
            "Monitoring is in place; the next step is making alerts mean something so they "
            "stop being ignored."
        ),
    ),
}

_UNAVAILABLE_SITE_EVIDENCE = "Website: not analysed (the page could not be read)"


def _practice_evidence(axis: DiagnosisAxis, reported: set[str], locale: str) -> list[str]:
    spec = _AXES[axis]
    labels = PRACTICE_LABELS[locale]
    copy = TEMPLATE_COPY[locale]
    present = [labels[p] for p in spec.practices if p in reported]
    absent = [labels[p] for p in spec.practices if p not in reported]

    evidence = []
    if present:
        evidence.append(copy["evidence_present"].format(items=", ".join(present)))
    if absent:
        evidence.append(copy["evidence_absent"].format(items=", ".join(absent)))
    return evidence


def _site_evidence(axis: DiagnosisAxis, site: SiteSignals, locale: str) -> list[str]:
    """Site facts attached to the axis they inform. Only measured values appear."""
    if not site.available:
        # Only the axes that would have used site data say so, to avoid repeating
        # the same line five times.
        if axis in {
            DiagnosisAxis.AI_DEVELOPMENT,
            DiagnosisAxis.DELIVERY_AUTOMATION,
            DiagnosisAxis.SECURITY_DEPENDENCIES,
            DiagnosisAxis.OBSERVABILITY,
        }:
            return [TEMPLATE_COPY[locale]["evidence_site_unavailable"]]
        return []

    def presence(value: bool | None) -> str:
        return "present" if value else "absent"

    if axis is DiagnosisAxis.AI_DEVELOPMENT and site.framework:
        return [TEMPLATE_COPY[locale]["evidence_framework"].format(framework=site.framework)]

    if axis is DiagnosisAxis.DELIVERY_AUTOMATION:
        return [
            "Shipped page metadata — "
            f"title: {presence(site.title)}, "
            f"description: {presence(site.description)}, "
            f"canonical: {presence(site.canonical)}, "
            f"robots.txt: {presence(site.robots_txt)}, "
            f"sitemap: {presence(site.sitemap)}"
        ]

    if axis is DiagnosisAxis.SECURITY_DEPENDENCIES:
        copy = TEMPLATE_COPY[locale]
        evidence = [copy["evidence_https_on"] if site.https else copy["evidence_https_off"]]
        if site.security_headers:
            evidence.append(f"Security headers present: {', '.join(site.security_headers)}")
        if site.missing_security_headers:
            evidence.append(
                copy["evidence_missing_headers"].format(
                    items=", ".join(site.missing_security_headers)
                )
            )
        return evidence

    if axis is DiagnosisAxis.OBSERVABILITY:
        evidence = []
        if site.page_weight_bytes is not None:
            evidence.append(f"Home page weight: {site.page_weight_bytes / 1000:.0f} kB")
        if site.resource_count is not None:
            evidence.append(f"Requests on first load: {site.resource_count}")
        return evidence

    return []


def _priority_for(axis: DiagnosisAxis, reported: set[str], site: SiteSignals) -> Priority:
    spec = _AXES[axis]
    covered = sum(1 for practice in spec.practices if practice in reported)

    if covered == 0:
        return Priority.HIGH

    # A measured, missing security header outranks a self-reported practice:
    # it is evidence over claim.
    if (
        axis is DiagnosisAxis.SECURITY_DEPENDENCIES
        and site.available
        and site.missing_security_headers
    ):
        return Priority.HIGH

    return Priority.LOW if covered == len(spec.practices) else Priority.MEDIUM


class TemplateReportGenerator:
    """Deterministic generator: same facts in, byte-identical report out.

    This is the default and the only implementation exercised by tests, so the
    whole flow is verifiable with no model, no key and no network.
    """

    name = "template"

    async def generate(self, facts: ReportFacts) -> ContactReport:
        reported = {practice.strip() for practice in facts.workflow.practices if practice.strip()}
        locale = resolve_locale(facts.locale)
        axis_copy = AXIS_COPY[locale]
        copy = TEMPLATE_COPY[locale]

        sections: list[ReportSection] = []
        recommendations: list[Recommendation] = []

        for axis, spec in _AXES.items():
            evidence = _practice_evidence(axis, reported, locale) + _site_evidence(
                axis, facts.site, locale
            )
            priority = _priority_for(axis, reported, facts.site)
            is_gap = priority is Priority.HIGH

            texts = axis_copy[axis.value]
            rationale = texts["gap_rationale"] if is_gap else texts["strength_rationale"]

            sections.append(
                ReportSection(
                    axis=axis,
                    heading=texts["heading"],
                    diagnosis=rationale,
                    evidence=evidence,
                )
            )
            recommendations.append(
                Recommendation(
                    axis=axis,
                    action=texts["gap_action"] if is_gap else texts["strength_action"],
                    rationale=rationale,
                    service=spec.service,
                    priority=priority,
                )
            )

        # Stable order: urgency first, then the fixed axis order — never insertion
        # luck, or two identical inputs could produce two different documents.
        axis_order = list(_AXES)
        recommendations.sort(key=lambda r: (r.priority.rank, axis_order.index(r.axis)))

        return ContactReport(
            title=copy["title"].format(company=facts.company),
            summary=self._summary(facts, recommendations, locale),
            sections=sections,
            recommendations=recommendations,
            generator=self.name,
        )

    @staticmethod
    def _summary(facts: ReportFacts, recommendations: list[Recommendation], locale: str) -> str:
        copy = TEMPLATE_COPY[locale]
        urgent = [r for r in recommendations if r.priority is Priority.HIGH]

        if facts.site.available and facts.site.url:
            site_clause = copy["summary_with_url"].format(url=facts.site.url)
        elif facts.site.available:
            # available=True means the page WAS read: claiming otherwise would tell
            # the lead we could not look at a site we did look at.
            site_clause = copy["summary_site_analysed"]
        else:
            site_clause = copy["summary_no_site"]

        parts = [
            copy["summary_opening"].format(name=facts.contact_name, company=facts.company)
            + site_clause
        ]

        if facts.workflow.team_size:
            parts.append(copy["summary_team_size"].format(team_size=facts.workflow.team_size))

        parts.append(
            copy["summary_priorities"].format(count=len(urgent))
            if urgent
            else copy["summary_all_good"]
        )

        if facts.workflow.notes:
            # Quoted verbatim, never paraphrased: it is the visitor's own account.
            parts.append(copy["summary_notes"].format(notes=facts.workflow.notes))

        return " ".join(parts)


def build_report_generator(
    name: str,
    *,
    model_api_key: str = "",
    model_name: str = "",
) -> ReportGenerator:
    """Select the generator by name. Unknown or unusable values raise."""
    selected = (name or STUB_GENERATOR).strip().lower()

    if selected == STUB_GENERATOR:
        return TemplateReportGenerator()

    if selected == GEMINI_GENERATOR:
        if not model_api_key:
            raise UnusableReportGenerator(
                "REPORT_GENERATOR=gemini requires GEMINI_API_KEY to be set"
            )

        # Imported here so the module stays importable without httpx present and
        # so selecting the stub never pulls the model path in.
        from app.services.report_gemini import GeminiReportGenerator

        return GeminiReportGenerator(api_key=model_api_key, model=model_name)

    if selected == GENKIT_GENERATOR:
        if not model_api_key:
            raise UnusableReportGenerator(
                "REPORT_GENERATOR=genkit requires GEMINI_API_KEY to be set"
            )
        # The dependency lands in a later phase (F). Failing here is deliberate:
        # a silent fallback would email a template report as if a model wrote it.
        # Deliberately still refuses. The Genkit plugin for Gemini pulls 137MB of
        # google/ and grpc/, which does not fit Vercel's Python function ceiling
        # (ADR 0004, measured). Use `gemini`, which speaks the same API over REST.
        raise UnusableReportGenerator(
            "REPORT_GENERATOR=genkit is not supported: the Genkit Gemini plugin does not fit "
            "the deployment's bundle limit. Use REPORT_GENERATOR=gemini instead."
        )

    raise UnusableReportGenerator(
        f"Unknown REPORT_GENERATOR value: {name!r}. Valid values: "
        f"{STUB_GENERATOR!r}, {GEMINI_GENERATOR!r}"
    )
