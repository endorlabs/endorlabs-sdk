"""Generate Client stub (.pyi) from RESOURCE_REGISTRY and CUSTOM_FACADE_REGISTRY.

Single source of truth: the registry. Run from repo root with:
  uv run python scripts/generate_client_stub.py
Writes src/endorlabs/client_surface.pyi so Pyright types client.project, etc.

Each resource gets a dedicated stub class (e.g. ``_ProjectFacade``) that
exposes only the methods the resource actually supports, with concrete
return types and validated resource descriptions.
"""

from __future__ import annotations

import inspect
import re
import sys
from pathlib import Path
from typing import Any

# Add src so we can import endorlabs.registry
repo_root = Path(__file__).resolve().parent.parent
src = repo_root / "src"
if str(src) not in sys.path:
    sys.path.insert(0, str(src))

from endorlabs.facade import ResourceFacade, _ListableFacade
from endorlabs.registry import (
    CUSTOM_FACADE_REGISTRY,
    RESOURCE_REGISTRY,
    ResourceEntry,
)
from endorlabs.utils.model_validation import get_tags_update_paths

# ---------------------------------------------------------------------------
# Resource descriptions — validated from OpenAPI spec + local user docs
# ---------------------------------------------------------------------------
RESOURCE_DESCRIPTIONS: dict[str, str] = {
    "namespace": "Isolate and organize resources in a parent-child hierarchy.",
    "project": "Logical root for a repository and its scan results.",
    "finding": "Security or compliance finding from a scan.",
    "repository": "Source control repository metadata.",
    "repository_version": "Versioned snapshot of a repository.",
    "policy": "Rule controlling scan behavior, findings, and workflows.",
    "authorization_policy": "Permission grant for an authenticated identity.",
    "package_version": "Package version with dependency information.",
    "installation": (
        "SCM platform integration (GitHub, GitLab, Azure, Bitbucket)."
    ),
    "scan_profile": "Scan configuration applied across projects.",
    "scan_result": "Results from an endorctl scan.",
    "scan_log_request": "Request for scan log messages.",
    "linter_result": (
        "Linter analysis result for a package or repository version."
    ),
    "metric": "Analytics output attached to packages or repositories.",
    "semgrep_rule": "Custom SAST rule in Semgrep/OpenGrep format.",
    "api_key": "API key for programmatic access.",
    "audit_log": "Audit trail of API operations.",
    "finding_log": "Historical snapshot of a finding state.",
    "notification_target": "Integration endpoint for notification delivery.",
    "scan_workflow": "Workflow orchestrating scan steps.",
    "scan_workflow_result": "Result from a scan workflow execution.",
    "version_upgrade": "Suggested dependency version upgrade.",
    "invitation": "User invitation for platform access.",
    "code_owners": "Code ownership assignments for a project.",
    "package_license": "License information for a package.",
    "dependency_metadata": "Dependency relationship between packages.",
    "vulnerability": "Open-source vulnerability records.",
    "malware": "Open-source malware records.",
    "query_vulnerability": "Advanced vulnerability query endpoint.",
    "query_malware": "Advanced malware query endpoint.",
    "authentication_log": "Authentication event log.",
    "endor_license": "Platform license assigned to a tenant.",
    "policy_template": "Reusable template for creating policies.",
}

# ---------------------------------------------------------------------------
# Signature helpers
# ---------------------------------------------------------------------------

# Methods defined on _ListableFacade (always present when "list" is supported)
_LISTABLE_METHODS = ("list", "lookup", "list_iter")
# Methods defined on ResourceFacade
_CRUD_METHODS = ("get", "create", "update", "delete")
_TAG_METHODS = ("tag", "untag")

# Map method name -> class that defines it
_METHOD_SOURCE: dict[str, type] = {}
for _m in _LISTABLE_METHODS:
    _METHOD_SOURCE[_m] = _ListableFacade
for _m in (*_CRUD_METHODS, *_TAG_METHODS):
    _METHOD_SOURCE[_m] = ResourceFacade


def _get_method_signatures() -> dict[str, inspect.Signature]:
    """Extract signatures for all public facade methods once."""
    sigs: dict[str, inspect.Signature] = {}
    for name, cls in _METHOD_SOURCE.items():
        sigs[name] = inspect.signature(getattr(cls, name))
    return sigs


def _get_method_docline(name: str) -> str:
    """Extract first line of a facade method's docstring.

    Truncates to fit within 88-char line limit (8 chars indent + quotes).
    """
    cls = _METHOD_SOURCE[name]
    doc = getattr(cls, name).__doc__ or ""
    first = doc.strip().split("\n")[0].strip()
    # Method docstrings are indented 8 chars: '        """..."""'
    max_content = 88 - 8 - 6  # 74 chars for the docstring content
    if len(first) > max_content:
        # Truncate at last word boundary that fits
        truncated = first[:max_content].rsplit(" ", 1)[0].rstrip(".,;:")
        first = truncated + "."
    return first


