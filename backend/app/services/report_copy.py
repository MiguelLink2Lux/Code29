"""Localised copy for the template report.

The chat asks in Spanish, so a Spanish visitor must not receive an English
report. Text lives here rather than inline in `report.py` so the two languages
sit side by side and a missing translation is visible — `test_report_locale.py`
asserts parity rather than trusting review.

The Gemini connector does not use this module: it instructs the model to write
in the visitor's language directly.
"""

from __future__ import annotations

# Axis keys are plain strings, not the DiagnosisAxis enum: importing it here
# would close a cycle (report -> report_copy -> report). DiagnosisAxis is a
# StrEnum, so its members hash and compare equal to these keys.
SUPPORTED_LOCALES = ("es", "en")
FALLBACK_LOCALE = "es"


def resolve_locale(locale: str | None) -> str:
    """Known locale, or the fallback. Never raises: an odd value must not 500."""
    candidate = (locale or "").strip().lower()

    return candidate if candidate in SUPPORTED_LOCALES else FALLBACK_LOCALE


PRACTICE_LABELS: dict[str, dict[str, str]] = {
    "es": {
        "ai_assisted_coding": "programación asistida por IA en el día a día",
        "ai_bug_triage": "triaje de bugs asistido por IA",
        "automated_tests": "suite de tests automáticos",
        "code_review": "revisión de código entre pares",
        "ci_pipeline": "pipeline de integración continua",
        "automated_deploys": "despliegues automatizados",
        "dependency_scanning": "escaneo de dependencias y vulnerabilidades",
        "error_monitoring": "monitorización de errores y alertado",
    },
    "en": {
        "ai_assisted_coding": "AI-assisted coding in the daily loop",
        "ai_bug_triage": "AI-assisted bug triage",
        "automated_tests": "automated test suite",
        "code_review": "peer code review",
        "ci_pipeline": "continuous integration pipeline",
        "automated_deploys": "automated deploys",
        "dependency_scanning": "dependency and vulnerability scanning",
        "error_monitoring": "error monitoring and alerting",
    },
}

AXIS_COPY: dict[str, dict[str, dict[str, str]]] = {
    "es": {
        "ai_development": {
            "heading": "Desarrollo continuo asistido por IA",
            "gap_action": "Implantar un flujo de desarrollo AI-First y capacitar al equipo",
            "gap_rationale": (
                "No se reporta asistencia de IA en el ciclo diario de desarrollo, que es "
                "donde están las mejoras más grandes y más rápidas."
            ),
            "strength_action": "Medir y estandarizar el flujo asistido por IA que ya usáis",
            "strength_rationale": (
                "Ya usáis asistencia de IA; la siguiente mejora viene de hacerla consistente "
                "en todo el equipo, no de adoptar más herramientas."
            ),
        },
        "ai_quality": {
            "heading": "Gestión de bugs y calidad con IA",
            "gap_action": "Automatizar el triaje de bugs y la cobertura de regresión con IA",
            "gap_rationale": (
                "Los defectos se gestionan a mano, así que cada bug se paga dos veces: una "
                "en el triaje y otra en el arreglo."
            ),
            "strength_action": (
                "Ampliar la práctica de calidad actual con triaje y por IA "
                "priorización"
            ),
            "strength_rationale": (
                "Las prácticas de calidad están puestas; la IA puede ahora recortar el tiempo "
                "entre que aparece un defecto y lo ve quien debe arreglarlo."
            ),
        },
        "delivery_automation": {
            "heading": "CI/CD y despliegue automatizado",
            "gap_action": (
                "Construir un pipeline CI/CD asistido por IA con despliegue y "
                "rollback automáticos"
            ),
            "gap_rationale": (
                "Las releases dependen de pasos manuales, lo que las hace poco frecuentes, "
                "arriesgadas y difíciles de revertir cuando algo se rompe."
            ),
            "strength_action": "Endurecer el pipeline con rollback automático y puertas de release",
            "strength_rationale": (
                "La entrega ya está automatizada; el riesgo que queda es qué pasa cuando una "
                "release defectuosa llega a producción."
            ),
        },
        "security_dependencies": {
            "heading": "Seguridad y gestión de dependencias",
            "gap_action": (
                "Meter escaneo continuo de dependencias y vulnerabilidades en el "
                "pipeline"
            ),
            "gap_rationale": (
                "Nada de lo reportado vigila las dependencias de terceros, que es por donde "
                "entra la mayor parte del riesgo explotable en un código moderno."
            ),
            "strength_action": (
                "Convertir los resultados del escaneo en un backlog y con "
                "priorizado dueño"
            ),
            "strength_rationale": (
                "El escaneo existe; el valor está ahora en decidir qué se arregla de verdad y "
                "cuándo, que es una cuestión de arquitectura y de propiedad."
            ),
        },
        "observability": {
            "heading": "Observabilidad y retroalimentación operativa",
            "gap_action": (
                "Añadir monitorización de errores y alertado accionable en todos "
                "los entornos"
            ),
            "gap_rationale": (
                "Sin monitorización, los problemas de producción los reportan los usuarios "
                "antes de que los vea el equipo."
            ),
            "strength_action": (
                "Afinar el alertado para que refleje impacto en usuario, no "
                "volumen de errores"
            ),
            "strength_rationale": (
                "La monitorización está puesta; el siguiente paso es que las alertas "
                "signifiquen algo para que dejen de ignorarse."
            ),
        },
    },
    "en": {
        "ai_development": {
            "heading": "Continuous AI-assisted development",
            "gap_action": "Introduce an AI-first development loop and train the team on it",
            "gap_rationale": (
                "No AI assistance was reported in the daily development loop, which is where "
                "the largest and fastest gains sit."
            ),
            "strength_action": "Measure and standardise the existing AI-assisted workflow",
            "strength_rationale": (
                "AI assistance is already in use; the next gain comes from making it "
                "consistent across the team rather than from adopting more tools."
            ),
        },
        "ai_quality": {
            "heading": "Bug management and quality with AI",
            "gap_action": "Automate bug triage and regression coverage with AI-assisted workflows",
            "gap_rationale": (
                "Defects are handled manually, so the cost of every bug is paid twice: once "
                "in triage and once in the fix."
            ),
            "strength_action": (
                "Extend the existing quality practice with AI triage and "
                "prioritisation"
            ),
            "strength_rationale": (
                "Quality practices are in place; AI can now cut the time between a defect "
                "appearing and the right person seeing it."
            ),
        },
        "delivery_automation": {
            "heading": "CI/CD and automated deployment",
            "gap_action": "Build an AI-assisted CI/CD pipeline with automated deploys and rollback",
            "gap_rationale": (
                "Releases depend on manual steps, which makes them rare, risky and hard to "
                "reverse when something breaks."
            ),
            "strength_action": "Harden the pipeline with automated rollback and release gates",
            "strength_rationale": (
                "Delivery is already automated; the remaining risk is what happens when a bad "
                "release reaches production."
            ),
        },
        "security_dependencies": {
            "heading": "Security and dependency management",
            "gap_action": "Put continuous dependency and vulnerability scanning in the pipeline",
            "gap_rationale": (
                "Nothing reported watches third-party dependencies, which is where most "
                "exploitable risk enters a modern codebase."
            ),
            "strength_action": (
                "Turn scanning results into an owned, prioritised remediation "
                "backlog"
            ),
            "strength_rationale": (
                "Scanning exists; value now comes from deciding what actually gets fixed and "
                "when, which is an architecture and ownership question."
            ),
        },
        "observability": {
            "heading": "Observability and operational feedback",
            "gap_action": "Add error monitoring and actionable alerting across environments",
            "gap_rationale": (
                "Without monitoring, production problems are reported by users before they "
                "are seen by the team."
            ),
            "strength_action": (
                "Tune alerting so it reflects user impact rather than raw "
                "error volume"
            ),
            "strength_rationale": (
                "Monitoring is in place; the next step is making alerts mean something so "
                "they stop being ignored."
            ),
        },
    },
}

