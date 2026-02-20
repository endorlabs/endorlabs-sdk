"""Session context loader for interactive CLI demos.

Pulls per-project context (findings, policies, repository versions,
dependencies, call graphs) from the Endor Labs API and writes
structured artifacts into a progressive-disclosure directory tree
under ``.endorlabs-context/session-<user>/``.

Experimental: API may change without the same stability guarantees
as the rest of the SDK.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from io import StringIO
from pathlib import Path
from typing import TYPE_CHECKING, Any

from .common import WorkflowResult

if TYPE_CHECKING:
    from endorlabs import Client

from endorlabs.utils.logging_config import get_resource_logger

logger = get_resource_logger(__name__)

# Finding categories used for the "by scan type" summary
_FINDING_CATEGORIES = [
    "FINDING_CATEGORY_VULNERABILITY",
    "FINDING_CATEGORY_SAST",
    "FINDING_CATEGORY_SECRETS",
    "FINDING_CATEGORY_CICD",
]

_SEVERITY_LEVELS = [
    "FINDING_LEVEL_CRITICAL",
    "FINDING_LEVEL_HIGH",
    "FINDING_LEVEL_MEDIUM",
    "FINDING_LEVEL_LOW",
]

_SEVERITY_SHORT = {
    "FINDING_LEVEL_CRITICAL": "Critical",
    "FINDING_LEVEL_HIGH": "High",
    "FINDING_LEVEL_MEDIUM": "Medium",
    "FINDING_LEVEL_LOW": "Low",
}

_CATEGORY_SHORT = {
    "FINDING_CATEGORY_VULNERABILITY": "VULNERABILITY",
    "FINDING_CATEGORY_SAST": "SAST",
    "FINDING_CATEGORY_SECRETS": "SECRETS",
    "FINDING_CATEGORY_CICD": "CI_CD",
    "FINDING_CATEGORY_GHACTIONS": "GH_ACTIONS",
    "FINDING_CATEGORY_OPERATIONAL": "OPERATIONAL",
    "FINDING_CATEGORY_SCA": "SCA",
    "FINDING_CATEGORY_SCPM": "SCPM",
    "FINDING_CATEGORY_SECURITY": "SECURITY",
}


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------


@dataclass
class FindingsContext:
    """Findings data for a single project."""

    project_uuid: str = ""
    project_name: str = ""
    total: int = 0
    by_category: dict[str, dict[str, int]] = field(default_factory=dict)
    top_findings: list[dict[str, Any]] = field(default_factory=list)
    raw_findings: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class PoliciesContext:
    """Policies data for a project's namespace."""

    namespace: str = ""
    total: int = 0
    policies: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class VersionsContext:
    """Repository version data for a single project."""

    project_uuid: str = ""
    total: int = 0
    versions: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class SessionResult(WorkflowResult):
    """Result from a full session context pull.

    Attributes:
        user: Resolved user identity (from whoami).
        session_dir: Path to the session output directory.
        findings: Findings context for the project.
        policies: Policies context for the project's namespace.
        versions: Repository versions context.
    """

    user: str = ""
    session_dir: str = ""
    findings: FindingsContext = field(default_factory=FindingsContext)
    policies: PoliciesContext = field(default_factory=PoliciesContext)
    versions: VersionsContext = field(default_factory=VersionsContext)


# ---------------------------------------------------------------------------
# Context pulling functions
# ---------------------------------------------------------------------------


