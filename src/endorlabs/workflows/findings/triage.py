"""Finding triage workflows: tag findings and create exception policies.

Provides composable functions for common finding triage operations
on the Endor Labs platform, using the Client facade (not raw HTTP).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from ..common import WorkflowResult

if TYPE_CHECKING:
    from endorlabs import Client

from endorlabs.utils.logging_config import get_resource_logger

logger = get_resource_logger(__name__)


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------


@dataclass
class TaggingResult(WorkflowResult):
    """Result of a finding tagging operation.

    Attributes:
        tagged: Number of findings successfully tagged.
        skipped: Number of findings that already had the tag.
        failed: Number of findings that could not be tagged.
        total: Total number of findings matched by criteria.
    """

    tagged: int = 0
    skipped: int = 0
    failed: int = 0
    total: int = 0


@dataclass
class ExceptionPolicyResult(WorkflowResult):
    """Result of an exception policy creation.

    Attributes:
        uuid: UUID of the created policy (empty on dry-run or failure).
        name: Name of the created policy.
        rego_rule: The generated Rego rule source.
        pattern_type: ``"templated"`` or ``"custom"``.
        package_name: Rego package name (e.g. ``"sast"``, ``"secrets"``).
    """

    uuid: str = ""
    name: str = ""
    rego_rule: str = ""
    pattern_type: str = ""
    package_name: str = ""


# ---------------------------------------------------------------------------
# Rego generation (pure functions — no side effects)
# ---------------------------------------------------------------------------

_REGO_HELPERS_BASE = """\
contains_any_substring(s, substrings) {
    some i
    contains(lower(s), lower(substrings[i]))
}

list_contains(list, elem) {
    list[_] == elem
}

match_path(finding, paths) {
    some i, j
    glob.match(paths[j], ["/"], finding.spec.dependency_file_paths[i])
}"""

_REGO_FILE_PATH_HELPER = """\
file_path_match(finding, path) {
  contains(finding.spec.finding_metadata.custom.uri, path)
}

file_path_match(finding, path) {
  contains(finding.spec.finding_metadata.custom.location, path)
}

file_path_match(finding, path) {
  contains(finding.spec.finding_metadata.file_path, path)
}