def _format_annotation(ann: Any, model_name: str) -> str:
    """Convert an inspect annotation to a .pyi string, replacing T."""
    if ann is inspect.Parameter.empty:
        return ""
    s = str(ann) if isinstance(ann, str) else getattr(ann, "__name__", str(ann))
    # Replace the generic type variable T with the concrete model name.
    # Use word-boundary replacement so e.g. "Iterator" is not mangled.
    s = re.sub(r"\bT\b", model_name, s)
    return s


def _format_default(default: Any) -> str:
    """Convert inspect default to .pyi representation."""
    if default is inspect.Parameter.empty:
        return ""
    # In .pyi stubs, all defaults are represented as ...
    return " = ..."


def _format_method(
    name: str,
    sig: inspect.Signature,
    model_name: str,
    indent: str = "    ",
) -> list[str]:
    """Format one method as .pyi stub lines."""
    docline = _get_method_docline(name)
    params: list[str] = []
    saw_keyword_only = False

    for pname, param in sig.parameters.items():
        if pname == "self":
            params.append(f"{indent}    self,")
            continue

        # Insert bare * for keyword-only boundary
        if (
            param.kind == inspect.Parameter.KEYWORD_ONLY
            and not saw_keyword_only
        ):
            params.append(f"{indent}    *,")
            saw_keyword_only = True

        ann = _format_annotation(param.annotation, model_name)
        default = _format_default(param.default)
        ann_str = f": {ann}" if ann else ""

        if param.kind == inspect.Parameter.VAR_KEYWORD:
            params.append(f"{indent}    **{pname}{ann_str},")
        elif param.kind == inspect.Parameter.VAR_POSITIONAL:
            params.append(f"{indent}    *{pname}{ann_str},")
        else:
            params.append(f"{indent}    {pname}{ann_str}{default},")

    ret = _format_annotation(sig.return_annotation, model_name)
    ret_str = f" -> {ret}" if ret else ""

    lines = [f"{indent}def {name}("]
    lines.extend(params)
    lines.append(f"{indent}){ret_str}:")
    if docline:
        lines.append(f'{indent}    """{docline}"""')
    lines.append(f"{indent}    ...")
    return lines


# ---------------------------------------------------------------------------
# Per-resource class builder
# ---------------------------------------------------------------------------


def _get_available_methods(entry: ResourceEntry) -> list[str]:
    """Return method names this resource supports."""
    methods: list[str] = []
    if "list" in entry.supported_ops:
        methods.extend(_LISTABLE_METHODS)
    if "get" in entry.supported_ops:
        methods.append("get")
    if "create" in entry.supported_ops:
        methods.append("create")
    if "update" in entry.supported_ops:
        methods.append("update")
    if "delete" in entry.supported_ops:
        methods.append("delete")
    if "update" in entry.supported_ops:
        tags_paths = get_tags_update_paths(entry.model_class)
        if "meta.tags" in tags_paths:
            methods.extend(_TAG_METHODS)
    return methods


def _build_class_docstring(entry: ResourceEntry) -> list[str]:
    """Build multi-line class docstring from description + registry metadata."""
    desc = RESOURCE_DESCRIPTIONS.get(entry.attr_name, "")
    parts: list[str] = []
    if desc:
        parts.append(desc)

    # Identity kwargs — wrap if the line would exceed 88 chars
    if entry.filter_kwarg_map:
        items = [
            f"{k} (-> {v})" for k, v in entry.filter_kwarg_map.items()
        ]
        id_line = f"Identity kwargs: {', '.join(items)}."
        # 4 chars indent in class body
        if len(id_line) + 4 <= 88:
            parts.append(id_line)
        else:
            # Split across lines
            parts.append("Identity kwargs:")
            for item in items:
                parts.append(f"  {item}")

    # Parent scoping
    if entry.parent_kind:
        parts.append(f"Supports list(parent=<{entry.parent_kind}>).")

    # Scope
    if entry.scope == "system":
        parts.append("System-scoped.")
    elif entry.scope == "oss":
        parts.append("OSS-scoped (namespace fixed to 'oss').")

    if not parts:
        return ['    """Resource facade."""']

    if len(parts) == 1:
        return [f'    """{parts[0]}"""']

    lines = [f'    """{parts[0]}', ""]
    for p in parts[1:]:
        lines.append(f"    {p}")
    lines.append('    """')
    return lines


