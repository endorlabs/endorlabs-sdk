"""Model consistency: SDK Pydantic vs OpenAPI spec.

Enumerates SDK models (inheritance/modularity) and spec definitions (noisy but
accurate), computes inheritance-aware diff (shared base enumerated once;
per-resource extra excludes base-derived paths), and generates text/JSON reports.
"""

from __future__ import annotations

import json
import logging
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, get_args, get_origin

logger = logging.getLogger(__name__)

# Default spec location (same as sync script and schema-drift workflow)
DEFAULT_SPEC_PATH = "external_docs/openapi-swagger.json"
DEFAULT_SPEC_URL = "https://api.endorlabs.com/download/openapiv2.swagger.json"

# Shared SDK models (enumerated once for inheritance-aware diff)
SHARED_MODEL_NAMES = frozenset(
    {
        "BaseMeta",
        "BaseSpec",
        "TenantMeta",
        "Context",
        "BaseResource",
    }
)

# Spec def -> SDK model (shared components; spec v1Meta -> BaseMeta)
SPEC_TO_SDK_SHARED: dict[str, str] = {
    "v1Meta": "BaseMeta",
    "v1TenantMeta": "TenantMeta",
    "v1Context": "Context",
}

# SDK field aliases -> shared path name (for "extra" attribution).
# Greenfield convention: use Python name = spec key (context, processing_status,
# index_data) so no entries needed for shared fields. Keep empty; add only if
# a future resource uses a prefixed Python name with alias for a shared concept.
SDK_FIELD_ALIAS_TO_SHARED: dict[str, str] = {}


# --- SDK enumerator ---


def _get_pydantic_model(t: type) -> type[Any] | None:
    """Resolve type to a Pydantic BaseModel class if possible."""
    try:
        from pydantic import BaseModel
    except ImportError:
        return None
    origin = get_origin(t)
    if origin is None:
        if isinstance(t, type) and issubclass(t, BaseModel):
            return t
        return None
    if origin is type(None):
        return None
    for arg in get_args(t):
        if isinstance(arg, type) and issubclass(arg, BaseModel):
            return arg
        sub = _get_pydantic_model(arg)
        if sub is not None:
            return sub
    return None


def _collect_fields_at_depth(
    model_class: type[Any],
    prefix: str = "",
    seen: set[type[Any]] | None = None,
) -> list[dict[str, Any]]:
    """Recursively collect field paths and types. Avoid cycles."""
    try:
        from pydantic import BaseModel
    except ImportError:
        return []
    seen = seen or set()
    if model_class in seen:
        return []
    if not issubclass(model_class, BaseModel):
        return []
    seen.add(model_class)
    out: list[dict[str, Any]] = []
    fields = getattr(model_class, "model_fields", {})
    annotations = getattr(model_class, "__annotations__", {})
    for name, info in fields.items():
        path = f"{prefix}.{name}" if prefix else name
        ann = getattr(info, "annotation", None) or annotations.get(name, Any)
        if isinstance(ann, str):
            type_str = ann
            nested_model = None
        else:
            type_str = getattr(ann, "__name__", str(ann))
            nested_model = _get_pydantic_model(ann)
        out.append({"path": path, "type": type_str})
        if nested_model is not None and nested_model is not model_class:
            out.extend(_collect_fields_at_depth(nested_model, path, seen.copy()))
    seen.discard(model_class)
    return out


def enumerate_sdk_models_flat_paths() -> dict[str, list[str]]:
    """Enumerate SDK models and field paths (at depth) using Pydantic.

    Returns dict mapping model name (e.g. Finding, FindingSpec, BaseMeta) to list of
    dot-separated field paths. Uses registry for resources and adds shared base models.
    """
    try:
        from endorlabs.models.base import (
            BaseMeta,
            BaseResource,
            BaseSpec,
            Context,
            TenantMeta,
        )
        from endorlabs.registry import RESOURCE_REGISTRY
    except ImportError:
        return {}

    result: dict[str, list[str]] = {}
    for entry in RESOURCE_REGISTRY:
        model_class = entry.model_class
        name = getattr(model_class, "__name__", None)
        if not name:
            continue
        field_entries = _collect_fields_at_depth(model_class)
        result[name] = [e["path"] for e in field_entries]

    for cls in (TenantMeta, Context, BaseMeta, BaseSpec, BaseResource):
        name = cls.__name__
        if name not in result:
            result[name] = [e["path"] for e in _collect_fields_at_depth(cls)]

    return result