def pull_findings_context(
    client: Client,
    project: Any,
    *,
    max_pages: int = 5,
) -> FindingsContext:
    """Pull findings for a project, grouped by scan type and severity.

    Args:
        client: Authenticated Endor Labs Client.
        project: Project resource object.
        max_pages: Max pages to fetch.

    Returns:
        :class:`FindingsContext` with aggregated data.
    """
    project_uuid = project.uuid
    project_name = project.meta.name if project.meta else project_uuid
    project_ns = (
        project.tenant_meta.namespace
        if project.tenant_meta and project.tenant_meta.namespace
        else None
    )

    ctx = FindingsContext(project_uuid=project_uuid, project_name=project_name)

    try:
        list_kwargs: dict[str, Any] = {
            "filter": f'spec.project_uuid=="{project_uuid}"',
            "max_pages": max_pages,
            "page_size": 100,
        }
        if project_ns:
            list_kwargs["namespace"] = project_ns

        findings = client.finding.list(**list_kwargs)
    except Exception as exc:
        logger.warning("Unable to fetch findings: %s", exc)
        return ctx

    ctx.total = len(findings)

    # Build the by-category-and-severity matrix
    for cat in _FINDING_CATEGORIES:
        cat_short = _CATEGORY_SHORT.get(cat, cat)
        ctx.by_category[cat_short] = {
            _SEVERITY_SHORT[sev]: 0 for sev in _SEVERITY_LEVELS
        }
        ctx.by_category[cat_short]["Total"] = 0

    for f in findings:
        raw_level = f.spec.level if f.spec and f.spec.level else ""
        # Handle enum or string values
        level = raw_level.value if hasattr(raw_level, "value") else str(raw_level)
        raw_cats = (
            f.spec.finding_categories if f.spec and f.spec.finding_categories else []
        )
        if isinstance(raw_cats, str):
            raw_cats = [raw_cats]
        categories = [c.value if hasattr(c, "value") else str(c) for c in raw_cats]

        sev_short = _SEVERITY_SHORT.get(level, "")

        for cat in categories:
            cat_short = _CATEGORY_SHORT.get(cat, cat)
            if cat_short not in ctx.by_category:
                ctx.by_category[cat_short] = {
                    _SEVERITY_SHORT[s]: 0 for s in _SEVERITY_LEVELS
                }
                ctx.by_category[cat_short]["Total"] = 0
            if sev_short and sev_short in ctx.by_category[cat_short]:
                ctx.by_category[cat_short][sev_short] += 1
            ctx.by_category[cat_short]["Total"] += 1

        # Collect raw data (masked to key fields)
        finding_dict: dict[str, Any] = {
            "uuid": f.uuid,
            "description": f.meta.description if f.meta else "",
            "level": level,
            "categories": categories,
        }
        if f.spec:
            finding_dict["target_dependency"] = getattr(
                f.spec, "target_dependency_package_name", None
            )
            finding_dict["summary"] = getattr(f.spec, "summary", "")
        ctx.raw_findings.append(finding_dict)

    # Top critical/high findings
    for f_dict in ctx.raw_findings:
        if f_dict.get("level") in (
            "FINDING_LEVEL_CRITICAL",
            "FINDING_LEVEL_HIGH",
        ):
            ctx.top_findings.append(f_dict)
    ctx.top_findings = ctx.top_findings[:20]

    return ctx


def pull_policies_context(
    client: Client,
    project: Any,
    *,
    max_pages: int = 3,
) -> PoliciesContext:
    """Pull policies from the project's namespace.

    Args:
        client: Authenticated Endor Labs Client.
        project: Project resource object.
        max_pages: Max pages to fetch.

    Returns:
        :class:`PoliciesContext` with policy data.
    """
    project_ns = (
        project.tenant_meta.namespace
        if project.tenant_meta and project.tenant_meta.namespace
        else None
    )
    ctx = PoliciesContext(namespace=project_ns or "")

    try:
        list_kwargs: dict[str, Any] = {
            "max_pages": max_pages,
            "page_size": 100,
        }
        if project_ns:
            list_kwargs["namespace"] = project_ns

        policies = client.policy.list(**list_kwargs)
    except Exception as exc:
        logger.warning("Unable to fetch policies: %s", exc)
        return ctx

    ctx.total = len(policies)
    for p in policies:
        policy_dict: dict[str, Any] = {
            "uuid": p.uuid,
            "name": p.meta.name if p.meta else "",
            "description": p.meta.description if p.meta else "",
        }
        if p.spec:
            policy_dict["disabled"] = getattr(p.spec, "disabled", None)
            policy_dict["policy_type"] = str(getattr(p.spec, "policy_type", ""))
            action = getattr(p.spec, "action", None)
            policy_dict["action"] = str(action) if action else ""
        ctx.policies.append(policy_dict)

    return ctx