def _emit_resource_class(
    entry: ResourceEntry,
    sigs: dict[str, inspect.Signature],
) -> list[str]:
    """Generate a per-resource stub class."""
    model_name = entry.model_class.__name__
    # Class name: _ProjectFacade, _FindingFacade, etc.
    class_name = f"_{model_name}Facade"
    methods = _get_available_methods(entry)

    lines: list[str] = []
    lines.append(f"class {class_name}:")
    lines.extend(_build_class_docstring(entry))
    lines.append("")

    for i, method_name in enumerate(methods):
        sig = sigs[method_name]
        lines.extend(_format_method(method_name, sig, model_name))
        # Blank line between methods, but not after the last one
        if i < len(methods) - 1:
            lines.append("")

    return lines


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:  # noqa: D103
    out = src / "endorlabs" / "client_surface.pyi"
    sigs = _get_method_signatures()

    lines: list[str] = [
        "# Generated by scripts/generate_client_stub.py"
        " — do not edit by hand.",
        "# Source of truth: endorlabs.registry.RESOURCE_REGISTRY"
        " and CUSTOM_FACADE_REGISTRY.",
        "",
        "from collections.abc import Iterator",
        "from typing import Any",
        "",
    ]

    # Collect ALL relative imports (alphabetically sorted by module).
    # isort requires one contiguous first-party block in alpha order.
    relative_imports: dict[str, list[str]] = {
        ".api_client": ["APIClient"],
        ".facade": ["ScanLogsFacade"],
        ".core.filter": ["FilterExpression"],
        ".core.types": ["ListParameters"],
    }
    for entry in RESOURCE_REGISTRY:
        mod = entry.model_class.__module__
        name = entry.model_class.__name__
        if mod.startswith("endorlabs."):
            mod = "." + mod[len("endorlabs.") :]
        if mod not in relative_imports:
            relative_imports[mod] = []
        if name not in relative_imports[mod]:
            relative_imports[mod].append(name)

    for mod in sorted(relative_imports.keys()):
        names = sorted(relative_imports[mod])
        lines.append(f"from {mod} import {', '.join(names)}")

    # -- Per-resource stub classes -----------------------------------------
    for entry in RESOURCE_REGISTRY:
        lines.append("")
        lines.extend(_emit_resource_class(entry, sigs))

    # -- Client class ------------------------------------------------------
    lines.append("")
    lines.append("class Client:")

    # Build compact resource list for the Client docstring
    resource_names = sorted(e.attr_name for e in RESOURCE_REGISTRY)
    custom_names = [e.attr_name for e in CUSTOM_FACADE_REGISTRY]
    # Wrap resource names into lines of ~78 chars (88 - 4 indent - 6 margin)
    resource_lines: list[str] = []
    current_line = "    "
    for i, name in enumerate(resource_names):
        separator = ", " if i > 0 else ""
        candidate = current_line + separator + name
        if len(candidate) > 78 and current_line.strip():
            resource_lines.append(current_line.rstrip() + ",")
            current_line = "    " + name
        else:
            current_line = candidate
    if current_line.strip():
        resource_lines.append(current_line)

    lines.append('    """Resource-oriented client with typed facades.')
    lines.append("")
    lines.append("    Resources:")
    for rl in resource_lines:
        lines.append(rl)
    if custom_names:
        lines.append(f"    Custom: {', '.join(custom_names)}")
    lines.append('    """')
    lines.append("")
    for entry in RESOURCE_REGISTRY:
        attr = entry.attr_name
        model_name = entry.model_class.__name__
        class_name = f"_{model_name}Facade"
        desc = RESOURCE_DESCRIPTIONS.get(attr, "")
        lines.append(f"    {attr}: {class_name}")
        if desc:
            lines.append(f'    """{desc}"""')
    for custom in CUSTOM_FACADE_REGISTRY:
        attr = custom.attr_name
        if attr == "scan_logs":
            lines.append(f"    {attr}: ScanLogsFacade")
            lines.append(
                '    """Scan logs facade. Use get_logs() to fetch'
                ' log messages."""'
            )
        else:
            lines.append(
                f"    {attr}: Any"
                "  # Custom facade; add type when known"
            )
    lines.append("")
    lines.append("    _client: APIClient | None")
    lines.append("")
    lines.append("    def __init__(")
    lines.append("        self,")
    lines.append("        api_client: APIClient | None = ...,")
    lines.append("        tenant: str | None = ...,")
    lines.append("        *,")
    lines.append("        timeout: float = ...,")
    lines.append("        content_type: str = ...,")
    lines.append("        accept_encoding: str | None = ...,")
    lines.append("        max_retries: int = ...,")
    lines.append("        base_url: str | None = ...,")
    lines.append("        **client_kwargs: Any,")
    lines.append("    ) -> None: ...")
    lines.append("    def close(self) -> None: ...")
    lines.append("    def __enter__(self) -> Client: ...")
    lines.append("    def __exit__(")
    lines.append("        self,")
    lines.append("        exc_type: type[BaseException] | None,")
    lines.append("        exc_val: BaseException | None,")
    lines.append("        exc_tb: Any,")
    lines.append("    ) -> None: ...")
    lines.append("    def whoami(self) -> str | None:")
    lines.append(
        '        """Return the authenticated identity name,'
        ' or None."""'
    )
    lines.append("        ...")
    lines.append("    def wait_until(")
    lines.append("        self,")
    lines.append("        predicate: Any,")
    lines.append("        timeout: float = ...,")
    lines.append("        poll_interval_max: float = ...,")
    lines.append("    ) -> bool: ...")

    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {out} ({len(lines)} lines)")


if __name__ == "__main__":
    main()
