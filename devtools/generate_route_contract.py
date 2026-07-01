"""Generate route contract artifacts from overlay YAML + partition profile."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from sync.path_safety import find_repo_root

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore[assignment]


def _load_yaml(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    if yaml is None:
        raise RuntimeError("PyYAML required: uv sync --group dev")
    payload = yaml.safe_load(text)
    if not isinstance(payload, dict):
        raise ValueError(f"Expected mapping in {path}")
    return payload


def _edge_list(contract: dict[str, Any]) -> list[dict[str, Any]]:
    edges = contract.get("edges")
    if not isinstance(edges, list):
        raise ValueError("contract must contain edges list")
    return [e for e in edges if isinstance(e, dict)]


def _load_registry_resources(repo: Path) -> list[dict[str, Any]]:
    sys.path.insert(0, str(repo / "src"))
    try:
        from endorlabs.generated.registry_contract import RUNTIME_REGISTRY_CONTRACT
    finally:
        if sys.path[0] == str(repo / "src"):
            sys.path.pop(0)
    resources = RUNTIME_REGISTRY_CONTRACT.get("resources")
    if not isinstance(resources, list):
        raise ValueError("RUNTIME_REGISTRY_CONTRACT.resources must be a list")
    return [r for r in resources if isinstance(r, dict)]


def _project_filter_by_kind(manual_edges: list[dict[str, Any]]) -> dict[str, str]:
    """Map to_kind -> filter_field from project-scoped list_by_uuid_field edges."""
    out: dict[str, str] = {}
    for edge in manual_edges:
        if edge.get("from_kind") != "Project":
            continue
        if edge.get("edge") != "list_by_uuid_field":
            continue
        kind = edge.get("to_kind")
        field = edge.get("filter_field")
        if isinstance(kind, str) and isinstance(field, str):
            out[kind] = field
    return out


def _supported_ops(row: dict[str, Any]) -> set[str]:
    ops = row.get("supported_ops")
    if not isinstance(ops, list):
        return set()
    return {str(op) for op in ops if isinstance(op, str)}


def _generate_partition_edges(
    *,
    manual_edges: list[dict[str, Any]],
    profile: dict[str, Any],
    registry_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    defaults = profile.get("defaults")
    if not isinstance(defaults, dict):
        raise ValueError("route_partition_targets.yaml must contain defaults mapping")
    targets_raw = profile.get("targets")
    if not isinstance(targets_raw, list):
        raise ValueError("route_partition_targets.yaml must contain targets list")

    registry_by_kind = {
        str(row["attr_name"]): row
        for row in registry_rows
        if isinstance(row.get("attr_name"), str)
    }
    inherited_project_filter = _project_filter_by_kind(manual_edges)

    generated: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    seen_methods: set[str] = set()

    for item in targets_raw:
        if not isinstance(item, dict):
            continue
        kind = item.get("kind")
        edge_id = item.get("edge_id")
        if not isinstance(kind, str) or not isinstance(edge_id, str):
            raise ValueError(f"partition target must have kind and edge_id: {item!r}")
        if edge_id in seen_ids:
            raise ValueError(f"duplicate partition edge_id: {edge_id!r}")
        seen_ids.add(edge_id)

        row = registry_by_kind.get(kind)
        if row is None:
            raise ValueError(f"partition target {kind!r} not in registry contract")
        if "list" not in _supported_ops(row):
            raise ValueError(f"partition target {kind!r} is not listable")

        public_method = f"{kind}.list_for_context"
        if public_method in seen_methods:
            raise ValueError(f"duplicate partition public_method: {public_method!r}")
        seen_methods.add(public_method)

        project_field = item.get("project_list_filter_field")
        if project_field is None:
            project_field = inherited_project_filter.get(kind)
        elif not isinstance(project_field, str):
            raise ValueError(
                f"project_list_filter_field for {kind!r} must be a string or null"
            )

        uuid_tpl = str(defaults.get("project_uuid_from", "source.meta.parent_uuid"))
        edge: dict[str, Any] = {
            "id": edge_id,
            "from_kind": str(defaults.get("from_kind", "ScanResult")),
            "to_kind": kind,
            "edge": str(defaults.get("edge", "list_by_context_partition")),
            "tier": str(defaults.get("tier", "B")),
            "public_method": public_method,
            "context_from": str(defaults.get("context_from", "context")),
            "namespace_from": str(defaults.get("namespace_from", "source")),
        }
        if isinstance(project_field, str) and project_field.strip():
            edge["also_filter"] = f'{project_field}==\"{{{uuid_tpl}}}\"'
        generated.append(edge)

    return generated


def _merge_edge_lists(
    manual: list[dict[str, Any]], generated: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    seen_ids: set[str] = set()
    merged: list[dict[str, Any]] = []
    for edge in [*manual, *generated]:
        edge_id = str(edge.get("id", ""))
        if not edge_id:
            raise ValueError(f"edge missing id: {edge!r}")
        if edge_id in seen_ids:
            raise ValueError(f"duplicate route edge id: {edge_id!r}")
        seen_ids.add(edge_id)
        merged.append(edge)
    return merged


def build_contract(repo: Path) -> dict[str, Any]:
    profiles = repo / "devtools" / "model_sync_profiles"
    manual = _load_yaml(profiles / "route_contract_overlay.yaml")
    partition_profile = _load_yaml(profiles / "route_partition_targets.yaml")
    manual_edges = _edge_list(manual)
    registry_rows = _load_registry_resources(repo)
    generated_edges = _generate_partition_edges(
        manual_edges=manual_edges,
        profile=partition_profile,
        registry_rows=registry_rows,
    )
    return {"edges": _merge_edge_lists(manual_edges, generated_edges)}


def _build_route_table(edges: list[dict[str, Any]]) -> dict[str, tuple[str, ...]]:
    table: dict[str, list[str]] = {}
    for edge in edges:
        public = edge.get("public_method")
        if not isinstance(public, str) or "." not in public:
            continue
        attr, _ = public.split(".", 1)
        table.setdefault(attr, []).append(str(edge["id"]))
    return {k: tuple(v) for k, v in sorted(table.items())}


def _build_relationship_map(
    edges: list[dict[str, Any]],
) -> list[tuple[str, str, str, str, str]]:
    rows: list[tuple[str, str, str, str, str]] = []
    for edge in edges:
        public = edge.get("public_method")
        if not isinstance(public, str):
            continue
        rows.append(
            (
                str(edge.get("from_kind", "")),
                str(edge.get("to_kind", "")),
                public,
                str(edge.get("id", "")),
                str(edge.get("edge", "")),
            )
        )
    return sorted(rows, key=lambda r: (r[2], r[3]))


def render_module(contract: dict[str, Any]) -> str:
    edges = _edge_list(contract)
    json_text = json.dumps({"edges": edges}, indent=2)
    table = _build_route_table(edges)
    rel_map = _build_relationship_map(edges)
    return f'''# Auto-generated by devtools/generate_route_contract.py — do not edit by hand.
"""Generated route contract for generated accessor helper wiring."""

from __future__ import annotations

import json

from endorlabs.operations.route_contract import RouteContract

ROUTE_CONTRACT_JSON = {json_text!r}

ROUTE_CONTRACT: RouteContract = RouteContract.from_dict(json.loads(ROUTE_CONTRACT_JSON))

ROUTE_TABLE_BY_ATTR: dict[str, tuple[str, ...]] = {repr(table)}

ROUTE_RELATIONSHIP_MAP: tuple[tuple[str, str, str, str, str], ...] = {repr(tuple(rel_map))}
'''


def render_markdown(contract: dict[str, Any]) -> str:
    edges = _edge_list(contract)
    lines = [
        "# Resource route map (generated)",
        "",
        "Generated **relationship accessor** edges between first-class facades. "
        "Regenerate with `uv run python devtools/generate_route_contract.py`.",
        "",
        "Manual edges: `devtools/model_sync_profiles/route_contract_overlay.yaml`.",
        "Partition edges: `devtools/model_sync_profiles/route_partition_targets.yaml`.",
        "",
        "## Relationship table",
        "",
        "| From | To | Public method | Edge id | Wire kind | Tier |",
        "|------|-----|---------------|---------|-----------|------|",
    ]
    for edge in edges:
        public = edge.get("public_method", "")
        lines.append(
            f"| {edge.get('from_kind', '')} | {edge.get('to_kind', '')} | "
            f"`{public}` | `{edge.get('id', '')}` | `{edge.get('edge', '')}` | "
            f"{edge.get('tier', 'B')} |"
        )
    lines.extend(
        [
            "",
            "## Usage",
            "",
            "Generated list accessors (`list_by_project`, `list_for_context`, …) return "
            "`list[T]` like `.list()`. Stitch accessors (`to_dependency_metadata`, …) "
            "return `RouteResult` — use `.value` / `.single` and inspect "
            "`.edge_used` / `.warnings`. Namespace is taken from the source resource "
            "unless `namespace=` is passed.",
            "",
            "```python",
            "projects = client.Project.search_by_name('my-repo', namespace=ns, max_pages=2)",
            "project = projects[0] if projects else None",
            "findings = client.Finding.list_by_project(project, max_pages=1)",
            "scans = client.ScanResult.list_by_project(",
            "    project, max_pages=1, sort_by='meta.create_time', desc=True)",
            "if scans:",
            "    by_context = client.Finding.list_for_context(scans[0], max_pages=1)",
            "dm = client.Finding.to_dependency_metadata(finding_row)",
            "```",
            "",
            "See [facade-helpers.md](../guides/facade-helpers.md) and "
            "[contracts.md](../contracts.md#generated-accessor-helpers).",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    repo = find_repo_root(start=Path(__file__).resolve().parent)
    contract = build_contract(repo)
    py_out = repo / "src" / "endorlabs" / "generated" / "route_contract.py"
    md_out = repo / "docs" / "generated-reference" / "resource-routes.md"
    golden_out = repo / "tests" / "fixtures" / "routes" / "golden_edges.json"
    py_out.write_text(render_module(contract), encoding="utf-8")
    md_out.write_text(render_markdown(contract), encoding="utf-8")
    golden_out.write_text(
        json.dumps(contract, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {py_out.relative_to(repo)}")
    print(f"Wrote {md_out.relative_to(repo)}")
    print(f"Wrote {golden_out.relative_to(repo)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