# Sentences the report assembles around the axis copy.
TEMPLATE_COPY: dict[str, dict[str, str]] = {
    "es": {
        "title": "Diagnóstico de flujo de trabajo — {company}",
        "summary_opening": (
            "{name}, este diagnóstico de {company} se basa en las respuestas del chat"
        ),
        "summary_with_url": " y en señales medidas de {url}.",
        "summary_site_analysed": " y en señales medidas de la portada.",
        "summary_no_site": ", ya que no se pudo analizar la web.",
        "summary_team_size": "Tamaño de equipo reportado: {team_size}.",
        "summary_priorities": "{count} de 5 áreas necesitan atención prioritaria.",
        "summary_all_good": "Las cinco áreas están cubiertas; las mejoras son de refinamiento.",
        "summary_notes": 'En sus palabras: "{notes}"',
        "evidence_present": "En uso: {items}",
        "evidence_absent": "No reportado: {items}",
        "evidence_https_on": "HTTPS: activado",
        "evidence_https_off": "HTTPS: no activado",
        "evidence_missing_headers": "Cabeceras de seguridad ausentes: {items}",
        "evidence_framework": "Stack detectado en la portada: {framework}",
        "evidence_no_sitemap": "No se encontró sitemap.xml",
        "evidence_site_unavailable": "Web: no analizada (no se pudo leer la página)",
        "generator": "plantilla",
    },
    "en": {
        "title": "Workflow assessment — {company}",
        "summary_opening": (
            "{name}, this assessment of {company} is based on the answers given in the chat"
        ),
        "summary_with_url": " and on signals measured from {url}.",
        "summary_site_analysed": " and on signals measured from the home page.",
        "summary_no_site": ", since the website could not be analysed.",
        "summary_team_size": "Team size reported: {team_size}.",
        "summary_priorities": "{count} of 5 areas need attention first.",
        "summary_all_good": "All five areas are covered; the gains left are refinements.",
        "summary_notes": 'In their words: "{notes}"',
        "evidence_present": "Reported in place: {items}",
        "evidence_absent": "Not reported: {items}",
        "evidence_https_on": "HTTPS: enabled",
        "evidence_https_off": "HTTPS: not enabled",
        "evidence_missing_headers": "Missing security headers: {items}",
        "evidence_framework": "Stack detected on the home page: {framework}",
        "evidence_no_sitemap": "No sitemap.xml found",
        "evidence_site_unavailable": "Website: not analysed (the page could not be read)",
        "generator": "template",
    },
}
