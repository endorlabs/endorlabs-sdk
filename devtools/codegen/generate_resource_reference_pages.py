"""Generate per-resource reference pages under docs/generated-reference/resources/."""
# ruff: noqa: E501, C901, D103, TRY004, PERF401, I001

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from endorlabs.registry import RESOURCE_REGISTRY  # noqa: E402
from endorlabs.registry_overlay import merge_generated_contract_with_overlay  # noqa: E402

from doc_facade_helpers import render_resource_facade_helpers_section  # noqa: E402

logger = logging.getLogger(__name__)

OUTPUT_DIR = REPO_ROOT / "docs" / "generated-reference" / "resources"
RESOURCE_INDEX_PATH = REPO_ROOT / "src" / "endorlabs" / "generated" / "resource_index.json"
DESCRIPTIONS_PATH = (
    REPO_ROOT / "devtools" / "codegen" / "model_sync_profiles" / "resource_descriptions.json"
)
RELATED_PATH = REPO_ROOT / "devtools" / "codegen" / "model_sync_profiles" / "resource_related.json"

SDK_OP_ORDER = ("list", "get", "create", "update", "delete")


def _load_contract_resources() -> dict[str, dict[str, Any]]:
    from endorlabs.generated.registry_contract import RUNTIME_REGISTRY_CONTRACT

    resources = RUNTIME_REGISTRY_CONTRACT.get("resources")
    if not isinstance(resources, list):
        raise RuntimeError("registry_contract.resources must be a list")
    merged = merge_generated_contract_with_overlay(
        [item for item in resources if isinstance(item, dict)]
    )
    return {
        str(item["attr_name"]): item
        for item in merged
        if isinstance(item.get("attr_name"), str)
    }


