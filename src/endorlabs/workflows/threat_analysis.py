"""Threat model analysis via LLM sub-agent.

Spawns a single LLM call per project to produce a structured threat model
from pre-loaded security context (findings, policies, dependencies, call
graphs).  The result is written to the session directory and fed as
additional context to the main conversational agent.

Experimental: API may change without the same stability guarantees
as the rest of the SDK.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from .common import WorkflowResult

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Prompt template
# ---------------------------------------------------------------------------

THREAT_MODEL_PROMPT = """\
You are a world-class application security expert.  You have been given
a complete security analysis of **{project_name}** including:

- Dependency tree and call graph analysis
- {finding_count} security findings across {category_count} categories
- {policy_count} active security policies
- Repository version information

Based on this data, produce a structured threat model.  Be specific and
cite actual package names, CVE IDs, and finding descriptions from the data.

## Required Sections

1. **Component Architecture** — key components inferred from the dependency
   tree and call graph, their roles, and trust boundaries.
2. **Attack Surface** — exposed interfaces, entry points, and data flows
   that an attacker could target.
3. **Risk Assessment** — top 5 risks ranked by severity and exploitability.
   For each risk include the finding ID or CVE, a one-line description,
   severity, and a brief exploitability rationale.
4. **Dependency Risk** — the most concerning direct and transitive
   dependencies, why they are risky, and whether they are reachable
   via call graph analysis.
5. **Policy Coverage** — gaps in the current policy configuration that
   leave blind spots (e.g. missing SAST, no secret scanning policy).
6. **Recommendations** — top 3 actionable improvements ordered by
   impact-to-effort ratio.

---

{context_markdown}
"""


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------


@dataclass
class ThreatModelResult(WorkflowResult):
    """Result from a threat-model sub-agent analysis.

    Attributes:
        project_name: Repository / project name analysed.
        report: The full Markdown threat-model report.
        risk_count: Number of risks identified in the assessment section.
    """

    project_name: str = ""
    report: str = ""
    risk_count: int = 0


# ---------------------------------------------------------------------------
# Core analysis function
# ---------------------------------------------------------------------------


def _extract_first_int(line: str) -> int:
    """Return the first integer token found in *line*, or ``0``."""
    for token in line.split():
        cleaned = token.strip("*:,")
        if cleaned.isdigit():
            return int(cleaned)
    return 0


def _count_category_rows(lines: list[str]) -> int:
    """Count data rows in the first ``| Category |`` Markdown table."""
    count = 0
    in_table = False
    for line in lines:
        if "| Category |" in line:
            in_table = True
            continue
        if in_table:
            if line.startswith(("|--", "| --")):
                continue
            if line.startswith("| "):
                count += 1
            else:
                break
    return count


def _count_metrics(context_markdown: str) -> dict[str, int]:
    """Extract rough counts from the context markdown for prompt injection."""
    finding_count = 0
    policy_count = 0
    lines = context_markdown.splitlines()

    for line in lines:
        lower = line.lower()
        if "total findings" in lower:
            finding_count = _extract_first_int(line)
        elif "total policies" in lower or "policies**:" in lower:
            policy_count = _extract_first_int(line)

    return {
        "finding_count": finding_count,
        "category_count": max(_count_category_rows(lines), 1),
        "policy_count": policy_count,
    }


def analyze_project_threat_model(
    llm: Any,
    project_name: str,
    context_markdown: str,
) -> ThreatModelResult:
    """Run the appsec sub-agent to produce a threat model.

    This performs a *single* LLM call (not a multi-step graph) with the
    full project context injected into the prompt.

    Args:
        llm: A LangChain ``BaseChatModel`` instance (e.g. Gemini, GPT-4).
        project_name: Human-readable project name / URL.
        context_markdown: Combined Markdown context from session_context
            and dependency_explorer.

    Returns:
        :class:`ThreatModelResult` containing the Markdown report.
    """
    metrics = _count_metrics(context_markdown)

    prompt_text = THREAT_MODEL_PROMPT.format(
        project_name=project_name,
        finding_count=metrics["finding_count"],
        category_count=metrics["category_count"],
        policy_count=metrics["policy_count"],
        context_markdown=context_markdown,
    )

    try:
        response = llm.invoke(prompt_text)
        report = (
            str(response.content) if hasattr(response, "content") else str(response)
        )
    except Exception as exc:
        logger.error(
            "Unable to complete threat model analysis for '%s': %s",
            project_name,
            exc,
        )
        return ThreatModelResult(
            status="error",
            message=f"Unable to complete threat model: {exc}",
            errors=[str(exc)],
            project_name=project_name,
        )

    # Count risks (look for numbered items in Risk Assessment section)
    risk_count = 0
    in_risk_section = False
    for line in report.splitlines():
        if "risk assessment" in line.lower():
            in_risk_section = True
            continue
        if in_risk_section:
            stripped = line.strip()
            if stripped and stripped[0].isdigit() and "." in stripped[:4]:
                risk_count += 1
            if stripped.startswith("##") and "risk assessment" not in stripped.lower():
                in_risk_section = False

    return ThreatModelResult(
        status="success",
        message=f"Threat model for {project_name}: {risk_count} risks identified",
        project_name=project_name,
        report=report,
        risk_count=risk_count,
    )
