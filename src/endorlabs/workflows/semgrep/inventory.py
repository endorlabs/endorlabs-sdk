"""Inventory metadata keys on tenant SemgrepRule resources.

Produces:
- JSON artifact with per-key prevalence and example rules
- Optional markdown summary for quick review
"""

from __future__ import annotations

import argparse
import json
import logging
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import endorlabs
from endorlabs.context.paths import workflow_artifacts_root
from endorlabs.tools.list_bounds import (
    is_list_truncated,
    resolve_max_pages,
    truncation_message,
)
from endorlabs.utils.logging_config import get_resource_logger
from endorlabs.utils.path_safety import safe_write_text

LOGGER = get_resource_logger(__name__)


def _extract_meta_dict(rule: Any) -> dict[str, Any]:
    spec = getattr(rule, "spec", None)
    native = getattr(spec, "rule", None) if spec else None
    metadata = getattr(native, "metadata", None) if native else None
    if metadata is None:
        return {}
    return metadata.model_dump(by_alias=True, exclude_none=True)


def build_inventory(
    client: endorlabs.Client,
    namespace: str,
    *,
    max_pages: int = 0,
    page_size: int = 500,
) -> dict[str, Any]:
    """List SemgrepRule resources and summarize metadata-key prevalence by origin."""
    list_max_pages = resolve_max_pages(max_pages)
    rules = client.SemgrepRule.list(
        namespace=namespace,
        traverse=True,
        max_pages=list_max_pages,
        page_size=page_size,
    )
    list_truncated = is_list_truncated(
        len(rules), max_pages=list_max_pages, page_size=page_size
    )
    if list_truncated:
        LOGGER.warning(
            "%s",
            truncation_message(
                resource="SemgrepRule",
                scope=f"namespace={namespace}",
                row_count=len(rules),
                max_pages=list_max_pages,
                page_size=page_size,
            ),
        )
    key_counts: Counter[str] = Counter()
    key_examples: dict[str, list[dict[str, str]]] = defaultdict(list)
    origin_counts: Counter[str] = Counter()

    for rule in rules:
        spec = getattr(rule, "spec", None)
        origin = getattr(spec, "defined_by", None) or "unknown"
        origin_counts[origin] += 1
        meta = _extract_meta_dict(rule)
        for key in sorted(meta.keys()):
            key_counts[key] += 1
            if len(key_examples[key]) < 5:
                key_examples[key].append(
                    {
                        "name": getattr(getattr(rule, "meta", None), "name", "") or "",
                        "defined_by": origin,
                        "uuid": getattr(rule, "uuid", "") or "",
                    }
                )

    return {
        "namespace": namespace,
        "total_rules": len(rules),
        "list_truncated": list_truncated,
        "list_max_pages": max_pages,
        "list_page_size": page_size,
        "defined_by_counts": dict(sorted(origin_counts.items())),
        "metadata_key_counts": dict(sorted(key_counts.items())),
        "metadata_key_examples": dict(sorted(key_examples.items())),
    }


def _write_markdown_summary(inventory: dict[str, Any], output_path: Path) -> None:
    lines = [
        "# SemgrepRule metadata inventory",
        "",
        f"- Namespace: `{inventory['namespace']}`",
        f"- Total rules: `{inventory['total_rules']}`",
        "",
        "## Rule origins",
        "",
    ]
    for origin, count in inventory["defined_by_counts"].items():
        lines.append(f"- `{origin}`: {count}")
    lines.extend(["", "## Metadata keys", ""])
    for key, count in inventory["metadata_key_counts"].items():
        lines.append(f"- `{key}`: {count}")
    safe_write_text(output_path.parent, output_path, "\n".join(lines) + "\n")


def main() -> int:
    """Run the module CLI and return exit code."""
    parser = argparse.ArgumentParser(
        description="Inventory SemgrepRule metadata keys (endor-semgrep-inventory)."
    )
    parser.add_argument("--namespace", required=True, help="Tenant namespace")
    parser.add_argument(
        "--max-pages",
        type=int,
        default=0,
        help="Max pages for SemgrepRule.list (0 = unlimited).",
    )
    parser.add_argument(
        "--page-size",
        type=int,
        default=500,
        help="List page size for SemgrepRule.list. Default: 500",
    )
    parser.add_argument(
        "--json-out",
        type=Path,
        default=workflow_artifacts_root() / "semgrep_rule_metadata_inventory.json",
        help="JSON artifact output path",
    )
    parser.add_argument(
        "--summary-out",
        type=Path,
        default=workflow_artifacts_root() / "semgrep_rule_metadata_inventory.md",
        help="Markdown summary output path",
    )
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    client = endorlabs.Client(tenant=args.namespace)
    try:
        inventory = build_inventory(
            client=client,
            namespace=args.namespace,
            max_pages=args.max_pages,
            page_size=args.page_size,
        )

        args.json_out = args.json_out.resolve()
        args.summary_out = args.summary_out.resolve()
        safe_write_text(
            args.json_out.parent,
            args.json_out,
            json.dumps(inventory, indent=2),
        )

        _write_markdown_summary(inventory, args.summary_out)

        print(f"Wrote {args.json_out}")
        print(f"Wrote {args.summary_out}")
    finally:
        client.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
