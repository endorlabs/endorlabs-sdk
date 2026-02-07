#!/usr/bin/env python3
r"""Import Semgrep Rule YAML definitions into an Endor Labs namespace.

Reads one or more Semgrep-compatible YAML rule files from disk and creates
them as custom Semgrep rules in the Endor Labs platform via the SDK.

This is the import counterpart to ``export_semgrep_rule.py``.

Examples:
    Import a single rule YAML file::

        uv run python maneuvers/import_semgrep_rule.py \\
            --file .endorlabs-context/semgrep-rules/my-rule.yaml

    Import all YAML files in a directory::

        uv run python maneuvers/import_semgrep_rule.py \\
            --dir .endorlabs-context/semgrep-rules/

    Dry-run (validate and list rules without creating)::

        uv run python maneuvers/import_semgrep_rule.py \\
            --dir .endorlabs-context/semgrep-rules/ --dry-run

    Force overwrite existing rules with the same name::

        uv run python maneuvers/import_semgrep_rule.py \\
            --file my-rule.yaml --force

"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path

import yaml

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from endorlabs.api_client import APIClient
from endorlabs.resources.semgrep_rule import (
    CreateSemgrepRulePayload,
    SemgrepNativeRule,
    SemgrepRule,
    SemgrepRuleMetaCreate,
    SemgrepRuleSpec,
    UpdateSemgrepRulePayload,
    create_semgrep_rule,
    list_semgrep_rules,
    update_semgrep_rule,
)
from endorlabs.types import ListParameters
from endorlabs.utils.logging_config import setup_logging

logger = logging.getLogger(__name__)

# Default input directory relative to repo root
DEFAULT_INPUT_DIR = (
    Path(__file__).parent.parent / ".endorlabs-context" / "semgrep-rules"
)


# ---------------------------------------------------------------------------
# YAML parsing helpers
# ---------------------------------------------------------------------------


def _parse_yaml_file(path: Path) -> list[dict]:
    """Parse a Semgrep-compatible YAML file and return the list of rule dicts.

    Handles both single-rule files (``rules: [...]``) and bare rule dicts.
    """
    text = path.read_text(encoding="utf-8")
    doc = yaml.safe_load(text)

    if doc is None:
        logger.warning(f"  Empty YAML file: {path}")
        return []

    if isinstance(doc, dict) and "rules" in doc:
        rules = doc["rules"]
        if isinstance(rules, list):
            return rules
        logger.warning(f"  'rules' key is not a list in {path}")
        return []

    if isinstance(doc, dict):
        # Bare rule dict (no wrapping 'rules' key)
        return [doc]

    logger.warning(f"  Unexpected YAML structure in {path}")
    return []


def _rule_display_id(rule_dict: dict) -> str:
    """Return a human-readable identifier from a parsed rule dict."""
    return rule_dict.get("id", rule_dict.get("message", "unknown"))[:80]


def _build_rule_name(rule_dict: dict, source_file: Path) -> str:
    """Derive a rule name for the Endor Labs meta.name field.

    Prefers the rule ``id`` field; falls back to the filename stem.
    """
    rule_id = rule_dict.get("id")
    if rule_id:
        return str(rule_id)
    return source_file.stem


def _build_native_rule(rule_dict: dict) -> SemgrepNativeRule:
    """Build a minimal SemgrepNativeRule from a parsed rule dict.

    Extracts only the fields that the Pydantic model recognises (id,
    languages, message, severity, pattern, mode).  The full rule
    definition lives in ``spec.yaml`` which the API parses server-side;
    this object satisfies client-side validation only.
    """
    return SemgrepNativeRule(
        id=rule_dict.get("id"),
        languages=rule_dict.get("languages"),
        message=rule_dict.get("message"),
        severity=rule_dict.get("severity"),
        pattern=rule_dict.get("pattern"),
        mode=rule_dict.get("mode"),
    )


# ---------------------------------------------------------------------------
# Conflict detection
# ---------------------------------------------------------------------------


def _find_existing_rule(
    client: APIClient,
    namespace: str,
    rule_name: str,
) -> SemgrepRule | None:
    """Search for an existing rule with the given name.

    Returns the first match or ``None``.
    """
    params = ListParameters(filter=f'meta.name=="{rule_name}"')
    results = list_semgrep_rules(client, namespace, list_params=params)
    return results[0] if results else None


# ---------------------------------------------------------------------------
# Import logic
# ---------------------------------------------------------------------------


def import_rule(
    client: APIClient,
    namespace: str,
    rule_dict: dict,
    yaml_content: str,
    source_file: Path,
    *,
    dry_run: bool = False,
    force: bool = False,
) -> str:
    """Import a single rule into the Endor Labs namespace.

    Returns a status string: ``"created"``, ``"updated"``, ``"skipped"``,
    or ``"failed"``.
    """
    rule_name = _build_rule_name(rule_dict, source_file)
    display_id = _rule_display_id(rule_dict)

    # Check for existing rule with the same name
    existing = _find_existing_rule(client, namespace, rule_name)

    if existing and not force:
        logger.info(
            f"  SKIP: Rule '{display_id}' already exists "
            f"(uuid={existing.uuid}). Use --force to overwrite."
        )
        return "skipped"

    if dry_run:
        action = "update" if existing else "create"
        logger.info(f"  [DRY RUN] Would {action}: {display_id}")
        return "skipped"

    # Build the YAML content for spec.yaml (the API-native format).
    # Wrap single rule dict in the standard 'rules:' envelope if needed.
    if not yaml_content.lstrip().startswith("rules:"):
        wrapped = yaml.dump(
            {"rules": [rule_dict]},
            default_flow_style=False,
            allow_unicode=True,
            sort_keys=False,
        )
    else:
        wrapped = yaml_content

    if existing and force:
        # Update existing rule
        logger.info(
            f"  FORCE: Updating existing rule '{display_id}' (uuid={existing.uuid})..."
        )
        try:
            update_desc = rule_dict.get("metadata", {}).get(
                "description", ""
            ) or rule_dict.get("message", "")
            if len(update_desc.encode("utf-8")) > 1024:
                update_desc = update_desc[:1020] + "..."
            payload = UpdateSemgrepRulePayload(
                meta=SemgrepRuleMetaCreate(
                    name=rule_name,
                    description=update_desc,
                ),
                spec=SemgrepRuleSpec(yaml=wrapped),
            )
            update_semgrep_rule(
                client,
                namespace,
                existing.uuid,
                payload,
                update_mask="spec,meta.description",
            )
            logger.info(f"  Updated: {display_id} (uuid={existing.uuid})")
            return "updated"
        except Exception as e:
            logger.error(f"  FAILED to update '{display_id}': {e}")
            return "failed"

    # Create new rule
    try:
        native_rule = _build_native_rule(rule_dict)
        # API limits meta.description to 1024 bytes; use metadata.description
        # (short form) if available, otherwise truncate the message.
        description = rule_dict.get("metadata", {}).get(
            "description", ""
        ) or rule_dict.get("message", "")
        if len(description.encode("utf-8")) > 1024:
            description = description[:1020] + "..."
        meta = SemgrepRuleMetaCreate(
            name=rule_name,
            description=description,
        )
        spec = SemgrepRuleSpec(rule=native_rule, yaml=wrapped)
        payload = CreateSemgrepRulePayload(
            meta=meta,
            spec=spec,
            propagate=True,
        )

        logger.info(f"  Creating: {display_id}...")
        # Skip client-side validation: the YAML is the authoritative rule
        # definition (already validated by opengrep/semgrep locally) and may
        # use pattern operators (e.g. pattern-not-inside) that the SDK's
        # Pydantic models do not fully represent.  The API parses spec.yaml
        # server-side.
        created = create_semgrep_rule(client, namespace, payload, validate=False)
        logger.info(f"  Created: {display_id} (uuid={created.uuid})")
        return "created"
    except Exception as e:
        logger.error(f"  FAILED to create '{display_id}': {e}")
        return "failed"


# ---------------------------------------------------------------------------
# File resolution
# ---------------------------------------------------------------------------


def resolve_yaml_files(
    file_path: Path | None = None,
    dir_path: Path | None = None,
) -> list[Path]:
    """Resolve the set of YAML files to import."""
    if file_path:
        if not file_path.exists():
            logger.error(f"File not found: {file_path}")
            return []
        return [file_path]

    if dir_path:
        if not dir_path.is_dir():
            logger.error(f"Directory not found: {dir_path}")
            return []
        files = sorted(dir_path.glob("*.yaml")) + sorted(dir_path.glob("*.yml"))
        if not files:
            logger.warning(f"No YAML files found in {dir_path}")
        return files

    return []


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def main() -> int:
    """Run the Semgrep rule YAML import."""
    parser = argparse.ArgumentParser(
        description=(
            "Import Semgrep rule YAML definitions into an Endor Labs namespace."
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

    # File selection (mutually exclusive)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument(
        "--file",
        type=Path,
        dest="file_path",
        help="Import a single Semgrep rule YAML file.",
    )
    source.add_argument(
        "--dir",
        type=Path,
        dest="dir_path",
        help="Import all YAML files in a directory.",
    )

    # Import options
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate and list rules without creating them.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing rules with the same name.",
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

    # Resolve YAML files
    yaml_files = resolve_yaml_files(
        file_path=args.file_path,
        dir_path=args.dir_path,
    )

    if not yaml_files:
        logger.warning("No YAML files to import.")
        return 0

    logger.info(f"Found {len(yaml_files)} YAML file(s) to process.")

    # Initialize API client
    if not args.dry_run:
        try:
            client = APIClient()
        except Exception as e:
            logger.error(f"Failed to initialize API client: {e}")
            return 1
    else:
        client = None  # type: ignore[assignment]

    # Process each YAML file
    stats: dict[str, int] = {"created": 0, "updated": 0, "skipped": 0, "failed": 0}

    for yaml_file in yaml_files:
        logger.info(f"\nProcessing: {yaml_file}")

        try:
            rule_dicts = _parse_yaml_file(yaml_file)
        except Exception as e:
            logger.error(f"  Failed to parse {yaml_file}: {e}")
            stats["failed"] += 1
            continue

        if not rule_dicts:
            logger.warning(f"  No rules found in {yaml_file}")
            continue

        yaml_text = yaml_file.read_text(encoding="utf-8")

        for rule_dict in rule_dicts:
            display_id = _rule_display_id(rule_dict)

            if args.dry_run:
                logger.info(f"  [DRY RUN] Would import: {display_id}")
                stats["skipped"] += 1
                continue

            status = import_rule(
                client,
                args.namespace,
                rule_dict,
                yaml_text,
                yaml_file,
                dry_run=args.dry_run,
                force=args.force,
            )
            stats[status] += 1

    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("Import Summary")
    logger.info("=" * 60)
    logger.info(f"  Created:  {stats['created']}")
    logger.info(f"  Updated:  {stats['updated']}")
    logger.info(f"  Skipped:  {stats['skipped']}")
    logger.info(f"  Failed:   {stats['failed']}")
    logger.info(f"  Total:    {sum(stats.values())}")

    return 1 if stats["failed"] > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
