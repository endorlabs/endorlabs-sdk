"""Shared helpers for generating facade accessor documentation."""

from __future__ import annotations

from typing import Any

IDENTITY_LANE_ROWS: tuple[tuple[str, str, str], ...] = (
    ("Project", "search_by_name", "Substring on `meta.name`; partial UUID match"),
    ("VectorStore", "search_by_name", "Substring on `meta.name`"),
    ("AuthorizationPolicy", "search_by_claims", "Claims substring match"),
    ("Vulnerability", "search_by_vuln_alias", "Vuln alias substring (OSS scope)"),
)

CUSTOM_FACADE_ROWS: tuple[tuple[str, str, str], ...] = (
    (
        "CallGraphData",
        "decode(package_version, …)",
        "Decoded call graph JSON for a PackageVersion",
    ),
    (
        "CallGraphData",
        "fetch(package_version, …)",
        "Raw CallGraphData wire envelope",
    ),
    (
        "ScanResult",
        "get_logs(scan_result, …)",
        "Scan log messages via ScanLogRequest API",
    ),
)

LISTABLE_HELPER_ROWS: tuple[tuple[str, str], ...] = (
    ("count(**list_kwargs)", "Server-side row count"),
    ("list_groups(*, paths, **kwargs)", "Group-by aggregation buckets"),
    ("latest(sort_by=..., **kwargs)", "Newest single row (`max_pages=1`)"),
    ("latest_created(**kwargs)", "Sugar for `sort_by=\"meta.create_time\"`"),
    ("latest_updated(**kwargs)", "Sugar for `sort_by=\"meta.update_time\"`"),
    ("parent(resource)", "GET parent row via registry `parent_kind`"),
)


def _load_route_edges() -> list[Any]:
    from endorlabs.generated.route_contract import ROUTE_CONTRACT

    return list(ROUTE_CONTRACT.edges)


def edges_for_attr(attr_name: str) -> list[Any]:
    """Route edges whose ``public_method`` is on ``client.{attr_name}``."""
    prefix = f"{attr_name}."
    return [
        edge
        for edge in _load_route_edges()
        if isinstance(getattr(edge, "public_method", None), str)
        and edge.public_method.startswith(prefix)
    ]


def _route_return_hint(edge: Any) -> str:
    kind = getattr(edge, "edge", "")
    if kind == "get_by_uuid":
        return "RouteResult → `.value`"
    if kind == "list_by_attribute":
        return "RouteResult → `.value` (fallback path)"
    return "RouteResult → `.values`"


def render_identity_lane_table() -> str:
    lines = [
        "## Identity lane (`search_by_*`)",
        "",
        "Bounded list discovery; returns `list[T]` (not `RouteResult`).",
        "",
        "| Facade | Method | Match |",
        "|--------|--------|-------|",
    ]
    for facade, method, match in IDENTITY_LANE_ROWS:
        lines.append(f"| `{facade}` | `{facade}.{method}` | {match} |")
    lines.append("")
    return "\n".join(lines)


def render_route_accessor_table() -> str:
    seen_methods: set[str] = set()
    lines = [
        "## Relationship accessors (generated)",
        "",
        "From `route_contract.py`. Return `RouteResult` — use `.values` or `.value`.",
        "Full edge inventory: [resource-routes.md](resource-routes.md).",
        "",
        "| Public method | From → To | Edge id | Wire kind | Returns |",
        "|---------------|-----------|---------|-----------|---------|",
    ]
    for edge in sorted(
        _load_route_edges(),
        key=lambda item: (
            str(getattr(item, "public_method", "")),
            str(getattr(item, "id", "")),
        ),
    ):
        public = getattr(edge, "public_method", None)
        if not isinstance(public, str) or public in seen_methods:
            continue
        seen_methods.add(public)
        lines.append(
            "| "
            f"`{public}` | "
            f"{getattr(edge, 'from_kind', '')} → {getattr(edge, 'to_kind', '')} | "
            f"`{getattr(edge, 'id', '')}` | "
            f"`{getattr(edge, 'edge', '')}` | "
            f"{_route_return_hint(edge)} |"
        )
    lines.append("")
    return "\n".join(lines)


def render_custom_facades_table() -> str:
    lines = [
        "## Custom and wire facades",
        "",
        "| Facade | Method | Purpose |",
        "|--------|--------|---------|",
    ]
    for facade, method, purpose in CUSTOM_FACADE_ROWS:
        lines.append(f"| `{facade}` | `{method}` | {purpose} |")
    lines.append("")
    return "\n".join(lines)


def render_listable_helpers_table() -> str:
    lines = [
        "## Universal list helpers (`ListableFacade`)",
        "",
        "Available on every listable registry facade unless noted.",
        "",
        "| Method | Purpose |",
        "|--------|---------|",
    ]
    for method, purpose in LISTABLE_HELPER_ROWS:
        lines.append(f"| `{method}` | {purpose} |")
    lines.append("")
    lines.append(
        "`list(count=True)` emits `DeprecationWarning` and delegates to `count()`."
    )
    lines.append("")
    return "\n".join(lines)


def render_resource_facade_helpers_section(attr_name: str) -> str | None:
    """Markdown section for a per-resource page, or None when empty."""
    section_lines: list[str] = []

    identity = [row for row in IDENTITY_LANE_ROWS if row[0] == attr_name]
    if identity:
        section_lines.extend(["## Facade helpers", ""])
        section_lines.append("### Identity lane")
        section_lines.append("")
        for _, method, match in identity:
            section_lines.append(f"- **`{attr_name}.{method}(query, …)`** — {match}")
        section_lines.append("")

    edges = edges_for_attr(attr_name)
    if edges:
        if not section_lines:
            section_lines.extend(["## Facade helpers", ""])
        section_lines.extend(
            [
                "### Relationship accessors",
                "",
                "| Method | Edge id | Wire kind | Returns |",
                "|--------|---------|-----------|---------|",
            ]
        )
        seen: set[str] = set()
        for edge in sorted(edges, key=lambda item: str(getattr(item, "id", ""))):
            public = getattr(edge, "public_method", None)
            if not isinstance(public, str):
                continue
            method_suffix = public.split(".", 1)[-1]
            if method_suffix in seen:
                continue
            seen.add(method_suffix)
            section_lines.append(
                "| "
                f"`{method_suffix}(…)` | "
                f"`{getattr(edge, 'id', '')}` | "
                f"`{getattr(edge, 'edge', '')}` | "
                f"{_route_return_hint(edge)} |"
            )
        section_lines.extend(
            [
                "",
                "See [resource-routes.md](../resource-routes.md) and "
                "[facade-helpers.md](../../guides/facade-helpers.md).",
                "",
            ]
        )

    custom = [row for row in CUSTOM_FACADE_ROWS if row[0] == attr_name]
    if custom:
        if not section_lines:
            section_lines.extend(["## Facade helpers", ""])
        section_lines.append("### Wire helpers")
        section_lines.append("")
        for _, method, purpose in custom:
            section_lines.append(f"- **`{method}`** — {purpose}")
        section_lines.append("")

    if not section_lines:
        return None
    return "\n".join(section_lines)