def get_shared_sdk_paths(sdk_models: dict[str, list[str]] | None = None) -> set[str]:
    """Return the set of SDK paths that come from shared base (BaseResource, BaseSpec).

    Enumerate BaseResource and BaseSpec once; for BaseSpec paths prefix with "spec."
    so that spec.exception, spec.finding, spec.notification are treated as shared.
    Alias variants (when SDK_FIELD_ALIAS_TO_SHARED has entries) are treated as shared.
    """
    if sdk_models is None:
        sdk_models = enumerate_sdk_models_flat_paths()
    shared_resource_paths = set(sdk_models.get("BaseResource", []))
    shared_spec_paths = set(sdk_models.get("BaseSpec", []))
    shared_sdk_paths = shared_resource_paths | {"spec." + p for p in shared_spec_paths}
    # Add alias variants so alias fields are excluded from per-resource extra
    for sdk_name, api_name in SDK_FIELD_ALIAS_TO_SHARED.items():
        for p in list(shared_sdk_paths):
            if p == api_name:
                shared_sdk_paths.add(sdk_name)
            elif p.startswith(api_name + "."):
                suffix = p[len(api_name) + 1 :]
                shared_sdk_paths.add(sdk_name + "." + suffix)
    return shared_sdk_paths


def sdk_model_name_to_spec_definition(sdk_name: str) -> str:
    """Map SDK model name to OpenAPI definition name (v1X)."""
    return f"v1{sdk_name}"


def spec_definition_to_sdk_model_name(spec_name: str) -> str | None:
    """Map OpenAPI def name (v1X) to SDK model name; e.g. v1Meta -> BaseMeta."""
    if spec_name in SPEC_TO_SDK_SHARED:
        return SPEC_TO_SDK_SHARED[spec_name]
    if spec_name.startswith("v1") and len(spec_name) > 2:
        return spec_name[2:]
    return None


# --- Spec enumerator ---


def _sdk_to_spec_definition_names() -> set[str]:
    """Return set of definition names we care about (v1* for implemented resources)."""
    try:
        from endorlabs.registry import RESOURCE_REGISTRY
    except Exception:
        resource_models = [
            "Namespace",
            "Project",
            "Finding",
            "Repository",
            "RepositoryVersion",
            "Policy",
            "AuthorizationPolicy",
            "PackageVersion",
            "PackageLicense",
            "DependencyMetadata",
            "Installation",
            "ScanProfile",
            "ScanResult",
            "LinterResult",
            "Metric",
            "SemgrepRule",
            "APIKey",
            "AuditLog",
            "FindingLog",
        ]
        return (
            {f"v1{m}" for m in resource_models}
            | {f"v1{m}Spec" for m in resource_models if m != "APIKey"}
            | {"v1Meta", "v1TenantMeta", "v1Context"}
        )
    names: set[str] = {"v1Meta", "v1TenantMeta", "v1Context"}
    for entry in RESOURCE_REGISTRY:
        model_class = getattr(entry, "model_class", None)
        if model_class is None:
            continue
        name = getattr(model_class, "__name__", "")
        if name:
            names.add(f"v1{name}")
            if name not in ("APIKey", "AuditLog"):
                names.add(f"v1{name}Spec")
    return names


def load_spec(
    path: str | Path | None = None,
    url: str | None = None,
) -> dict[str, Any]:
    """Load OpenAPI/Swagger JSON from file or URL."""
    if path is not None:
        p = Path(path)
        if p.exists():
            with open(p, encoding="utf-8") as f:
                return json.load(f)
    if url is not None:
        with urllib.request.urlopen(url, timeout=60) as resp:
            return json.load(resp)
    p = Path(DEFAULT_SPEC_PATH)
    if p.exists():
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    with urllib.request.urlopen(DEFAULT_SPEC_URL, timeout=60) as resp:
        return json.load(resp)