def pull_repository_versions_context(
    client: Client,
    project: Any,
    *,
    max_pages: int = 2,
) -> VersionsContext:
    """Pull repository versions for a project.

    Args:
        client: Authenticated Endor Labs Client.
        project: Project resource object.
        max_pages: Max pages to fetch.

    Returns:
        :class:`VersionsContext` with version data.
    """
    project_uuid = project.uuid
    project_ns = (
        project.tenant_meta.namespace
        if project.tenant_meta and project.tenant_meta.namespace
        else None
    )
    ctx = VersionsContext(project_uuid=project_uuid)

    try:
        list_kwargs: dict[str, Any] = {
            "filter": (
                f'meta.parent_uuid=="{project_uuid}" and meta.parent_kind=="Project"'
            ),
            "max_pages": max_pages,
            "page_size": 100,
        }
        if project_ns:
            list_kwargs["namespace"] = project_ns

        versions = client.repository_version.list(**list_kwargs)
    except Exception as exc:
        logger.warning("Unable to fetch repository versions: %s", exc)
        return ctx

    ctx.total = len(versions)
    for v in versions:
        ver_dict: dict[str, Any] = {
            "uuid": v.uuid,
            "name": v.meta.name if v.meta else "",
        }
        if v.spec:
            version_info = getattr(v.spec, "version", None)
            if version_info:
                ver_dict["ref"] = getattr(version_info, "ref", "")
                ver_dict["sha"] = getattr(version_info, "sha", "")
            ver_dict["last_commit_date"] = str(getattr(v.spec, "last_commit_date", ""))
        ctx.versions.append(ver_dict)

    return ctx


# ---------------------------------------------------------------------------
# Markdown renderers
# ---------------------------------------------------------------------------


def render_findings_summary(ctx: FindingsContext) -> str:
    """Render ``findings-summary.md`` content."""
    buf = StringIO()
    buf.write(f"# Findings Summary \u2014 {ctx.project_name}\n\n")

    if ctx.total == 0:
        buf.write("No findings found for this project.\n")
        return buf.getvalue()

    buf.write(f"**Total findings**: {ctx.total}\n\n")

    # By scan type table
    buf.write("## By Scan Type\n\n")
    buf.write("| Category | Critical | High | Medium | Low | Total |\n")
    buf.write("|----------|----------|------|--------|-----|-------|\n")
    for cat_name, counts in sorted(ctx.by_category.items()):
        buf.write(
            f"| {cat_name} | {counts.get('Critical', 0)} "
            f"| {counts.get('High', 0)} | {counts.get('Medium', 0)} "
            f"| {counts.get('Low', 0)} | {counts.get('Total', 0)} |\n"
        )
    buf.write("\n")

    # Top critical/high findings
    if ctx.top_findings:
        buf.write("## Top Critical/High Findings\n\n")
        for f_dict in ctx.top_findings:
            level = f_dict.get("level", "").replace("FINDING_LEVEL_", "")
            desc = f_dict.get("description", "") or f_dict.get("summary", "")
            cats = f_dict.get("categories", [])
            cat_str = ", ".join(_CATEGORY_SHORT.get(c, c) for c in cats)
            buf.write(f"- `{f_dict.get('uuid', '')}` {desc} ({level}, {cat_str})\n")
        buf.write("\n")

    ts = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    buf.write(f"---\n\n*Generated at {ts}*\n")
    return buf.getvalue()


