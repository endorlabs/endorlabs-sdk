#!/usr/bin/env python3
"""
Generate manual baseline for model consistency at depth.

Enumerates implemented resources (from registry), their Pydantic models,
and exposed field paths (at depth). Outputs JSON and optional Markdown
for parity validation of the automated enumerators.

Usage:
    python .github/scripts/generate_manual_baseline.py [--output-dir DIR] [--md]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, get_args, get_origin

# Add repo root and src to path
_repo_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_repo_root))
sys.path.insert(0, str(_repo_root / "src"))

from pydantic import BaseModel


def _get_pydantic_model(t: type) -> type[BaseModel] | None:
    """Resolve type to a Pydantic BaseModel class if possible."""
    origin = get_origin(t)
    if origin is None:
        if isinstance(t, type) and issubclass(t, BaseModel):
            return t
        return None
    # Optional[X] -> Union[X, None]; Union[X, Y]
    if origin is type(None):
        return None
    for arg in get_args(t):
        if isinstance(arg, type) and issubclass(arg, BaseModel):
            return arg
        sub = _get_pydantic_model(arg)
        if sub is not None:
            return sub
    return None


def _model_file_path(model_class: type) -> str:
    """Return source file path relative to repo root."""
    module = getattr(model_class, "__module__", "")
    if not module or not module.startswith("endorlabs."):
        return ""
    # endorlabs.resources.finding -> src/endorlabs/resources/finding.py
    rel = module.replace(".", "/") + ".py"
    return f"src/{rel}" if not rel.startswith("src/") else rel


def _collect_fields_at_depth(
    model_class: type[BaseModel],
    prefix: str = "",
    seen: set[type[BaseModel]] | None = None,
) -> list[dict[str, Any]]:
    """Recursively collect field paths and types. Avoid cycles."""
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
            out.extend(
                _collect_fields_at_depth(nested_model, path, seen.copy())
            )
    seen.discard(model_class)
    return out


def _resource_attr_name(entry: Any) -> str:
    """Get resource name from registry entry (e.g. namespaces -> Namespace)."""
    attr = getattr(entry, "attr_name", "")
    if not attr:
        return ""
    # namespaces -> Namespace, finding_logs -> FindingLog
    return attr.rstrip("s").replace("_", " ").title().replace(" ", "")


def collect_implemented_models_and_fields() -> dict[str, Any]:
    """Use registry and Pydantic introspection. Returns structure for baseline."""
    from endorlabs.registry import RESOURCE_REGISTRY

    resources: list[dict[str, Any]] = []
    all_models: dict[str, list[dict[str, Any]]] = {}

    for entry in RESOURCE_REGISTRY:
        model_class = entry.model_class
        resource_name = _resource_attr_name(entry)
        if not resource_name:
            continue
        file_path = _model_file_path(model_class)
        # Top-level fields (what list/get return): uuid, meta, spec, tenant_meta, etc.
        field_entries = _collect_fields_at_depth(model_class)
        resources.append({
            "resource_name": resource_name,
            "model_class": model_class.__name__,
            "file": file_path,
            "top_level_fields": [f["path"] for f in field_entries if "." not in f["path"]],
            "field_count": len(field_entries),
        })
        all_models[model_class.__name__] = field_entries

    # Add shared base models used by resources (so automation can match)
    from endorlabs.models.base import (
        BaseMeta,
        BaseResource,
        BaseSpec,
        Context,
        TenantMeta,
    )
    for cls in (TenantMeta, Context, BaseMeta, BaseSpec, BaseResource):
        name = cls.__name__
        if name not in all_models:
            all_models[name] = _collect_fields_at_depth(cls)

    return {
        "resources": resources,
        "models": {k: v for k, v in all_models.items()},
        "inconsistencies_note": [
            "TenantMeta/ProcessingStatus redefined in project.py and finding.py (F811).",
            "BaseMeta/BaseSpec use extra='allow'.",
            "Some Specs override detect_schema_drift (FindingSpec, PackageVersionSpec).",
        ],
    }


def collect_exposed_field_paths() -> dict[str, list[str]]:
    """Map resource_name -> list of exposed field paths (at depth)."""
    from endorlabs.registry import RESOURCE_REGISTRY

    out: dict[str, list[str]] = {}
    for entry in RESOURCE_REGISTRY:
        model_class = entry.model_class
        resource_name = _resource_attr_name(entry)
        if not resource_name:
            continue
        field_entries = _collect_fields_at_depth(model_class)
        out[resource_name] = [e["path"] for e in field_entries]
    return out


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate manual baseline for model consistency"
    )
    parser.add_argument(
        "--output-dir",
        default=str(_repo_root / ".tmp"),
        help="Output directory for baseline files",
    )
    parser.add_argument(
        "--md",
        action="store_true",
        help="Also write Markdown report",
    )
    args = parser.parse_args()
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    baseline = collect_implemented_models_and_fields()
    exposed = collect_exposed_field_paths()
    baseline["exposed_fields_by_resource"] = exposed

    json_path = out_dir / "model_consistency_manual_baseline.json"
    with open(json_path, "w") as f:
        json.dump(baseline, f, indent=2)
    print(f"Wrote {json_path}")

    if args.md:
        md_path = out_dir / "model_consistency_manual_baseline.md"
        lines = [
            "# Model Consistency Manual Baseline",
            "",
            "## Implemented resources and models",
            "",
        ]
        for r in baseline["resources"]:
            lines.append(f"- **{r['resource_name']}** (model: `{r['model_class']}`) — `{r['file']}`")
            lines.append(f"  Top-level: {', '.join(r['top_level_fields'])}")
            lines.append("")
        lines.append("## Exposed field paths by resource")
        lines.append("")
        for res_name, paths in exposed.items():
            lines.append(f"### {res_name}")
            lines.append("")
            for p in sorted(paths)[:50]:  # cap for readability
                lines.append(f"- `{p}`")
            if len(paths) > 50:
                lines.append(f"- ... and {len(paths) - 50} more")
            lines.append("")
        lines.append("## Inconsistencies (documented)")
        lines.append("")
        for note in baseline["inconsistencies_note"]:
            lines.append(f"- {note}")
        with open(md_path, "w") as f:
            f.write("\n".join(lines))
        print(f"Wrote {md_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