file_path_match(finding, path) {
  some i
  glob.match(path, ["/"], finding.spec.dependency_file_paths[i])
}"""


def _rego_cwe_helpers(cwe_list: list[str]) -> str:
    """Generate Rego helper rules for CWE matching.

    Args:
        cwe_list: CWE identifiers (e.g. ``["CWE-22", "CWE-78"]``).

    Returns:
        Rego source fragment with ``cwe_match(finding)`` rules.
    """
    rules: list[str] = []
    for cwe in cwe_list:
        cwe_prefix = cwe if cwe.endswith(":") else f"{cwe}:"
        rules.append(
            f"cwe_match(finding) {{\n"
            f'  cwe := lower("{cwe_prefix}")\n'
            f"  finding_cwe := lower(finding.spec.finding_metadata.custom.cwes[_])\n"
            f"  startswith(finding_cwe, cwe)\n"
            f"}}"
        )
    return (
        "# Helper function: check if finding matches any of the specified CWEs\n"
        + "\n\n".join(rules)
    )


def resolve_rego_package(finding_category: str | None) -> str:
    """Determine the Rego package name from a finding category.

    Args:
        finding_category: Finding category constant
            (e.g. ``"FINDING_CATEGORY_SAST"``).

    Returns:
        Package name string (``"sast"``, ``"secrets"``, or ``"exceptions"``).
    """
    if finding_category == "FINDING_CATEGORY_SAST":
        return "sast"
    if finding_category == "FINDING_CATEGORY_SECRETS":
        return "secrets"
    return "exceptions"


def build_exception_rego_rule(
    *,
    finding_category: str | None = None,
    cwe_list: list[str] | None = None,
    file_path: str | None = None,
    tag: str | None = None,
    finding_tag: str | None = None,
    project_uuid: str | None = None,
    global_scope: bool = False,
) -> str:
    """Build a templated exception policy Rego rule.

    The generated rule uses ``data.resources.Finding[i]`` to iterate over
    all stored findings (the templated pattern recommended for SAST/SECRETS).

    This is a **pure function** — no API calls, no side effects.

    Args:
        finding_category: Finding category to match
            (e.g. ``"FINDING_CATEGORY_SAST"``).
        cwe_list: CWE identifiers to suppress (e.g. ``["CWE-22"]``).
        file_path: File path pattern to match (e.g. ``"devtools/"``).
        tag: Custom meta tag to match (e.g. ``"false-positive"``).
        finding_tag: System finding tag to match
            (e.g. ``"FINDING_TAGS_UNREACHABLE_DEPENDENCY"``).
        project_uuid: Scope to a specific project (ignored when
            *global_scope* is True).
        global_scope: When True, the rule applies to all projects.

    Returns:
        Complete Rego rule source string.
    """
    package_name = resolve_rego_package(finding_category)

    helper_blocks: list[str] = [_REGO_HELPERS_BASE]
    match_conditions: list[str] = []

    # Tag matching
    if tag:
        match_conditions.append(f'finding.meta.tags[_] == "{tag}"')
    if finding_tag:
        match_conditions.append(f'finding.spec.finding_tags[_] == "{finding_tag}"')

    # CWE matching
    if cwe_list:
        helper_blocks.append(_rego_cwe_helpers(cwe_list))
        match_conditions.append("cwe_match(finding)")

    # File path matching
    if file_path:
        helper_blocks.append(
            "# Helper function: check if finding is in target path\n"
            + _REGO_FILE_PATH_HELPER
        )
        match_conditions.append(f'file_path_match(finding, "{file_path}")')

    # Build main rule body
    rule_conditions = [
        "some i",
        "finding := data.resources.Finding[i]",
    ]
    if finding_category:
        rule_conditions.append(
            f'finding.spec.finding_categories[_] == "{finding_category}"'
        )
    rule_conditions.extend(match_conditions)
    if not global_scope and project_uuid:
        rule_conditions.append(f'finding.spec.project_uuid == "{project_uuid}"')

    conditions_str = "\n        ".join(rule_conditions)
    helpers_str = "\n".join(helper_blocks)

    return (
        f"package {package_name}\n"
        f"{helpers_str}\n"
        f"\n"
        f"match_finding[result] {{\n"
        f"        {conditions_str}\n"
        f"        result = {{\n"
        f'                "Endor" : {{\n'
        f'                        "Finding" : finding.uuid\n'
        f"                }}\n"
        f"        }}\n"
        f"}}"
    )


# ---------------------------------------------------------------------------
# Tag findings
# ---------------------------------------------------------------------------


def tag_findings_by_criteria(
    client: Client,
    namespace: str,
    project_uuid: str,
    categories: list[str],
    tag: str,
    *,
    file_path: str | None = None,
    dry_run: bool = False,
) -> TaggingResult:
    """Tag findings matching criteria with a custom meta tag.

    Uses the Client facade's ``finding.list()`` and ``finding.update()``
    (not raw HTTP) to add *tag* to ``meta.tags`` on each matching finding.

    Args:
        client: Authenticated ``endorlabs.Client`` instance.
        namespace: Namespace to search in.
        project_uuid: Project UUID to filter findings.
        categories: Finding categories to match
            (e.g. ``["FINDING_CATEGORY_SECRETS"]``).
        tag: Tag string to add (e.g. ``"false-positive"``).
        file_path: Optional file path to include in filter.
        dry_run: When True, compute matches but skip updates.

    Returns:
        TaggingResult with counts of tagged / skipped / failed findings.
    """
    # Build filter expression
    filter_parts = [f'spec.project_uuid=="{project_uuid}"']
    if categories:
        cat_clauses = " OR ".join(
            f'spec.finding_categories=="{cat}"' for cat in categories
        )
        filter_parts.append(f"({cat_clauses})")
    if file_path:
        filter_parts.append(f'spec.dependency_file_paths contains ["{file_path}"]')
    filter_expr = " AND ".join(filter_parts)

    findings = client.Finding.list(
        namespace=namespace,
        filter=filter_expr,
        sort_by="spec.level",
        desc=True,
    )

    result = TaggingResult(total=len(findings))

    if not findings:
        result.message = "No findings matched the criteria."
        return result

    for finding_obj in findings:
        existing_tags: list[str] = finding_obj.meta.tags or []
        if tag in existing_tags:
            result.skipped += 1
            continue

        if dry_run:
            result.tagged += 1
            continue

        new_tags = [tag, *(t for t in existing_tags if t != tag)]
        try:
            client.Finding.update(
                finding_obj,
                meta_tags=new_tags,
            )
            result.tagged += 1
        except Exception as exc:
            logger.error("Unable to tag finding '%s': %s", finding_obj.uuid, exc)
            result.failed += 1
            result.errors.append(f"{finding_obj.uuid}: {exc}")

    if result.failed:
        result.status = "partial"
    result.message = (
        f"Tagged {result.tagged}/{result.total} findings with '{tag}'"
        f" (skipped={result.skipped}, failed={result.failed})."
    )
    return result


# ---------------------------------------------------------------------------
# Create exception policy
# ---------------------------------------------------------------------------


def _build_exception_description(
    *,
    tag: str | None,
    finding_tag: str | None,
    finding_category: str | None,
    cwe_list: list[str] | None,
    file_path: str | None,
    global_scope: bool,
    project_uuid: str | None,
) -> str:
    """Build a human-readable description for an exception policy."""
    parts: list[str] = []
    if tag:
        parts.append(f"custom tag '{tag}'")
    if finding_tag:
        parts.append(f"system finding tag '{finding_tag}'")
    if finding_category:
        parts.append(f"category '{finding_category}'")
    if cwe_list:
        parts.append(f"CWEs {', '.join(cwe_list)}")
    if file_path:
        parts.append(f"file path '{file_path}'")
    scope_desc = (
        "globally"
        if global_scope
        else f"for project {project_uuid}"
        if project_uuid
        else "for matching projects"
    )
    return f"Suppresses findings with {', '.join(parts)} {scope_desc}"


def _build_exception_tags(
    *,
    tag: str | None,
    finding_tag: str | None,
    file_path: str | None,
    cwe_list: list[str] | None,
) -> list[str]:
    """Build policy tags for an exception policy."""
    tags = ["exception", "endorlabs-sdk"]
    if tag:
        tags.append(tag)
    if finding_tag:
        tags.append(finding_tag)
    if file_path:
        tags.append("file-path")
    if cwe_list:
        tags.append("cwe-based")
    return tags


def create_exception_policy(
    client: Client,
    namespace: str,
    policy_name: str,
    *,
    description: str | None = None,
    finding_category: str | None = None,
    cwe_list: list[str] | None = None,
    file_path: str | None = None,
    tag: str | None = None,
    finding_tag: str | None = None,
    project_uuid: str | None = None,
    project_tags: list[str] | None = None,
    global_scope: bool = False,
    propagate: bool = False,
    dry_run: bool = False,
) -> ExceptionPolicyResult:
    """Create an exception policy to suppress findings matching criteria.

    Generates a Rego rule from the provided criteria and creates a
    ``POLICY_TYPE_EXCEPTION`` policy via the Client facade.

    Args:
        client: Authenticated ``endorlabs.Client`` instance.
        namespace: Namespace where the policy will be created.
        policy_name: Human-readable name for the policy.
        description: Optional description (auto-generated when omitted).
        finding_category: Finding category to match.
        cwe_list: CWE identifiers to suppress.
        file_path: File path pattern to match.
        tag: Custom meta tag to match.
        finding_tag: System finding tag to match.
        project_uuid: Scope to a specific project.
        project_tags: Project tags for selector.
        global_scope: Apply to all projects in namespace.
        propagate: Propagate to child namespaces.
        dry_run: When True, build the policy but skip creation.

    Returns:
        ExceptionPolicyResult with the created policy details.
    """
    rego_rule = build_exception_rego_rule(
        finding_category=finding_category,
        cwe_list=cwe_list,
        file_path=file_path,
        tag=tag,
        finding_tag=finding_tag,
        project_uuid=project_uuid if not global_scope else None,
        global_scope=global_scope,
    )

    package_name = resolve_rego_package(finding_category)

    if not description:
        description = _build_exception_description(
            tag=tag,
            finding_tag=finding_tag,
            finding_category=finding_category,
            cwe_list=cwe_list,
            file_path=file_path,
            global_scope=global_scope,
            project_uuid=project_uuid,
        )

    result = ExceptionPolicyResult(
        name=policy_name,
        rego_rule=rego_rule,
        pattern_type="templated",
        package_name=package_name,
    )

    if dry_run:
        result.message = f"[DRY RUN] Would create exception policy '{policy_name}'."
        return result

    policy_tags = _build_exception_tags(
        tag=tag,
        finding_tag=finding_tag,
        file_path=file_path,
        cwe_list=cwe_list,
    )

    # Build project selector
    project_selector: list[str] | None = None
    if not global_scope and project_uuid:
        project_selector = [f"$uuid={project_uuid}"]
    elif project_tags:
        project_selector = [f"${t}" for t in project_tags]

    try:
        policy = client.Policy.create(
            name=policy_name,
            namespace=namespace,
            description=description,
            tags=policy_tags,
            policy_type="POLICY_TYPE_EXCEPTION",
            rule=rego_rule,
            query_statements=[f"data.{package_name}.match_finding"],
            project_selector=project_selector,
            resource_kinds=["Finding"],
            disable=False,
            exception={"reason": "EXCEPTION_REASON_FALSE_POSITIVE"},
            propagate=propagate,
        )
        result.uuid = policy.uuid
        result.message = (
            f"Created exception policy '{policy_name}' (uuid={policy.uuid})."
        )
        logger.info(result.message)
    except Exception as exc:
        result.status = "error"
        result.message = f"Unable to create exception policy: {exc}"
        result.errors.append(str(exc))
        logger.error(result.message)

    return result