def _resolve_ref(spec: dict[str, Any], ref: str) -> dict[str, Any] | None:
    """Resolve #/definitions/X to definition object."""
    if not ref.startswith("#/definitions/"):
        return None
    key = ref.split("/")[-1]
    defs = spec.get("definitions") or {}
    return defs.get(key)


def _collect_definition_paths_flat(
    spec: dict[str, Any],
    definition: dict[str, Any],
    prefix: str = "",
    visited: set[str] | None = None,
) -> list[str]:
    """Recursively collect all field path strings; resolve $ref."""
    visited = visited or set()
    out: list[str] = []
    props = definition.get("properties") or {}
    for name, prop in props.items():
        path = f"{prefix}.{name}" if prefix else name
        out.append(path)
        if isinstance(prop, dict) and "$ref" in prop:
            ref = prop["$ref"]
            if ref in visited:
                continue
            visited.add(ref)
            resolved = _resolve_ref(spec, ref)
            if resolved:
                out.extend(
                    _collect_definition_paths_flat(spec, resolved, path, visited)
                )
            visited.discard(ref)
    return out


def enumerate_spec_fields_flat(
    spec: dict[str, Any],
    definition_names: set[str] | None = None,
) -> dict[str, list[str]]:
    """Enumerate all field paths (strings) per definition for diffing.

    Resolves $ref. Returns e.g. {"v1Finding": ["uuid", "meta", "meta.name", ...], ...}.
    """
    definition_names = definition_names or _sdk_to_spec_definition_names()
    defs = spec.get("definitions") or {}
    result: dict[str, list[str]] = {}
    for def_name in definition_names:
        definition = defs.get(def_name)
        if not definition or not isinstance(definition, dict):
            continue
        result[def_name] = _collect_definition_paths_flat(spec, definition)
    return result


def _prop_ref_or_type(prop: dict[str, Any]) -> str:
    """Return ref key (e.g. v1Context) or type string for a property."""
    if isinstance(prop, dict) and "$ref" in prop:
        ref = prop["$ref"]
        if ref.startswith("#/definitions/"):
            return ref.split("/")[-1]
        return ref
    if isinstance(prop, dict) and "type" in prop:
        return str(prop["type"])
    return "object"


def enumerate_spec_top_level_refs(
    spec: dict[str, Any],
    definition_names: set[str] | None = None,
) -> dict[str, list[tuple[str, str]]]:
    """Enumerate top-level property names and their resolved ref/type per definition.

    Returns mapping: definition_name -> list of (property_name, resolved_ref_or_type).
    Uses definition_names or _sdk_to_spec_definition_names() for scope.
    """
    definition_names = definition_names or _sdk_to_spec_definition_names()
    defs = spec.get("definitions") or {}
    result: dict[str, list[tuple[str, str]]] = {}
    for def_name in definition_names:
        definition = defs.get(def_name)
        if not definition or not isinstance(definition, dict):
            continue
        props = definition.get("properties") or {}
        result[def_name] = [
            (name, _prop_ref_or_type(prop)) for name, prop in props.items()
        ]
    return result


