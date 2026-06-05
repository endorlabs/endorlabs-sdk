"""Inventory metadata keys used by tenant Semgrep rules.

Produces:
- JSON artifact with per-key prevalence and example rules
- Optional markdown summary for quick review
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import endorlabs
from endorlabs.context.paths import workflow_artifacts_root


def _extract_meta_dict(rule: Any) -> dict[str, Any]:
    spec = getattr(rule, "spec", None)
    native = getattr(spec, "rule", None) if spec else None
    metadata = getattr(native, "metadata", None) if native else None
    if metadata is None:
        return {}
    return metadata.model_dump(by_alias=True, exclude_none=True)


def build_inventory(client: endorlabs.Client, namespace: str) -> dict[str, Any]:
    rules = client.SemgrepRule.list(namespace=namespace, traverse=True, max_pages=200)
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
        "defined_by_counts": dict(sorted(origin_counts.items())),
        "metadata_key_counts": dict(sorted(key_counts.items())),
        "metadata_key_examples": dict(sorted(key_examples.items())),
    }


def _write_markdown_summary(inventory: dict[str, Any], output_path: Path) -> None:
    lines = [
        "# Semgrep metadata inventory",
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
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Inventory Semgrep rule metadata keys."
    )
    parser.add_argument("--namespace", required=True, help="Tenant namespace")
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

    client = endorlabs.Client(tenant=args.namespace)
    try:
        inventory = build_inventory(client=client, namespace=args.namespace)

        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(json.dumps(inventory, indent=2), encoding="utf-8")

        args.summary_out.parent.mkdir(parents=True, exist_ok=True)
        _write_markdown_summary(inventory, args.summary_out)

        print(f"Wrote {args.json_out}")
        print(f"Wrote {args.summary_out}")
    finally:
        client.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