def _load_descriptions() -> dict[str, str]:
    if not DESCRIPTIONS_PATH.exists():
        return {}
    payload = json.loads(DESCRIPTIONS_PATH.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        return {}
    return {
        key: value.strip()
        for key, value in payload.items()
        if isinstance(key, str) and isinstance(value, str) and value.strip()
    }


def _load_related() -> dict[str, list[str]]:
    if not RELATED_PATH.exists():
        return {}
    payload = json.loads(RELATED_PATH.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        return {}
    related: dict[str, list[str]] = {}
    for key, value in payload.items():
        if isinstance(key, str) and isinstance(value, list):
            related[key] = [item for item in value if isinstance(item, str)]
    return related


def _str_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]


def _format_bullet_list(items: list[str]) -> str:
    if not items:
        return "_None._"
    return "\n".join(f"- `{item}`" for item in items)


def _operations_table(supported_ops: list[str]) -> str:
    rows = ["| Operation | Supported |", "|-----------|-----------|"]
    for op in SDK_OP_ORDER:
        rows.append(f"| `{op}` | {'yes' if op in supported_ops else 'no'} |")
    return "\n".join(rows)


def _render_resource_page(
    attr_name: str,
    contract: dict[str, Any],
    description: str,
    related_map: dict[str, list[str]],
) -> str:
    resource_name = contract.get("resource_name", "")
    scope = contract.get("scope", "tenant")
    parent_kind = contract.get("parent_kind")
    supported_ops = _str_list(contract.get("supported_ops"))
    spec_fields = _str_list(contract.get("create_convenience_spec_fields"))
    spec_required = set(_str_list(contract.get("create_convenience_spec_required")))
    meta_fields = _str_list(contract.get("create_convenience_meta_fields"))
    top_level = _str_list(contract.get("create_convenience_payload_top_level_fields"))
    read_only_spec = _str_list(contract.get("create_convenience_read_only_spec_fields"))
    skip_reason = contract.get("convenience_skip_reason")
    create_mode = contract.get("create_mode", "unsupported")
    model_name = contract.get("model_class", attr_name)
    import_path = contract.get("model_class_import_path", "")

    lines: list[str] = [
        f"# {attr_name}",
        "",
        description or f"{attr_name} resource facade.",
        "",
        "## Client access",
        "",
        f"- **Facade:** `client.{attr_name}`",
        f"- **API path segment:** `{resource_name}`",
        f"- **Scope:** `{scope}`",
    ]
    if parent_kind:
        lines.append(f"- **Parent list:** `list(parent=<{parent_kind}>)`")
    lines.extend(["", "## Operations", "", _operations_table(supported_ops), ""])

    if "create" in supported_ops:
        lines.extend(["## Create", ""])
        lines.append(f"- **Mode:** `{create_mode}`")
        if import_path:
            lines.append(f"- **Model import:** `{import_path}`")
        lines.append(f"- **Payload model:** `Create{model_name}Payload`")
        lines.extend(
            [
                "",
                "### Payload top-level fields",
                "",
                _format_bullet_list(top_level),
                "",
                "### Create convenience kwargs (flat)",
                "",
            ]
        )
        if skip_reason and not spec_fields and not meta_fields:
            lines.append(f"_Skipped: {skip_reason}_")
        else:
            if meta_fields:
                lines.append("**Meta (flat):**")
                lines.append("")
                lines.append(_format_bullet_list(meta_fields))
                lines.append("")
            if spec_fields:
                lines.append("**Spec (flat, promoted into `spec`):**")
                lines.append("")
                optional = [f for f in spec_fields if f not in spec_required]
                if spec_required:
                    lines.append("Required:")
                    lines.append("")
                    lines.append(_format_bullet_list(sorted(spec_required)))
                    lines.append("")
                if optional:
                    lines.append("Optional:")
                    lines.append("")
                    lines.append(_format_bullet_list(sorted(optional)))
                    lines.append("")
            lines.append(
                "Unknown flat kwargs raise `TypeError`. Use `payload=` or nested "
                "`spec=` / `meta=` for full control."
            )
        lines.extend(["", "### Examples", "", "**Python:**", "", "```python"])
        if spec_fields:
            example_kwargs = ", ".join(
                f'{field}="..."'
                for field in spec_fields[:2]
                if field in spec_required
            ) or "name='example'"
            lines.append(
                f"client.{attr_name}.create({example_kwargs}, namespace='tenant.ns')"
            )
        else:
            lines.append(
                f"client.{attr_name}.create(payload=Create{model_name}Payload(...))"
            )
        lines.extend(
            [
                "```",
                "",
                "**endorctl:**",
                "",
                "```bash",
                f"endorctl api create --resource={attr_name} --namespace=<tenant.ns> -f payload.json",
                "```",
                "",
            ]
        )

    if read_only_spec:
        lines.extend(
            [
                "## Response / read-only spec fields",
                "",
                "Present on responses; not accepted as flat create kwargs:",
                "",
                _format_bullet_list(read_only_spec),
                "",
            ]
        )

    related = related_map.get(attr_name, [])
    if related:
        lines.extend(["## Related resources", ""])
        for name in related:
            lines.append(f"- [{name}]({name}.md)")
        lines.append("")

    helpers = render_resource_facade_helpers_section(attr_name)
    if helpers:
        lines.append(helpers)

    lines.append(
        (
            "_Generated by `devtools/codegen/generate_resource_reference_pages.py`. "
            + "Do not edit by hand._"
        )
    )
    lines.append("")
    return "\n".join(lines)


def _render_index(
    rows: list[dict[str, Any]],
) -> str:
    lines = [
        "# Per-resource reference index",
        "",
        "One page per SDK facade resource (`client.<AttrName>`).",
        "",
        "| Resource | API segment | Scope | Operations | Page |",
        "|----------|-------------|-------|------------|------|",
    ]
    for row in sorted(rows, key=lambda item: str(item.get("attr_name", ""))):
        attr = str(row["attr_name"])
        ops = ", ".join(_str_list(row.get("supported_ops")))
        lines.append(
            f"| `{attr}` | `{row.get('resource_name', '')}` | "
            f"`{row.get('scope', '')}` | {ops} | [{attr}.md]({attr}.md) |"
        )
    lines.extend(
        [
            "",
            (
                "_Generated by `devtools/codegen/generate_resource_reference_pages.py`. "
                + "Do not edit by hand._"
            ),
            "",
        ]
    )
    return "\n".join(lines)


def generate_resource_reference_pages() -> list[Path]:
    """Write per-resource markdown pages and index JSON. Returns changed paths."""
    contract_by_attr = _load_contract_resources()
    descriptions = _load_descriptions()
    related_map = _load_related()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    index_rows: list[dict[str, Any]] = []
    changed: list[Path] = []
    current_names = {entry.attr_name for entry in RESOURCE_REGISTRY}

    for path in OUTPUT_DIR.glob("*.md"):
        if path.name == "README.md":
            continue
        if path.stem not in current_names:
            path.unlink()
            changed.append(path)

    for entry in sorted(RESOURCE_REGISTRY, key=lambda item: item.attr_name):
        contract = contract_by_attr.get(entry.attr_name, {})
        description = descriptions.get(entry.attr_name, "")
        if not description:
            generated = contract.get("description")
            if isinstance(generated, str) and generated.strip():
                description = generated.strip()

        page = _render_resource_page(
            entry.attr_name,
            contract,
            description,
            related_map,
        )
        path = OUTPUT_DIR / f"{entry.attr_name}.md"
        if not path.exists() or path.read_text(encoding="utf-8") != page:
            path.write_text(page, encoding="utf-8")
            changed.append(path)

        index_rows.append(
            {
                "attr_name": entry.attr_name,
                "resource_name": contract.get("resource_name", entry.resource_name),
                "scope": contract.get("scope", entry.scope),
                "supported_ops": sorted(entry.supported_ops),
                "doc_path": f"docs/generated-reference/resources/{entry.attr_name}.md",
            }
        )

    readme = _render_index(index_rows)
    readme_path = OUTPUT_DIR / "README.md"
    if not readme_path.exists() or readme_path.read_text(encoding="utf-8") != readme:
        readme_path.write_text(readme, encoding="utf-8")
        changed.append(readme_path)

    index_json = json.dumps({"resources": index_rows}, indent=2, sort_keys=True) + "\n"
    if (
        not RESOURCE_INDEX_PATH.exists()
        or RESOURCE_INDEX_PATH.read_text(encoding="utf-8") != index_json
    ):
        RESOURCE_INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
        RESOURCE_INDEX_PATH.write_text(index_json, encoding="utf-8")
        changed.append(RESOURCE_INDEX_PATH)

    return changed


def main() -> int:
    changed = generate_resource_reference_pages()
    if changed:
        logger.info("Updated %s resource reference file(s).", len(changed))
    else:
        logger.info("Resource reference pages are up to date.")
    return 0


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    raise SystemExit(main())
