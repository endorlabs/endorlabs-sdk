"""LangChain tools wrapping Endor Labs SDK operations.

Tools are created via create_tools(client) which binds the SDK client
to each tool function via closures. Uses a registry-driven factory pattern
to generate list/get tools for all SDK resources from the SDK's authoritative
RESOURCE_REGISTRY.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from langchain_core.tools import StructuredTool

from endorlabs.registry import RESOURCE_REGISTRY, ResourceEntry

if TYPE_CHECKING:
    from langchain_core.tools import BaseTool

    from endorlabs import Client


# Human-readable descriptions for resources (overrides for better LLM UX)
_RESOURCE_DESCRIPTIONS: dict[str, str] = {
    "namespace": "namespaces (organizational units)",
    "project": "projects (repositories being scanned)",
    "finding": "security findings",
    "repository": "repositories",
    "repository_version": "repository versions (snapshots at specific commits)",
    "policy": "policies (security rules and checks)",
    "authorization_policy": "authorization policies (access control rules)",
    "package_version": "package versions (dependencies)",
    "package_license": "package licenses",
    "dependency_metadata": "dependency metadata (OSS package information)",
    "installation": "installations (GitHub/GitLab app installations)",
    "scan_profile": "scan profiles (scan configurations)",
    "scan_result": "scan results",
    "linter_result": "linter results (code quality findings)",
    "metric": "metrics",
    "semgrep_rule": "Semgrep rules (custom SAST rules)",
    "api_key": "API keys",
    "audit_log": "audit logs",
    "finding_log": "finding logs (historical finding changes)",
    "notification_target": "notification targets (Slack, email, etc.)",
    "scan_workflow": "scan workflows",
    "scan_workflow_result": "scan workflow results",
    "version_upgrade": "version upgrades (recommended dependency updates)",
    "code_owners": "code owners",
    "invitation": "invitations (pending user invites)",
    "authentication_log": "authentication logs",
    "endor_license": "Endor licenses",
    "policy_template": "policy templates (built-in policy definitions)",
}

# Valid filter fields for each resource type (prevents LLM from hallucinating fields)
# Resources not listed here use the default: meta.name, meta.description
_RESOURCE_FILTER_FIELDS: dict[str, list[str]] = {
    "project": [
        "meta.name (repo URL like 'https://github.com/org/repo.git')",
        "meta.description",
        "spec.platform_source (PLATFORM_SOURCE_GITHUB, GITLAB, etc.)",
    ],
    "finding": [
        "meta.name",
        "meta.description",
        "spec.level (FINDING_LEVEL_CRITICAL, HIGH, MEDIUM, LOW)",
        "spec.project_uuid",
        "spec.finding_categories",
        "spec.target_dependency_package_name",
    ],
    "scan_result": [
        "meta.name",
        "spec.project_uuid",
        "spec.status",
        "spec.exit_code",
    ],
    "policy": [
        "meta.name",
        "meta.description",
        "spec.disabled (true/false)",
    ],
    "namespace": [
        "meta.name",
        "meta.description",
        "spec.parent_uuid",
    ],
    "repository": [
        "meta.name",
        "meta.description",
        "spec.http_clone_url",
    ],
    "package_version": [
        "meta.name",
        "spec.resolved_version",
        "spec.ecosystem",
    ],
    "installation": [
        "meta.name",
        "spec.platform_source",
    ],
}

# Default filter fields for resources not in _RESOURCE_FILTER_FIELDS
_DEFAULT_FILTER_FIELDS: list[str] = [
    "meta.name",
    "meta.description",
]


def _humanize_resource_name(attr_name: str) -> str:
    """Convert resource attr_name to human-readable description."""
    if attr_name in _RESOURCE_DESCRIPTIONS:
        return _RESOURCE_DESCRIPTIONS[attr_name]
    # Fallback: convert snake_case to spaces
    return attr_name.replace("_", " ") + "s"


def _get_tool_config_from_registry(entry: ResourceEntry) -> dict[str, Any]:
    """Derive tool configuration from SDK registry entry.

    Args:
        entry: A ResourceEntry from RESOURCE_REGISTRY.

    Returns:
        Tool configuration dict with description, scope, parent_kind, etc.
    """
    return {
        "attr_name": entry.attr_name,
        "description": _humanize_resource_name(entry.attr_name),
        "scope": entry.scope,  # "system" | "oss" | None (tenant)
        "parent_kind": entry.parent_kind,  # e.g., "project" for scan_result
        "model_class": entry.model_class,  # For field introspection
    }


# Field extractors for resource types. These define what fields to include
# in list/get results for each resource. Uses (field_name, extractor_lambda).
# Common extractors are reused; resource-specific ones override.
_COMMON_LIST_FIELDS: list[tuple[str, Callable[[Any], Any]]] = [
    ("uuid", lambda r: r.uuid),
    ("name", lambda r: r.meta.name if r.meta else None),
    ("description", lambda r: r.meta.description if r.meta else None),
]

_COMMON_GET_FIELDS: list[tuple[str, Callable[[Any], Any]]] = [
    ("uuid", lambda r: r.uuid),
    ("name", lambda r: r.meta.name if r.meta else None),
    ("description", lambda r: r.meta.description if r.meta else None),
]

# Resource-specific field overrides (only for resources needing special fields)
_FieldConfig = dict[str, list[tuple[str, Callable[[Any], Any]]]]
_RESOURCE_FIELD_OVERRIDES: dict[str, _FieldConfig] = {
    "namespace": {
        "get_fields": [
            ("uuid", lambda r: r.uuid),
            ("name", lambda r: r.meta.name if r.meta else None),
            ("description", lambda r: r.meta.description if r.meta else None),
            ("parent_uuid", lambda r: r.spec.parent_uuid if r.spec else None),
        ],
    },
    "project": {
        "list_fields": [
            ("uuid", lambda r: r.uuid),
            ("name", lambda r: r.meta.name if r.meta else None),
            (
                "git_url",
                lambda r: r.spec.git.http_clone_url if r.spec and r.spec.git else None,
            ),
        ],
        "get_fields": [
            ("uuid", lambda r: r.uuid),
            ("name", lambda r: r.meta.name if r.meta else None),
            ("description", lambda r: r.meta.description if r.meta else None),
            (
                "git_url",
                lambda r: r.spec.git.http_clone_url if r.spec and r.spec.git else None,
            ),
            (
                "default_branch",
                lambda r: r.spec.git.default_ref if r.spec and r.spec.git else None,
            ),
        ],
    },
    "repository": {
        "list_fields": [
            ("uuid", lambda r: r.uuid),
            ("name", lambda r: r.meta.name if r.meta else None),
            ("http_clone_url", lambda r: r.spec.http_clone_url if r.spec else None),
        ],
        "get_fields": [
            ("uuid", lambda r: r.uuid),
            ("name", lambda r: r.meta.name if r.meta else None),
            ("description", lambda r: r.meta.description if r.meta else None),
            ("http_clone_url", lambda r: r.spec.http_clone_url if r.spec else None),
            ("default_branch", lambda r: r.spec.default_branch if r.spec else None),
        ],
    },
    "repository_version": {
        "list_fields": [
            ("uuid", lambda r: r.uuid),
            ("name", lambda r: r.meta.name if r.meta else None),
            (
                "version",
                lambda r: r.spec.version.ref if r.spec and r.spec.version else None,
            ),
            (
                "sha",
                lambda r: r.spec.version.sha if r.spec and r.spec.version else None,
            ),
        ],
        "get_fields": [
            ("uuid", lambda r: r.uuid),
            ("name", lambda r: r.meta.name if r.meta else None),
            (
                "version",
                lambda r: r.spec.version.ref if r.spec and r.spec.version else None,
            ),
            (
                "sha",
                lambda r: r.spec.version.sha if r.spec and r.spec.version else None,
            ),
        ],
    },
    "policy": {
        "list_fields": [
            ("uuid", lambda r: r.uuid),
            ("name", lambda r: r.meta.name if r.meta else None),
            ("description", lambda r: r.meta.description if r.meta else None),
            ("enabled", lambda r: r.spec.disabled is False if r.spec else None),
        ],
        "get_fields": [
            ("uuid", lambda r: r.uuid),
            ("name", lambda r: r.meta.name if r.meta else None),
            ("description", lambda r: r.meta.description if r.meta else None),
            ("enabled", lambda r: r.spec.disabled is False if r.spec else None),
            (
                "action",
                lambda r: str(r.spec.action) if r.spec and r.spec.action else None,
            ),
        ],
    },
    "package_version": {
        "list_fields": [
            ("uuid", lambda r: r.uuid),
            ("name", lambda r: r.meta.name if r.meta else None),
            ("version", lambda r: r.spec.resolved_version if r.spec else None),
            ("ecosystem", lambda r: r.spec.ecosystem if r.spec else None),
        ],
        "get_fields": [
            ("uuid", lambda r: r.uuid),
            ("name", lambda r: r.meta.name if r.meta else None),
            ("version", lambda r: r.spec.resolved_version if r.spec else None),
            ("ecosystem", lambda r: r.spec.ecosystem if r.spec else None),
        ],
    },
    "installation": {
        "list_fields": [
            ("uuid", lambda r: r.uuid),
            ("name", lambda r: r.meta.name if r.meta else None),
            ("platform", lambda r: r.spec.platform_source if r.spec else None),
        ],
        "get_fields": [
            ("uuid", lambda r: r.uuid),
            ("name", lambda r: r.meta.name if r.meta else None),
            ("platform", lambda r: r.spec.platform_source if r.spec else None),
        ],
    },
    "scan_result": {
        "list_fields": [
            ("uuid", lambda r: r.uuid),
            ("name", lambda r: r.meta.name if r.meta else None),
            (
                "status",
                lambda r: str(r.spec.status) if r.spec and r.spec.status else None,
            ),
        ],
        "get_fields": [
            ("uuid", lambda r: r.uuid),
            ("name", lambda r: r.meta.name if r.meta else None),
            (
                "status",
                lambda r: str(r.spec.status) if r.spec and r.spec.status else None,
            ),
            ("exit_code", lambda r: r.spec.exit_code if r.spec else None),
        ],
    },
    "finding": {
        "list_fields": [
            ("uuid", lambda r: r.uuid),
            ("description", lambda r: r.meta.description if r.meta else None),
            ("severity", lambda r: str(r.spec.level) if r.spec else None),
            (
                "category",
                lambda r: str(r.spec.finding_categories)
                if r.spec and r.spec.finding_categories
                else None,
            ),
        ],
        "get_fields": [
            ("uuid", lambda r: r.uuid),
            ("description", lambda r: r.meta.description if r.meta else None),
            ("severity", lambda r: str(r.spec.level) if r.spec else None),
            (
                "category",
                lambda r: str(r.spec.finding_categories)
                if r.spec and r.spec.finding_categories
                else None,
            ),
            (
                "target_dependency",
                lambda r: r.spec.target_dependency_package_name if r.spec else None,
            ),
            (
                "source_policy_name",
                lambda r: r.spec.source_policy_info.name
                if r.spec and r.spec.source_policy_info
                else None,
            ),
        ],
    },
}


def _get_list_fields(attr_name: str) -> list[tuple[str, Callable[[Any], Any]]]:
    """Get list fields for a resource, using overrides or common fields."""
    overrides = _RESOURCE_FIELD_OVERRIDES.get(attr_name, {})
    return overrides.get("list_fields", _COMMON_LIST_FIELDS)


def _get_get_fields(attr_name: str) -> list[tuple[str, Callable[[Any], Any]]]:
    """Get get fields for a resource, using overrides or common fields."""
    overrides = _RESOURCE_FIELD_OVERRIDES.get(attr_name, {})
    return overrides.get("get_fields", _COMMON_GET_FIELDS)


def _extract_fields(
    resource: Any, field_config: list[tuple[str, Callable[[Any], Any]]]
) -> dict[str, Any]:
    """Extract fields from a resource using the field configuration."""
    result: dict[str, Any] = {}
    for key, extractor in field_config:
        try:
            result[key] = extractor(resource)
        except (AttributeError, TypeError):
            result[key] = None
    return result


# Filter syntax examples for docstrings
_FILTER_EXAMPLES = """
Filter Expression Syntax (CRITICAL - follow exactly):
    Operators: ==, !=, contains, in, matches, <, <=, >, >=
    
    CORRECT examples:
    - meta.name == "my-project"
    - meta.name contains "api"
    - spec.level == FINDING_LEVEL_CRITICAL
    - (meta.name contains "api") and (spec.level == FINDING_LEVEL_HIGH)
    - spec.project_uuid == "abc123"
    
    WRONG (will cause errors):
    - name="my-project"     (missing meta., wrong operator)
    - meta.name="project"   (wrong operator, use ==)
    - name=foo              (missing meta., missing quotes, wrong operator)