def compute_attribute_overlap_report(
    spec: dict[str, Any],
    definition_names: set[str] | None = None,
) -> dict[str, Any]:
    """Compute attribute name overlap and same-meaning / collisions across definitions.

    Builds reverse index: attribute_name -> list of (definition, ref). Reports:
    - attribute_overlap: names that appear in at least two definitions.
    - same_meaning: overlap names where all definitions use the same ref.
    - collisions: overlap names where at least two different refs appear.
    """
    top_level = enumerate_spec_top_level_refs(spec, definition_names)
    # Reverse index: attribute_name -> list of {definition, ref}
    by_attr: dict[str, list[dict[str, str]]] = {}
    for def_name, pairs in top_level.items():
        for prop_name, ref_or_type in pairs:
            if prop_name not in by_attr:
                by_attr[prop_name] = []
            by_attr[prop_name].append({"definition": def_name, "ref": ref_or_type})

    # Only names that appear in at least two definitions
    attribute_overlap = {
        name: entries for name, entries in by_attr.items() if len(entries) >= 2
    }
    same_meaning: list[str] = []
    collisions: list[str] = []
    for name, entries in attribute_overlap.items():
        refs = {e["ref"] for e in entries}
        if len(refs) == 1:
            same_meaning.append(name)
        else:
            collisions.append(name)

    return {
        "attribute_overlap": attribute_overlap,
        "same_meaning": sorted(same_meaning),
        "collisions": sorted(collisions),
    }


# --- Flatten collision (getter/setter namespace) ---


def path_to_flattened(path: str) -> str:
    """Convert update_mask path to flattened kwarg/getter name.

    Mirrors BaseResource._path_to_kwarg: processing_status.X -> X;
    all other paths -> path with dots replaced by underscores.
    """
    if path.startswith("processing_status."):
        return path.split(".", 1)[1]
    return path.replace(".", "_")


def compute_flatten_collision_report(
    spec: dict[str, Any],
    definition_names: set[str] | None = None,
) -> dict[str, Any]:
    """Compute within-definition collisions when flattening paths to kwarg names.

    For each definition, enumerates all field paths (via enumerate_spec_fields_flat),
    maps each path to a flattened name (path_to_flattened). A collision is when
    two or more paths in the same definition map to the same flattened name.

    Returns dict with by_definition, collisions (flat list), and summary.
    """
    spec_fields = enumerate_spec_fields_flat(spec, definition_names)
    by_definition: dict[str, dict[str, Any]] = {}
    all_collisions: list[dict[str, Any]] = []
    total_paths = 0

    for def_name, paths in spec_fields.items():
        path_to_flat: dict[str, str] = {}
        flat_to_paths: dict[str, list[str]] = {}
        for p in paths:
            flat = path_to_flattened(p)
            path_to_flat[p] = flat
            flat_to_paths.setdefault(flat, []).append(p)
        def_collisions = [
            {"flattened_name": name, "paths": path_list}
            for name, path_list in flat_to_paths.items()
            if len(path_list) > 1
        ]
        all_collisions.extend(
            [
                {
                    "definition": def_name,
                    "flattened_name": c["flattened_name"],
                    "paths": c["paths"],
                }
                for c in def_collisions
            ]
        )
        by_definition[def_name] = {
            "path_to_flattened": path_to_flat,
            "flattened_to_paths": flat_to_paths,
            "collisions": def_collisions,
        }
        total_paths += len(paths)

    definitions_with_collisions = sum(
        1 for d in by_definition.values() if d["collisions"]
    )
    collision_flattened_names = sorted({c["flattened_name"] for c in all_collisions})

    return {
        "by_definition": by_definition,
        "collisions": all_collisions,
        "summary": {
            "definitions_scanned": len(by_definition),
            "total_paths": total_paths,
            "definitions_with_collisions": definitions_with_collisions,
            "total_collisions": len(all_collisions),
            "collision_flattened_names": collision_flattened_names,
        },
    }


# --- Diff (inheritance-aware) and grouping ---


def _normalize_path_for_shared(path: str) -> str:
    """Return shared path if path is an alias; else return path unchanged."""
    for sdk_name, api_name in SDK_FIELD_ALIAS_TO_SHARED.items():
        if path == sdk_name:
            return api_name
        if path.startswith(sdk_name + "."):
            return api_name + "." + path[len(sdk_name) + 1 :]
    return path


