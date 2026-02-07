#!/usr/bin/env python3
"""Export Semgrep Rule YAML definitions to .endorlabs-context.

Retrieves one or more Semgrep rules from the Endor Labs API and writes
their native YAML definitions to .endorlabs-context/semgrep-rules/.

Each rule is saved as a standalone Semgrep-compatible YAML file named
after the rule ID (or UUID if the ID is unavailable).

Examples:
    Export a single rule by UUID::

        uv run python maneuvers/export_semgrep_rule.py --uuid <rule-uuid>

    Export a single rule by name::

        uv run python maneuvers/export_semgrep_rule.py --name "my-custom-rule"

    Export rules matching a filter expression::

        uv run python maneuvers/export_semgrep_rule.py \
            --filter "spec.defined_by==MyTenant"

    Export ALL rules in the namespace::

        uv run python maneuvers/export_semgrep_rule.py --all

    Dry-run (list matching rules without writing files)::

        uv run python maneuvers/export_semgrep_rule.py --all --dry-run

"""

from __future__ import annotations

import argparse
import logging
import os
import re
import sys
from pathlib import Path
from typing import Any

import yaml

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from endorlabs.api_client import APIClient
from endorlabs.resources.semgrep_rule import (
    SemgrepNativeRule,
    SemgrepRule,
    get_semgrep_rule,
    list_semgrep_rules,
)
from endorlabs.types import ListParameters
from endorlabs.utils.logging_config import setup_logging

logger = logging.getLogger(__name__)

# Default output directory relative to repo root
DEFAULT_OUTPUT_DIR = (
    Path(__file__).parent.parent / ".endorlabs-context" / "semgrep-rules"
)


def _sanitize_filename(name: str) -> str:
    """Replace unsafe characters with dashes for cross-platform paths."""
    # Replace path separators and other problematic characters
    sanitized = re.sub(r"[<>:\"/\\|?*\s]+", "-", name)
    # Collapse multiple dashes
    sanitized = re.sub(r"-{2,}", "-", sanitized)
    # Strip leading/trailing dashes and dots
    sanitized = sanitized.strip("-.")
    return sanitized or "unknown"


def _rule_to_full_yaml(rule: SemgrepRule) -> str:
    """Build a Semgrep-compatible YAML definition for a rule.

    Prefers ``spec.yaml`` when present (the API-stored original).  Falls
    back to reconstructing the YAML from ``spec.rule`` (the structured
    native rule).
    """
    # 1. If the API returned the original YAML, prefer it
    if rule.spec and rule.spec.yaml:
        return rule.spec.yaml

    # 2. Reconstruct from the structured native rule
    if rule.spec and rule.spec.rule:
        native = rule.spec.rule
        entry = _native_rule_to_dict(native)
        return yaml.dump(
            {"rules": [entry]},
            default_flow_style=False,
            allow_unicode=True,
            sort_keys=False,
        )

    # 3. Minimal fallback
    return yaml.dump(
        {
            "rules": [
                {
                    "id": rule.uuid,
                    "message": "No rule definition available",
                }
            ]
        },
        default_flow_style=False,
    )


def _native_rule_to_dict(
    native: SemgrepNativeRule,
) -> dict[str, Any]:
    """Convert a SemgrepNativeRule model into a plain dict for YAML.

    Emits only non-None fields so the resulting YAML stays clean and
    Semgrep-compatible.
    """
    entry: dict[str, Any] = {}

    # Required fields
    if native.id:
        entry["id"] = native.id
    if native.message:
        entry["message"] = native.message
    if native.languages:
        entry["languages"] = native.languages
    if native.severity:
        entry["severity"] = native.severity

    # Pattern fields (only one family should be present)
    if native.pattern:
        entry["pattern"] = native.pattern
    if native.patterns:
        entry["patterns"] = _dump_patterns(native.patterns)
    if native.pattern_either:
        entry["pattern-either"] = _dump_patterns(native.pattern_either)
    if native.pattern_regex:
        entry["pattern-regex"] = native.pattern_regex
    if native.pattern_not:
        entry["pattern-not"] = _dump_patterns(native.pattern_not)

    # Taint-mode fields
    if native.mode:
        entry["mode"] = native.mode
    if native.pattern_sources:
        entry["pattern-sources"] = _dump_patterns(native.pattern_sources)
    if native.pattern_sinks:
        entry["pattern-sinks"] = _dump_patterns(native.pattern_sinks)
    if native.pattern_propagators:
        entry["pattern-propagators"] = _dump_patterns(
            native.pattern_propagators,
        )
    if native.pattern_sanitizers:
        entry["pattern-sanitizers"] = _dump_patterns(
            native.pattern_sanitizers,
        )

    # Optional scalar fields
    if native.fix:
        entry["fix"] = native.fix
    if native.fix_regex:
        entry["fix-regex"] = native.fix_regex.model_dump(
            exclude_none=True,
        )
    if native.options:
        entry["options"] = native.options.model_dump(
            exclude_none=True,
            by_alias=True,
        )
    if native.paths:
        entry["paths"] = native.paths
    if native.focus_metavariable:
        entry["focus-metavariable"] = native.focus_metavariable
    if native.min_version:
        entry["min-version"] = native.min_version

    # Metadata
    if native.metadata:
        meta_dict = native.metadata.model_dump(exclude_none=True)
        if meta_dict:
            entry["metadata"] = meta_dict

    return entry


def _dump_patterns(patterns: list[Any]) -> list[dict[str, Any]]:
    """Recursively serialise pattern types to plain dicts."""
    result: list[dict[str, Any]] = []
    for p in patterns:
        if hasattr(p, "model_dump"):
            d = p.model_dump(exclude_none=True, by_alias=True)
        else:
            d = p
        if d:
            result.append(d)
    return result