"""


def _make_list_tool(
    client: Client,
    attr_name: str,
    config: dict[str, Any],
) -> StructuredTool:
    """Create a list tool for the given resource.

    Derives configuration from SDK registry. Always passes traverse to the SDK
    (the SDK handles it correctly for all resources). Uses proper pagination
    via max_pages.

    Args:
        client: The Endor Labs client.
        attr_name: The attribute name on the client (e.g., "project").
        config: Resource configuration derived from RESOURCE_REGISTRY.

    Returns:
        A StructuredTool for listing the resource.
    """
    description = config["description"]
    parent_kind = config.get("parent_kind")
    scope = config.get("scope")
    list_fields = _get_list_fields(attr_name)

    def list_func(
        namespace: str | None = None,
        max_results: int = 100,
        max_pages: int = 10,
        filter_expr: str | None = None,
        traverse: bool = False,
        parent_uuid: str | None = None,
    ) -> str:
        kwargs: dict[str, object] = {
            "page_size": min(max_results, 100),
            "max_pages": max_pages,
        }

        # Handle namespace (not for system/oss scoped resources)
        if namespace and scope not in ("system", "oss"):
            kwargs["namespace"] = namespace

        # Always pass traverse to SDK - it handles it correctly for all resources
        if traverse:
            kwargs["traverse"] = traverse

        # Handle filter
        if filter_expr:
            kwargs["filter"] = filter_expr

        # Handle parent (for resources with parent_kind like scan_result)
        if parent_kind and parent_uuid:
            # Use parent UUID in filter
            parent_filter = f"spec.{parent_kind}_uuid=={parent_uuid}"
            kwargs["filter"] = (
                parent_filter
                if not filter_expr
                else f"({filter_expr}) and {parent_filter}"
            )

        facade = getattr(client, attr_name)
        resources = facade.list(**kwargs)
        results = [_extract_fields(r, list_fields) for r in resources[:max_results]]
        return json.dumps(results, indent=2, default=str)

    # Build comprehensive docstring with all parameters
    doc_parts = [f"List {description}."]
    doc_parts.append("")
    doc_parts.append("Args:")
    if scope not in ("system", "oss"):
        doc_parts.append(
            "    namespace: Optional namespace to query. "
            "Uses client default if not provided."
        )
    doc_parts.append(
        "    max_results: Maximum number of results to return (default 100)."
    )
    doc_parts.append(
        "    max_pages: Maximum pages to fetch for pagination (default 10). "
        "Each page has up to 100 results."
    )
    doc_parts.append(
        "    filter_expr: Filter expression using == operator and meta./spec. paths. "
        'Example: meta.name == "project-name" (NOT name="project-name")'
    )
    doc_parts.append(
        "    traverse: If True, include results from child namespaces recursively."
    )
    if parent_kind:
        doc_parts.append(f"    parent_uuid: Optional {parent_kind} UUID to filter by.")
    doc_parts.append("")
    doc_parts.append("Returns:")
    doc_parts.append(
        f"    JSON array of {description} with fields: "
        f"{', '.join(f[0] for f in list_fields)}."
    )
    doc_parts.append("")
    doc_parts.append(_FILTER_EXAMPLES.strip())

    # Add resource-specific filterable fields
    filter_fields = _RESOURCE_FILTER_FIELDS.get(attr_name, _DEFAULT_FILTER_FIELDS)
    doc_parts.append("")
    doc_parts.append(f"Valid filter fields for {attr_name}:")
    for field in filter_fields:
        doc_parts.append(f"    - {field}")

    list_func.__doc__ = "\n".join(doc_parts)
    list_func.__name__ = f"list_{attr_name}"

    # Build rich tool description for LLM
    tool_description = f"List {description}"
    if scope not in ("system", "oss"):
        tool_description += " (supports traverse for child namespaces)"

    return StructuredTool.from_function(
        func=list_func,
        name=f"list_{attr_name}",
        description=tool_description,
    )


def _make_get_tool(
    client: Client,
    attr_name: str,
    config: dict[str, Any],
) -> StructuredTool:
    """Create a get tool for the given resource.

    Args:
        client: The Endor Labs client.
        attr_name: The attribute name on the client (e.g., "project").
        config: Resource configuration derived from RESOURCE_REGISTRY.

    Returns:
        A StructuredTool for getting a single resource by UUID.
    """
    description = config["description"]
    get_fields = _get_get_fields(attr_name)
    resource_singular = (
        description.rstrip("s") if description.endswith("s") else description
    )

    def get_func(uuid: str, namespace: str | None = None) -> str:
        facade = getattr(client, attr_name)
        kwargs: dict[str, Any] = {}
        if namespace:
            kwargs["namespace"] = namespace
        resource = facade.get(uuid, **kwargs)
        if not resource:
            return json.dumps(
                {"error": f"{resource_singular.title()} with UUID {uuid} not found."},
                indent=2,
            )
        return json.dumps(_extract_fields(resource, get_fields), indent=2, default=str)

    # Build comprehensive docstring with field info
    field_names = [f[0] for f in get_fields]
    get_func.__doc__ = (
        f"Get detailed information about a specific {resource_singular} by UUID.\n\n"
        f"Args:\n"
        f"    uuid: The UUID of the {resource_singular} to retrieve.\n"
        f"    namespace: Optional namespace (uses client default if not provided).\n\n"
        f"Returns:\n"
        f"    JSON object with fields: {', '.join(field_names)}.\n"
        f"    Returns error object if not found."
    )
    get_func.__name__ = f"get_{attr_name}"

    return StructuredTool.from_function(
        func=get_func,
        name=f"get_{attr_name}",
        description=f"Get a {resource_singular} by UUID",
    )


def create_tools(client: Client) -> list[BaseTool]:
    """Create LangChain tools bound to the given Endor Labs client.

    Tools are generated from the SDK's RESOURCE_REGISTRY, ensuring the agent
    tools stay in sync with SDK capabilities. All tenant-scoped resources
    support traverse for querying child namespaces.

    Args:
        client: An authenticated Endor Labs Client instance.

    Returns:
        List of LangChain tools for interacting with Endor Labs API.
    """
    tools: list[BaseTool] = []

    # Resources with custom list implementations (finding has severity filter)
    custom_list_resources = {"finding"}

    # Generate tools from SDK registry (single source of truth)
    for entry in RESOURCE_REGISTRY:
        config = _get_tool_config_from_registry(entry)
        attr_name = entry.attr_name

        # Skip custom_list resources for list tool (they have manual implementations)
        if attr_name not in custom_list_resources:
            tools.append(_make_list_tool(client, attr_name, config))

        # Always generate get tool (all resources support get)
        tools.append(_make_get_tool(client, attr_name, config))

    # Custom implementation: list_findings with severity filter and traverse support
    list_fields = _get_list_fields("finding")

    def list_findings(
        namespace: str | None = None,
        max_results: int = 100,
        max_pages: int = 10,
        filter_expr: str | None = None,
        severity: str | None = None,
        traverse: bool = False,
    ) -> str:
        """List security findings in the namespace.

        Args:
            namespace: Optional namespace to query. Uses client default if not provided.
            max_results: Maximum number of findings to return (default 100).
            max_pages: Maximum pages to fetch for pagination (default 10).
            filter_expr: Optional filter expression (e.g., "spec.project_uuid==abc123").
            severity: Filter by severity level (CRITICAL, HIGH, MEDIUM, LOW).
            traverse: If True, include results from child namespaces recursively.

        Returns:
            JSON array of findings with uuid, description, severity, and category.

        Filter Expression Syntax:
            - Equality: spec.level == FINDING_LEVEL_CRITICAL
            - Contains: meta.description contains "SQL"
            - Project: spec.project_uuid == "project-uuid-here"
            - Compound: (spec.level == FINDING_LEVEL_HIGH) and (...)
        """
        kwargs: dict[str, object] = {
            "page_size": min(max_results, 100),
            "max_pages": max_pages,
        }
        if namespace:
            kwargs["namespace"] = namespace

        # Always pass traverse to SDK
        if traverse:
            kwargs["traverse"] = traverse

        filters = []
        if filter_expr:
            filters.append(filter_expr)
        if severity:
            filters.append(f"spec.level == FINDING_LEVEL_{severity.upper()}")
        if filters:
            kwargs["filter"] = " and ".join(filters)

        findings = client.finding.list(**kwargs)
        results = [_extract_fields(f, list_fields) for f in findings[:max_results]]
        return json.dumps(results, indent=2, default=str)

    tools.append(
        StructuredTool.from_function(
            func=list_findings,
            name="list_findings",
            description=(
                "List security findings with optional severity filter "
                "(supports traverse for child namespaces)"
            ),
        )
    )

    # Helper tool: get valid filter fields for a resource type
    def get_filter_fields(resource_type: str) -> str:
        """Get valid filter fields for a resource type.

        Call this BEFORE constructing a filter if unsure which fields are valid.
        This prevents errors from using invalid field paths.

        Args:
            resource_type: Resource name (project, finding, scan_result, policy,
                namespace, repository, package_version, installation, etc.)

        Returns:
            JSON with valid filter field paths for the resource and syntax reminder.

        Example:
            get_filter_fields("project") returns fields like meta.name, spec.platform_source
        """
        fields = _RESOURCE_FILTER_FIELDS.get(resource_type, _DEFAULT_FILTER_FIELDS)
        return json.dumps(
            {
                "resource": resource_type,
                "filter_fields": fields,
                "syntax_reminder": 'Use == operator with field path: meta.name == "value"',
                "example": f'{fields[0].split(" ")[0]} == "example-value"',
            },
            indent=2,
        )

    tools.append(
        StructuredTool.from_function(
            func=get_filter_fields,
            name="get_filter_fields",
            description=(
                "Get valid filter fields for a resource type. "
                "Call this BEFORE constructing a filter to avoid invalid field errors."
            ),
        )
    )

    return tools