def render_policies_summary(ctx: PoliciesContext) -> str:
    """Render ``policies-summary.md`` content."""
    buf = StringIO()
    buf.write(f"# Policies Summary \u2014 {ctx.namespace}\n\n")

    if ctx.total == 0:
        buf.write("No policies found in this namespace.\n")
        return buf.getvalue()

    buf.write(f"**Total policies**: {ctx.total}\n\n")
    buf.write("| Name | Type | Enabled | Action |\n")
    buf.write("|------|------|---------|--------|\n")
    for p in ctx.policies:
        name = p.get("name", "")
        ptype = str(p.get("policy_type", "")).replace("POLICY_TYPE_", "")
        disabled = p.get("disabled", False)
        enabled = "No" if disabled else "Yes"
        action = str(p.get("action", "")).replace("POLICY_ACTION_", "")
        buf.write(f"| {name} | {ptype} | {enabled} | {action} |\n")
    buf.write("\n")

    ts = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    buf.write(f"---\n\n*Generated at {ts}*\n")
    return buf.getvalue()


def render_versions_summary(ctx: VersionsContext) -> str:
    """Render ``versions-summary.md`` content."""
    buf = StringIO()
    buf.write("# Repository Versions\n\n")

    if ctx.total == 0:
        buf.write("No repository versions found for this project.\n")
        return buf.getvalue()

    buf.write(f"**Total versions**: {ctx.total}\n\n")
    buf.write("| Name | Ref | SHA | Last Commit |\n")
    buf.write("|------|-----|-----|-------------|\n")
    for v in ctx.versions:
        name = v.get("name", "")
        ref = v.get("ref", "")
        sha = v.get("sha", "")
        if sha and len(sha) > 12:
            sha = sha[:12]
        last_commit = v.get("last_commit_date", "")
        buf.write(f"| {name} | {ref} | `{sha}` | {last_commit} |\n")
    buf.write("\n")

    ts = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    buf.write(f"---\n\n*Generated at {ts}*\n")
    return buf.getvalue()


def render_project_summary(
    project: Any,
    findings: FindingsContext,
    policies: PoliciesContext,
    versions: VersionsContext,
) -> str:
    """Render the top-level ``project-summary.md``."""
    buf = StringIO()
    project_name = project.meta.name if project.meta else project.uuid
    buf.write(f"# Project Summary \u2014 {project_name}\n\n")

    buf.write("| | |\n|---|---|\n")
    buf.write(f"| Repository | {project_name} |\n")
    buf.write(f"| UUID | `{project.uuid}` |\n")
    ns = (
        project.tenant_meta.namespace
        if project.tenant_meta and project.tenant_meta.namespace
        else ""
    )
    buf.write(f"| Namespace | `{ns}` |\n\n")

    # Quick stats
    buf.write("## Overview\n\n")
    buf.write(f"- **Findings**: {findings.total}\n")
    buf.write(f"- **Policies**: {policies.total}\n")
    buf.write(f"- **Repository Versions**: {versions.total}\n\n")

    # Findings breakdown
    if findings.total > 0:
        buf.write("### Findings by Category\n\n")
        buf.write("| Category | Critical | High | Medium | Low | Total |\n")
        buf.write("|----------|----------|------|--------|-----|-------|\n")
        for cat_name, counts in sorted(findings.by_category.items()):
            buf.write(
                f"| {cat_name} | {counts.get('Critical', 0)} "
                f"| {counts.get('High', 0)} | {counts.get('Medium', 0)} "
                f"| {counts.get('Low', 0)} | {counts.get('Total', 0)} |\n"
            )
        buf.write("\n")

    ts = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    buf.write(f"---\n\n*Generated at {ts}*\n")
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Artifact writer
# ---------------------------------------------------------------------------