def _group_by_resource(by_resource: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """Group by_resource into shared_components and by_resource_name."""
    shared_components: dict[str, dict[str, Any]] = {}
    by_resource_name: dict[str, dict[str, Any]] = {}

    for sdk_name, data in by_resource.items():
        if sdk_name in SHARED_MODEL_NAMES:
            shared_components[sdk_name] = data
        else:
            resource_name = sdk_name[:-4] if sdk_name.endswith("Spec") else sdk_name
            if resource_name not in by_resource_name:
                by_resource_name[resource_name] = {"models": {}}
            by_resource_name[resource_name]["models"][sdk_name] = data

    return {
        "shared_components": shared_components,
        "by_resource": by_resource_name,
    }


def compute_model_consistency_diff(
    sdk_models: dict[str, list[str]],
    spec_fields: dict[str, list[str]],
    *,
    inheritance_aware: bool = True,
) -> dict[str, Any]:
    """Compare SDK model field paths (Pydantic) vs spec field paths (OpenAPI).

    When inheritance_aware is True, per-resource extra_in_sdk excludes paths that
    belong to shared base (BaseResource, BaseSpec), so base-derived paths are
    not repeated for every resource.
    """
    shared_sdk_paths: set[str] = set()
    if inheritance_aware:
        shared_sdk_paths = get_shared_sdk_paths(sdk_models)

    missing_in_sdk: list[dict[str, Any]] = []
    extra_in_sdk: list[dict[str, Any]] = []
    by_resource: dict[str, dict[str, Any]] = {}

    for spec_name, spec_paths in spec_fields.items():
        sdk_name = spec_definition_to_sdk_model_name(spec_name)
        if sdk_name is None:
            continue
        sdk_paths_list = sdk_models.get(sdk_name, [])
        spec_set = set(spec_paths)
        sdk_set = set(sdk_paths_list)
        missing = sorted(spec_set - sdk_set)
        raw_extra = sdk_set - spec_set
        if inheritance_aware:
            # Exclude paths that are from shared base (or their alias)
            extra_set = set()
            for p in raw_extra:
                norm = _normalize_path_for_shared(p)
                if norm not in shared_sdk_paths and p not in shared_sdk_paths:
                    extra_set.add(p)
            extra = sorted(extra_set)
        else:
            extra = sorted(raw_extra)
        if missing:
            missing_in_sdk.extend(
                {"model": spec_name, "sdk_model": sdk_name, "path": p} for p in missing
            )
        if extra:
            extra_in_sdk.extend(
                {"model": spec_name, "sdk_model": sdk_name, "path": p} for p in extra
            )
        by_resource[sdk_name] = {
            "missing_in_sdk": missing,
            "extra_in_sdk": extra,
            "spec_path_count": len(spec_paths),
            "sdk_path_count": len(sdk_paths_list),
        }

    grouped = _group_by_resource(by_resource)
    result: dict[str, Any] = {
        "missing_in_sdk": missing_in_sdk,
        "extra_in_sdk": extra_in_sdk,
        "by_resource": by_resource,
        "grouped": grouped,
    }
    if inheritance_aware:
        result["shared_sdk_paths_count"] = len(shared_sdk_paths)
    return result


# --- Report generation ---


def run_model_consistency_report(
    spec_path: str | Path | None = None,
    spec_url: str | None = None,
    output_file: str | Path = "model_consistency_report",
    output_format: str = "json",
    *,
    inheritance_aware: bool = True,
) -> dict[str, Any]:
    """Run model consistency workflow: enumerate SDK and spec, diff, write report.

    When inheritance_aware is True, per-resource extra excludes shared base paths.
    Output is text or JSON.
    """
    logger.info("Loading OpenAPI spec...")
    spec = load_spec(path=spec_path, url=spec_url)
    spec_fields = enumerate_spec_fields_flat(spec)
    logger.info("Enumerating SDK models (Pydantic)...")
    sdk_models = enumerate_sdk_models_flat_paths()
    diff = compute_model_consistency_diff(
        sdk_models, spec_fields, inheritance_aware=inheritance_aware
    )
    overlap_report = compute_attribute_overlap_report(spec)

    report: dict[str, Any] = {
        "timestamp": datetime.now(UTC).isoformat(),
        "model_consistency": diff,
        "attribute_overlap_report": overlap_report,
        "summary": {
            "missing_in_sdk_count": len(diff["missing_in_sdk"]),
            "extra_in_sdk_count": len(diff["extra_in_sdk"]),
            "resources_compared": len(diff["by_resource"]),
            "overlap_attribute_count": len(overlap_report["attribute_overlap"]),
            "same_meaning_count": len(overlap_report["same_meaning"]),
            "collisions_count": len(overlap_report["collisions"]),
        },
    }
    if inheritance_aware and "shared_sdk_paths_count" in diff:
        report["summary"]["shared_sdk_paths_count"] = diff["shared_sdk_paths_count"]

    out_path = Path(output_file)
    if output_format.lower() in ("text", "txt"):
        grouped = diff["grouped"]
        summary = report["summary"]
        overlap = report.get("attribute_overlap_report", {})
        same_meaning = overlap.get("same_meaning", [])
        collisions = overlap.get("collisions", [])
        lines = [
            "# Model Consistency Report",
            "",
            f"Generated: {report['timestamp']}",
            "",
            "## Summary",
            "",
            f"- Missing in SDK (spec, not Pydantic): {summary['missing_in_sdk_count']}",
            f"- Extra in SDK (resource-specific): {summary['extra_in_sdk_count']}",
            f"- Resources compared: {summary['resources_compared']}",
            f"- Overlap (2+ defs): {summary.get('overlap_attribute_count', 0)}",
            f"- Same meaning: {summary.get('same_meaning_count', 0)}",
            f"- Collisions: {summary.get('collisions_count', 0)}",
            "",
            "## Attribute overlap (same meaning / collisions)",
            "",
            "Same-meaning attributes (Tier 3 alias candidates):",
            "",
        ]
        lines.extend(f"  - {a}" for a in same_meaning)
        lines.extend(
            [
                "",
                "Collisions (same key, different type across definitions):",
                "",
            ]
        )
        lines.extend(f"  - {a}" for a in collisions)
        lines.extend(["", "## Shared components", ""])
        for model_name in sorted(grouped["shared_components"].keys()):
            data = grouped["shared_components"][model_name]
            missing = data["missing_in_sdk"]
            extra = data["extra_in_sdk"]
            lines.append(f"### {model_name}")
            lines.append("")
            lines.append(f"- Missing in SDK: {len(missing)}")
            lines.extend(f"  - {p}" for p in missing[:30])
            if len(missing) > 30:
                lines.append(f"  - ... and {len(missing) - 30} more")
            lines.append(f"- Extra in SDK: {len(extra)}")
            lines.extend(f"  - {p}" for p in extra[:30])
            if len(extra) > 30:
                lines.append(f"  - ... and {len(extra) - 30} more")
            lines.append("")

        lines.extend(["## By resource", ""])
        for resource_name in sorted(grouped["by_resource"].keys()):
            resource_data = grouped["by_resource"][resource_name]
            models = resource_data.get("models", {})
            lines.append(f"### {resource_name}")
            lines.append("")
            for model_name in sorted(models.keys()):
                data = models[model_name]
                missing = data["missing_in_sdk"]
                extra = data["extra_in_sdk"]
                lines.append(f"#### {model_name}")
                lines.append("")
                lines.append(f"- Missing in SDK: {len(missing)}")
                lines.extend(f"  - {p}" for p in missing[:25])
                if len(missing) > 25:
                    lines.append(f"  - ... and {len(missing) - 25} more")
                lines.append(f"- Extra in SDK (resource-specific): {len(extra)}")
                lines.extend(f"  - {p}" for p in extra[:25])
                if len(extra) > 25:
                    lines.append(f"  - ... and {len(extra) - 25} more")
                lines.append("")
            lines.append("")

        text_path = (
            out_path if str(out_path).endswith(".txt") else Path(str(out_path) + ".txt")
        )
        text_path.write_text("\n".join(lines), encoding="utf-8")
        logger.info("Wrote %s", text_path)
    else:
        json_path = (
            out_path
            if str(out_path).endswith(".json")
            else Path(str(out_path) + ".json")
        )
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)
        logger.info("Wrote %s", json_path)

    return report
