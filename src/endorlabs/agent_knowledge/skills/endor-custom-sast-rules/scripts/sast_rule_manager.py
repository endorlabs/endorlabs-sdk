r"""Generic, guardrailed SAST Rule Manager for Endor Labs.

Manages custom OpenGrep/Semgrep rules on the Endor Labs platform with
five composable subcommands: import, delete, orphans, configure, sync.

Designed for agent use with strict validation guardrails that reject
unknown metadata fields rather than silently stripping them.

Usage examples:
    # Import rules from a directory
    uv run python .cursor/skills/endor-custom-sast-rules/scripts/sast_rule_manager.py \\
        import --rules-dir opengrep-rules/ --namespace tenant.ns

    # Delete rules matching a name filter
    uv run python .cursor/skills/endor-custom-sast-rules/scripts/sast_rule_manager.py \\
        delete --name-filter "endor-sdk" --namespace tenant.ns

    # Clean orphaned findings from deleted rules
    uv run python .cursor/skills/endor-custom-sast-rules/scripts/sast_rule_manager.py \\
        orphans --deleted-names rule-a rule-b --namespace tenant.ns

    # Configure enable/disable state
    uv run python .cursor/skills/endor-custom-sast-rules/scripts/sast_rule_manager.py \\
        configure --rules-dir opengrep-rules/ \\
        --enabled-dir opengrep-rules/trust-chain/ --namespace tenant.ns

    # Full sync (delete + orphans + import + configure)
    uv run python .cursor/skills/endor-custom-sast-rules/scripts/sast_rule_manager.py \\
        sync --rules-dir opengrep-rules/ \\
        --enabled-dir opengrep-rules/trust-chain/ \\
        --name-filter "endor-sdk" --namespace tenant.ns --force
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from typing import Any

import yaml

import endorlabs
from endorlabs.resources.semgrep_rule import (
    CreateSemgrepRulePayload,
    SemgrepNativeRule,
    SemgrepRuleMetaCreate,
    SemgrepRuleSpec,
    UpdateSemgrepRulePayload,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Validation guardrail
# ---------------------------------------------------------------------------

REQUIRED_TOP_LEVEL_KEYS: frozenset[str] = frozenset(
    {"id", "languages", "severity", "message"}
)
VALID_SEVERITIES: frozenset[str] = frozenset({"WARNING", "ERROR", "INFO"})
PATTERN_KEYS: frozenset[str] = frozenset(
    {
        "pattern",
        "patterns",
        "pattern-either",
        "pattern-regex",
        "pattern-sources",
        "pattern-sinks",
        "pattern_either",
        "pattern_regex",
        "pattern_sources",
        "pattern_sinks",
    }
)
ALLOWED_METADATA_KEYS: frozenset[str] = frozenset(
    {
        "asvs",
        "author",
        "bandit-code",
        "category",
        "confidence",
        "cwe",
        "cwe2020-top25",
        "cwe2021-top25",
        "cwe2022-top25",
        "cwe2023-top25",
        "deprecated",
        "description",
        "display-name",
        "endor-attack-examples",
        "endor-category",
        "endor-rule-origin",
        "endor-tags",
        "endor-targets",
        "explanation",
        "functional-categories",
        "help",
        "impact",
        "interfile",
        "license",
        "likelihood",
        "masvs",
        "owasp",
        "owaspapi",
        "precision",
        "references",
        "remediation",
        "resources",
        "rule-origin-note",
        "security-severity",
        "severity",
        "short-description",
        "shortDescription",
        "source-rule-url",
        "source-url-open",
        "subcategory",
        "tags",
        "technology",
        "version",
        "vulnerability",
        "vulnerability-class",
    }
)
CRUD_PARSER_UNSUPPORTED_METADATA_KEYS: frozenset[str] = frozenset(
    {"short-description", "shortDescription", "short_description"}
)


class RuleNormalizationResult:
    """Container for normalized rule and validation outcomes."""

    def __init__(
        self,
        rule: dict[str, Any],
        warnings: list[str],
        errors: list[str],
        dropped_metadata_keys: list[str],
    ) -> None:
        self.rule = rule
        self.warnings = warnings
        self.errors = errors
        self.dropped_metadata_keys = dropped_metadata_keys


def normalize_rule_dict_for_semgrep_crud(
    rule: dict[str, Any],
) -> RuleNormalizationResult:
    """Normalize and validate a Semgrep rule dict for /semgrep-rules CRUD."""
    normalized = dict(rule)
    warnings: list[str] = []
    errors: list[str] = []
    dropped: list[str] = []

    missing = [k for k in sorted(REQUIRED_TOP_LEVEL_KEYS) if k not in normalized]
    errors.extend([f"Missing required top-level key: '{key}'" for key in missing])

    if not (set(normalized.keys()) & PATTERN_KEYS):
        errors.append(f"At least one pattern key required: {sorted(PATTERN_KEYS)}")

    severity = normalized.get("severity")
    if severity is not None and severity not in VALID_SEVERITIES:
        errors.append(
            f"Invalid severity '{severity}'; must be one of {sorted(VALID_SEVERITIES)}"
        )

    metadata = normalized.get("metadata")
    if isinstance(metadata, dict):
        unknown = sorted(set(metadata.keys()) - ALLOWED_METADATA_KEYS)
        for key in unknown:
            metadata.pop(key, None)
            dropped.append(key)
        if unknown:
            warnings.append(
                f"Dropped unknown metadata key(s): {unknown}. "
                f"Allowed keys: {sorted(ALLOWED_METADATA_KEYS)}"
            )

        parser_unsupported = sorted(
            key for key in CRUD_PARSER_UNSUPPORTED_METADATA_KEYS if key in metadata
        )
        for key in parser_unsupported:
            metadata.pop(key, None)
            dropped.append(key)
        if parser_unsupported:
            warnings.append(
                "Dropped parser-unsupported metadata key(s) for /semgrep-rules CRUD: "
                f"{parser_unsupported}"
            )

        desc = metadata.get("description", "")
        if isinstance(desc, str) and len(desc.encode("utf-8")) > 1024:
            errors.append(
                "metadata.description exceeds 1024 UTF-8 bytes "
                f"({len(desc.encode('utf-8'))} bytes)"
            )

    return RuleNormalizationResult(
        rule=normalized,
        warnings=warnings,
        errors=errors,
        dropped_metadata_keys=sorted(set(dropped)),
    )


# ---------------------------------------------------------------------------
# YAML helpers
# ---------------------------------------------------------------------------


def _collect_yaml_files(directory: Path) -> list[Path]:
    """Recursively collect all .yaml/.yml files under *directory*."""
    paths: list[Path] = []
    for ext in ("*.yaml", "*.yml"):
        paths.extend(sorted(directory.rglob(ext)))
    return paths


def _extract_rule_ids_from_dir(directory: Path) -> set[str]:
    """Parse YAML files in *directory* and return the set of rule ``id`` values."""
    ids: set[str] = set()
    for yaml_path in _collect_yaml_files(directory):
        try:
            doc = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if isinstance(doc, dict) and "rules" in doc:
            for rule in doc["rules"]:
                if isinstance(rule, dict) and "id" in rule:
                    ids.add(str(rule["id"]))
        elif isinstance(doc, dict) and "id" in doc:
            ids.add(str(doc["id"]))
    return ids


def _parse_yaml_rules(path: Path) -> list[dict[str, Any]]:
    """Parse a Semgrep-compatible YAML file into rule dicts."""
    doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    if doc is None:
        return []
    if isinstance(doc, dict) and "rules" in doc:
        rules = doc["rules"]
        return rules if isinstance(rules, list) else []
    if isinstance(doc, dict):
        return [doc]
    return []


def _wrap_yaml(rule_dict: dict[str, Any], raw_yaml: str) -> str:
    """Ensure YAML content is wrapped in a ``rules:`` envelope."""
    _ = raw_yaml
    return yaml.dump(
        {"rules": [rule_dict]},
        default_flow_style=False,
        allow_unicode=True,
        sort_keys=False,
    )


def _extract_description(rule_dict: dict[str, Any]) -> str:
    """Extract a description from a parsed rule dict, truncated to 1024 bytes."""
    desc: str = rule_dict.get("metadata", {}).get("description", "") or rule_dict.get(
        "message", ""
    )
    if len(desc.encode("utf-8")) > 1024:
        desc = desc[:1020] + "..."
    return desc


def _display_id(rule_dict: dict[str, Any]) -> str:
    """Return a human-readable identifier from a parsed rule dict."""
    return str(rule_dict.get("id", rule_dict.get("message", "unknown")))[:80]


def _rule_display_name(rule: object) -> str:
    """Return a human-readable name for a SemgrepRule resource."""
    meta = getattr(rule, "meta", None)
    name = getattr(meta, "name", None) if meta else None
    uuid = getattr(rule, "uuid", "unknown")
    return f"{name} ({uuid})" if name else str(uuid)


# ---------------------------------------------------------------------------
# Subcommand: import
# ---------------------------------------------------------------------------


def cmd_import(
    client: endorlabs.Client,
    namespace: str,
    rules_dir: Path,
    *,
    force: bool = False,
    dry_run: bool = False,
) -> None:
    """Import all rule YAML files from *rules_dir*.

    Each rule dict is validated through ``validate_rule_dict()`` before
    import.  Uses ``client.SemgrepRule.create(payload=...)`` for creating
    new rules on the platform.
    """
    logger.info("=== import: importing rules from %s ===", rules_dir)

    yaml_files = _collect_yaml_files(rules_dir)
    if not yaml_files:
        logger.warning("No YAML files found in %s", rules_dir)
        return

    logger.info("Found %d YAML file(s) to process.", len(yaml_files))

    created = updated = skipped = failed = 0

    for yaml_path in yaml_files:
        try:
            rule_dicts = _parse_yaml_rules(yaml_path)
        except Exception as exc:
            logger.error("Failed to parse %s: %s", yaml_path, exc)
            failed += 1
            continue

        if not rule_dicts:
            continue

        raw_yaml = yaml_path.read_text(encoding="utf-8")

        for rule_dict in rule_dicts:
            rid = _display_id(rule_dict)
            rule_name = str(rule_dict.get("id", ""))

            # --- Validation guardrail (warn-and-drop for unknown metadata) ---
            normalized = normalize_rule_dict_for_semgrep_crud(rule_dict)
            for warning in normalized.warnings:
                logger.warning("Normalization warning for '%s': %s", rid, warning)

            if normalized.errors:
                for err in normalized.errors:
                    logger.error("Validation failed for '%s': %s", rid, err)
                failed += 1
                continue

            if dry_run:
                logger.info("[DRY RUN] Would import: %s (valid)", rid)
                skipped += 1
                continue

            normalized_rule = normalized.rule
            wrapped_yaml = _wrap_yaml(normalized_rule, raw_yaml)
            desc = _extract_description(normalized_rule)

            # Check for existing rule
            existing_rules = client.SemgrepRule.list(
                namespace=namespace,
                filter=f'meta.name=="{rule_name}"',
                max_pages=1,
            )
            existing = existing_rules[0] if existing_rules else None

            if existing and not force:
                logger.info("Skipped (exists, use --force to update): %s", rid)
                skipped += 1
                continue

            if existing:
                # Update existing rule
                try:
                    native_rule = SemgrepNativeRule.model_validate(normalized_rule)
                    upd = UpdateSemgrepRulePayload(
                        meta=SemgrepRuleMetaCreate(name=rule_name, description=desc),
                        spec=SemgrepRuleSpec(rule=native_rule, yaml=wrapped_yaml),
                    )
                    client.SemgrepRule.update(
                        existing,
                        payload=upd,
                        update_mask="spec,meta.description",
                    )
                    logger.info("Updated: %s (uuid=%s)", rid, existing.uuid)
                    updated += 1
                except Exception as exc:
                    logger.error("Failed to update '%s': %s", rid, exc)
                    failed += 1
                continue

            # Create new rule with validate=False for compound patterns
            try:
                native_rule = SemgrepNativeRule.model_validate(normalized_rule)
                create_payload = CreateSemgrepRulePayload(
                    meta=SemgrepRuleMetaCreate(name=rule_name, description=desc),
                    spec=SemgrepRuleSpec(rule=native_rule, yaml=wrapped_yaml),
                    propagate=True,
                )
                result = client.SemgrepRule.create(
                    payload=create_payload,
                    namespace=namespace,
                )
                logger.info("Created: %s (uuid=%s)", rid, result.uuid)
                created += 1
            except Exception as exc:
                logger.error("Failed to create '%s': %s", rid, exc)
                failed += 1

    logger.info(
        "Import complete: created=%d, updated=%d, skipped=%d, failed=%d.",
        created,
        updated,
        skipped,
        failed,
    )


# ---------------------------------------------------------------------------
# Subcommand: delete
# ---------------------------------------------------------------------------


def cmd_delete(
    client: endorlabs.Client,
    namespace: str,
    name_filter: str,
    *,
    dry_run: bool = False,
) -> list[str]:
    """Delete rules whose ``meta.name`` contains *name_filter*.

    Returns:
        List of deleted rule names (for orphan cleanup).
    """
    logger.info('=== delete: removing rules matching "%s" ===', name_filter)

    rules = client.SemgrepRule.list(
        namespace=namespace,
        filter=f'meta.name contains "{name_filter}"',
    )

    if not rules:
        logger.info("No rules found matching '%s'.", name_filter)
        return []

    logger.info("Found %d rule(s) to delete.", len(rules))
    deleted_names: list[str] = []

    for rule in rules:
        display = _rule_display_name(rule)
        name = rule.meta.name if rule.meta else None

        if dry_run:
            logger.info("[DRY RUN] Would delete: %s", display)
            if name:
                deleted_names.append(name)
            continue

        try:
            client.SemgrepRule.delete(rule, namespace=namespace)
            logger.info("Deleted: %s", display)
            if name:
                deleted_names.append(name)
        except Exception as exc:
            logger.error("Failed to delete %s: %s", display, exc)

    return deleted_names


# ---------------------------------------------------------------------------
# Subcommand: orphans
# ---------------------------------------------------------------------------


def cmd_orphans(
    client: endorlabs.Client,
    namespace: str,
    deleted_names: list[str],
    *,
    dry_run: bool = False,
) -> int:
    """Delete findings that reference rules which no longer exist.

    The API filter on ``meta.description`` does not reliably match
    sub-strings, so this fetches all SAST findings and checks
    ``meta.description`` / ``spec.extra_key`` client-side.

    Returns:
        Number of orphaned findings deleted.
    """
    if not deleted_names:
        logger.info("No deleted rule names provided; skipping orphan cleanup.")
        return 0

    logger.info(
        "=== orphans: cleaning findings for %d deleted rule(s) ===", len(deleted_names)
    )

    # Build a set of lower-cased substrings to match against
    needles = {n.lower() for n in deleted_names}

    all_findings = client.Finding.list(
        namespace=namespace,
        filter="spec.finding_categories contains [FINDING_CATEGORY_SAST]",
        traverse=True,
        max_pages=20,
    )
    logger.info("Scanned %d SAST findings.", len(all_findings))

    orphaned = []
    for f in all_findings:
        desc = (f.meta.description if f.meta else "") or ""
        extra = ""
        if f.spec and hasattr(f.spec, "extra_key"):
            extra = f.spec.extra_key or ""
        searchable = f"{desc} {extra}".lower()
        if any(needle in searchable for needle in needles):
            orphaned.append(f)

    if not orphaned:
        logger.info("No orphaned findings found.")
        return 0

    logger.info("Found %d orphaned finding(s) to delete.", len(orphaned))
    deleted = 0

    for f in orphaned:
        desc = f.meta.description if f.meta else "?"
        if dry_run:
            logger.info("[DRY RUN] Would delete finding: %s (uuid=%s)", desc, f.uuid)
            deleted += 1
            continue

        try:
            client.Finding.delete(f, namespace=namespace)
            logger.info("Deleted finding: %s (uuid=%s)", desc, f.uuid)
            deleted += 1
        except Exception as exc:
            logger.error("Failed to delete finding %s: %s", f.uuid, exc)

    return deleted


# ---------------------------------------------------------------------------
# Subcommand: configure
# ---------------------------------------------------------------------------


def _build_rule_yaml_map(rules_dir: Path) -> dict[str, str]:
    """Build a mapping of rule_id -> wrapped YAML from local files.

    The Endor Labs API re-validates ``spec.yaml`` on every update,
    even when only ``disabled`` is in the update_mask.  The list
    response does *not* return the yaml, so we must supply it from
    the local files.
    """
    id_to_yaml: dict[str, str] = {}
    for yaml_path in _collect_yaml_files(rules_dir):
        try:
            raw = yaml_path.read_text(encoding="utf-8")
            rule_dicts = _parse_yaml_rules(yaml_path)
        except Exception:
            continue
        for rd in rule_dicts:
            rid = str(rd.get("id", ""))
            if rid:
                id_to_yaml[rid] = _wrap_yaml(rd, raw)
    return id_to_yaml


def cmd_configure(
    client: endorlabs.Client,
    namespace: str,
    rules_dir: Path,
    enabled_dir: Path,
    *,
    dry_run: bool = False,
) -> None:
    """Enable rules from *enabled_dir* and disable all others in *rules_dir*.

    Derives the enabled set from the rule ``id`` values found in YAML
    files under *enabled_dir*, and the full set from *rules_dir*.
    """
    logger.info("=== configure: setting enable/disable states ===")

    all_ids = _extract_rule_ids_from_dir(rules_dir)
    enabled_ids = _extract_rule_ids_from_dir(enabled_dir)

    # Build rule_id -> yaml mapping from local files so we can satisfy
    # the API's spec.yaml re-validation requirement on PATCH.
    id_to_yaml = _build_rule_yaml_map(rules_dir)

    logger.info(
        "Enabled set (%d): %s",
        len(enabled_ids),
        ", ".join(sorted(enabled_ids)) or "(none)",
    )
    logger.info(
        "Disabled set (%d): %s",
        len(all_ids - enabled_ids),
        ", ".join(sorted(all_ids - enabled_ids)) or "(none)",
    )

    for rule_id in sorted(all_ids):
        want_enabled = rule_id in enabled_ids

        matches = client.SemgrepRule.list(
            namespace=namespace,
            filter=f'meta.name=="{rule_id}"',
            max_pages=1,
        )
        if not matches:
            logger.warning("Rule '%s' not found on platform; skipping.", rule_id)
            continue

        rule = matches[0]
        display = _rule_display_name(rule)
        action = "enable" if want_enabled else "disable"

        if dry_run:
            logger.info("[DRY RUN] Would %s: %s", action, display)
            continue

        try:
            # The API re-validates spec.yaml on every PATCH, even when
            # only 'disabled' is in the update_mask.  We must include
            # the yaml from local files to avoid a 400 null-parse error.
            rule_yaml = id_to_yaml.get(rule_id)
            if not rule_yaml:
                logger.warning(
                    "No local YAML found for '%s'; skipping configure.", rule_id
                )
                continue
            upd = UpdateSemgrepRulePayload(
                disabled=not want_enabled,
                spec=SemgrepRuleSpec(
                    disabled=not want_enabled,
                    yaml=rule_yaml,
                ),
            )
            client.SemgrepRule.update(
                rule,
                payload=upd,
                update_mask="disabled,spec.disabled,spec.yaml",
            )
            logger.info("%sd: %s", action.capitalize(), display)
        except Exception as exc:
            logger.error("Failed to %s %s: %s", action, display, exc)


# ---------------------------------------------------------------------------
# Subcommand: sync
# ---------------------------------------------------------------------------


def cmd_sync(
    client: endorlabs.Client,
    namespace: str,
    rules_dir: Path,
    enabled_dir: Path,
    *,
    name_filter: str | None = None,
    force: bool = False,
    dry_run: bool = False,
) -> None:
    """Full sync: delete -> orphans -> import -> configure.

    This is the "do everything" command, equivalent to running all four
    subcommands in sequence.
    """
    logger.info("=== sync: full lifecycle ===")

    # Step 1: Delete
    deleted_names: list[str] = []
    if name_filter:
        deleted_names = cmd_delete(client, namespace, name_filter, dry_run=dry_run)
        logger.info("Deleted %d rule(s).", len(deleted_names))
    else:
        logger.info("No --name-filter provided; skipping delete step.")

    # Step 2: Orphan cleanup
    orphans_deleted = cmd_orphans(client, namespace, deleted_names, dry_run=dry_run)
    logger.info("Deleted %d orphaned finding(s).", orphans_deleted)

    # Step 3: Import
    cmd_import(
        client,
        namespace,
        rules_dir,
        force=force,
        dry_run=dry_run,
    )

    # Step 4: Configure
    cmd_configure(client, namespace, rules_dir, enabled_dir, dry_run=dry_run)

    logger.info("=== sync complete ===")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    """Build the argument parser with subcommands."""
    parser = argparse.ArgumentParser(
        prog="sast_rule_manager",
        description="Generic, guardrailed SAST rule manager for Endor Labs.",
    )

    # Common arguments
    parser.add_argument(
        "--namespace",
        required=True,
        help="Target namespace (e.g. tenant.child). Required; no default.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Log planned actions without calling the API.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable DEBUG-level logging.",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    # --- import ---
    p_import = subparsers.add_parser(
        "import",
        help="Import rules from a directory.",
    )
    p_import.add_argument(
        "--rules-dir",
        type=Path,
        required=True,
        help="Directory containing rule YAML files.",
    )
    p_import.add_argument(
        "--force",
        action="store_true",
        help="Update existing rules (matched by meta.name).",
    )

    # --- delete ---
    p_delete = subparsers.add_parser(
        "delete",
        help="Delete rules matching a name filter.",
    )
    p_delete.add_argument(
        "--name-filter",
        required=True,
        help='Substring to match against meta.name (e.g. "endor-sdk").',
    )

    # --- orphans ---
    p_orphans = subparsers.add_parser(
        "orphans",
        help="Clean orphaned findings from deleted rules.",
    )
    p_orphans.add_argument(
        "--deleted-names",
        nargs="+",
        required=True,
        help="Rule names whose findings should be cleaned up.",
    )

    # --- configure ---
    p_configure = subparsers.add_parser(
        "configure",
        help="Enable/disable rules based on directory membership.",
    )
    p_configure.add_argument(
        "--rules-dir",
        type=Path,
        required=True,
        help="Directory containing all rule YAML files.",
    )
    p_configure.add_argument(
        "--enabled-dir",
        type=Path,
        required=True,
        help="Directory whose rules should be enabled; all others disabled.",
    )

    # --- sync ---
    p_sync = subparsers.add_parser(
        "sync",
        help="Full lifecycle: delete -> orphans -> import -> configure.",
    )
    p_sync.add_argument(
        "--rules-dir",
        type=Path,
        required=True,
        help="Directory containing all rule YAML files.",
    )
    p_sync.add_argument(
        "--enabled-dir",
        type=Path,
        required=True,
        help="Directory whose rules should be enabled; all others disabled.",
    )
    p_sync.add_argument(
        "--name-filter",
        default=None,
        help='Substring for delete step (e.g. "endor-sdk"). If omitted, delete is skipped.',
    )
    p_sync.add_argument(
        "--force",
        action="store_true",
        help="Update existing rules during import step.",
    )

    return parser


def main() -> None:
    """Entry point — parse args, set up SDK clients, dispatch subcommand."""
    parser = _build_parser()
    args = parser.parse_args()

    # Configure logging
    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
        stream=sys.stdout,
    )

    logger.info("Namespace: %s", args.namespace)
    if args.dry_run:
        logger.info("*** DRY RUN MODE — no changes will be made ***")

    # Initialize SDK client (credentials from env vars)
    log_level = "DEBUG" if args.verbose else "WARNING"
    client = endorlabs.Client(tenant=args.namespace, logging_level=log_level)

    # Dispatch
    if args.command == "import":
        cmd_import(
            client,
            args.namespace,
            args.rules_dir,
            force=args.force,
            dry_run=args.dry_run,
        )

    elif args.command == "delete":
        deleted = cmd_delete(
            client, args.namespace, args.name_filter, dry_run=args.dry_run
        )
        logger.info("Deleted %d rule(s).", len(deleted))

    elif args.command == "orphans":
        count = cmd_orphans(
            client,
            args.namespace,
            args.deleted_names,
            dry_run=args.dry_run,
        )
        logger.info("Deleted %d orphaned finding(s).", count)

    elif args.command == "configure":
        cmd_configure(
            client,
            args.namespace,
            args.rules_dir,
            args.enabled_dir,
            dry_run=args.dry_run,
        )

    elif args.command == "sync":
        cmd_sync(
            client,
            args.namespace,
            args.rules_dir,
            args.enabled_dir,
            name_filter=args.name_filter,
            force=args.force,
            dry_run=args.dry_run,
        )

    logger.info("--- Done ---")


if __name__ == "__main__":
    main()