def write_session_artifacts(
    session_dir: str | Path,
    project: Any,
    findings: FindingsContext,
    policies: PoliciesContext,
    versions: VersionsContext,
) -> None:
    """Write all session artifacts to the progressive-disclosure directory.

    Creates the directory structure::

        <session_dir>/<project-slug>/
            project-summary.md
            findings/
                findings-summary.md
                findings.json
            policies/
                policies-summary.md
                policies.json
            repository-versions/
                versions-summary.md
                versions.json
    """
    from endorlabs.tools.dependency_explorer import slugify
    from endorlabs.utils.path_safety import safe_write_text

    session_dir = Path(session_dir)
    project_name = project.meta.name if project.meta else project.uuid
    slug = slugify(project_name)
    proj_dir = session_dir / slug

    # -- project-summary.md --
    summary = render_project_summary(project, findings, policies, versions)
    safe_write_text(session_dir, proj_dir / "project-summary.md", summary)

    # -- findings/ --
    findings_dir = proj_dir / "findings"
    safe_write_text(
        session_dir,
        findings_dir / "findings-summary.md",
        render_findings_summary(findings),
    )
    safe_write_text(
        session_dir,
        findings_dir / "findings.json",
        json.dumps(findings.raw_findings, indent=2, default=str, ensure_ascii=False),
    )

    # -- policies/ --
    policies_dir = proj_dir / "policies"
    safe_write_text(
        session_dir,
        policies_dir / "policies-summary.md",
        render_policies_summary(policies),
    )
    safe_write_text(
        session_dir,
        policies_dir / "policies.json",
        json.dumps(policies.policies, indent=2, default=str, ensure_ascii=False),
    )

    # -- repository-versions/ --
    versions_dir = proj_dir / "repository-versions"
    safe_write_text(
        session_dir,
        versions_dir / "versions-summary.md",
        render_versions_summary(versions),
    )
    safe_write_text(
        session_dir,
        versions_dir / "versions.json",
        json.dumps(versions.versions, indent=2, default=str, ensure_ascii=False),
    )

    logger.info("Session artifacts written to %s", proj_dir)


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------


def create_session(
    client: Client,
    project: Any,
    session_dir: str | Path,
) -> SessionResult:
    """Pull all context for a project and write session artifacts.

    This is the main entry point for the session context workflow.
    It fetches findings, policies, and repository versions, then
    writes the progressive-disclosure directory structure.

    Args:
        client: Authenticated Endor Labs Client.
        project: Project resource object.
        session_dir: Root directory for the session output.

    Returns:
        :class:`SessionResult` with overall status and sub-contexts.
    """
    result = SessionResult(session_dir=str(session_dir))
    errors: list[str] = []

    # Pull findings
    project_name = project.meta.name if project.meta else project.uuid
    logger.info("Pulling findings for project '%s' ...", project_name)
    findings = pull_findings_context(client, project)
    result.findings = findings
    if findings.total == 0:
        logger.info("  No findings found for project '%s'", project.uuid)

    # Pull policies
    logger.info("Pulling policies for project '%s' ...", project_name)
    policies = pull_policies_context(client, project)
    result.policies = policies
    if policies.total == 0:
        logger.info("  No policies found in namespace '%s'", policies.namespace)

    # Pull repository versions
    logger.info("Pulling repository versions for project '%s' ...", project_name)
    versions = pull_repository_versions_context(client, project)
    result.versions = versions
    if versions.total == 0:
        logger.info("  No repository versions found for project '%s'", project.uuid)

    # Write artifacts
    try:
        write_session_artifacts(session_dir, project, findings, policies, versions)
    except Exception as exc:
        errors.append(f"Unable to write session artifacts: {exc}")
        logger.error("Unable to write session artifacts: %s", exc)

    result.errors = errors
    result.status = "error" if errors else "success"
    result.message = (
        f"Session context for {project.meta.name if project.meta else project.uuid}: "
        f"{findings.total} findings, {policies.total} policies, "
        f"{versions.total} repository versions"
    )
    return result