def _rule_display_id(rule: SemgrepRule) -> str:
    """Return a human-readable identifier for a rule."""
    if rule.spec and rule.spec.rule and rule.spec.rule.id:
        return rule.spec.rule.id
    if rule.meta and rule.meta.name:
        return rule.meta.name
    return rule.uuid


def export_rule(
    rule: SemgrepRule,
    output_dir: Path,
    *,
    dry_run: bool = False,
) -> Path | None:
    """Write a single rule to a YAML file under *output_dir*.

    Returns the written path, or ``None`` on dry-run / error.
    """
    display_id = _rule_display_id(rule)
    filename = _sanitize_filename(display_id) + ".yaml"
    dest = output_dir / filename

    yaml_content = _rule_to_full_yaml(rule)

    if dry_run:
        logger.info(f"  [DRY RUN] Would write: {dest}  ({len(yaml_content)} bytes)")
        return None

    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(yaml_content, encoding="utf-8")
    logger.info(f"  Exported: {dest}  ({len(yaml_content)} bytes)")
    return dest


def resolve_rules(
    client: APIClient,
    namespace: str,
    *,
    uuid: str | None = None,
    name: str | None = None,
    filter_expr: str | None = None,
    export_all: bool = False,
) -> list[SemgrepRule]:
    """Resolve the set of rules to export based on CLI arguments."""
    if uuid:
        logger.info(f"Fetching rule by UUID: {uuid}")
        rule = get_semgrep_rule(client, namespace, uuid)
        return [rule]

    if name:
        logger.info(f"Searching for rule with name: {name}")
        params = ListParameters(filter=f'meta.name=="{name}"')
        rules = list_semgrep_rules(client, namespace, list_params=params)
        if not rules:
            # Try partial match via contains
            params = ListParameters(
                filter=f'meta.name contains "{name}"',
            )
            rules = list_semgrep_rules(client, namespace, list_params=params)
        return rules

    if filter_expr:
        logger.info(
            f"Searching for rules matching filter: {filter_expr}",
        )
        params = ListParameters(filter=filter_expr)
        return list_semgrep_rules(client, namespace, list_params=params)

    if export_all:
        logger.info("Fetching all rules in namespace...")
        return list_semgrep_rules(client, namespace)

    return []


def main() -> int:
    """Run the Semgrep rule YAML export."""
    parser = argparse.ArgumentParser(
        description=(
            "Export Semgrep rule YAML definitions to .endorlabs-context/semgrep-rules/"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    # Namespace
    parser.add_argument(
        "--namespace",
        default=os.getenv("ENDOR_NAMESPACE"),
        help=(
            "Tenant namespace (e.g. 'tenant.namespace'). "
            "Defaults to ENDOR_NAMESPACE env var."
        ),
    )

    # Rule selection (mutually exclusive)
    selection = parser.add_mutually_exclusive_group(required=True)
    selection.add_argument(
        "--uuid",
        help="Export a single rule by UUID.",
    )
    selection.add_argument(
        "--name",
        help="Export rule(s) matching this name (exact or partial).",
    )
    selection.add_argument(
        "--filter",
        dest="filter_expr",
        help=(
            "Export rules matching an API filter expression "
            "(e.g. 'spec.defined_by==MyTenant')."
        ),
    )
    selection.add_argument(
        "--all",
        dest="export_all",
        action="store_true",
        help="Export ALL rules in the namespace.",
    )

    # Output options
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help=(f"Output directory for YAML files (default: {DEFAULT_OUTPUT_DIR})."),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="List matching rules without writing files.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging.",
    )

    args = parser.parse_args()

    # Setup logging
    setup_logging()
    if args.verbose:
        logging.getLogger("endorlabs").setLevel(logging.DEBUG)

    # Validate namespace
    if not args.namespace:
        logger.error(
            "Namespace is required. Set --namespace "
            "or ENDOR_NAMESPACE environment variable."
        )
        return 1

    # Initialize API client
    try:
        client = APIClient()
    except Exception as e:
        logger.error(f"Failed to initialize API client: {e}")
        return 1

    # Resolve rules to export
    try:
        rules = resolve_rules(
            client,
            args.namespace,
            uuid=args.uuid,
            name=args.name,
            filter_expr=args.filter_expr,
            export_all=args.export_all,
        )
    except Exception as e:
        logger.error(f"Error fetching rules: {e}", exc_info=True)
        return 1

    if not rules:
        logger.warning("No matching rules found.")
        return 0

    logger.info(f"Found {len(rules)} rule(s) to export.")

    # Export each rule
    exported = 0
    for rule in rules:
        display_id = _rule_display_id(rule)
        defined_by = rule.spec.defined_by if rule.spec else "unknown"
        disabled = (rule.disabled or (rule.spec and rule.spec.disabled)) or False
        state = "disabled" if disabled else "enabled"
        logger.info(f"  Rule: {display_id}  (defined_by={defined_by}, {state})")

        try:
            path = export_rule(rule, args.output_dir, dry_run=args.dry_run)
            if path is not None:
                exported += 1
        except Exception as e:
            logger.error(f"  Failed to export {display_id}: {e}")

    # Summary
    if args.dry_run:
        logger.info(
            f"\n[DRY RUN] Would export {len(rules)} rule(s) to {args.output_dir}"
        )
    else:
        logger.info(f"\nExported {exported}/{len(rules)} rule(s) to {args.output_dir}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
