"""Semgrep rule management workflows.

Provides composable functions for importing/exporting Semgrep rules
from YAML, calibrating rules (enable AI model rules, disable others),
and classifying rules by type.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

import yaml

from ..common import WorkflowResult
from ..wire_access import as_dict, dict_str, model_to_dict, nested_dict, nested_str

if TYPE_CHECKING:
    from endorlabs import Client
    from endorlabs.resources.semgrep_rule import SemgrepRule

from endorlabs.utils.logging_config import get_resource_logger

logger = get_resource_logger(__name__)


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------


@dataclass
class ImportResult(WorkflowResult):
    """Result of a YAML rule import operation."""

    created: int = 0
    updated: int = 0
    skipped: int = 0
    failed: int = 0


@dataclass
class ExportResult(WorkflowResult):
    """Result of a rule export operation."""

    exported: int = 0
    total: int = 0
    paths: list[str] = field(default_factory=list[str])


@dataclass
class CalibrationResult(WorkflowResult):
    """Result of a rule calibration operation."""

    enabled: int = 0
    disabled: int = 0
    skipped: int = 0
    failed: int = 0
    already_correct: int = 0
    total: int = 0


# ---------------------------------------------------------------------------
# Rule classification (pure domain logic)
# ---------------------------------------------------------------------------

_AI_PROVIDERS = frozenset(
    {
        "openai",
        "azureopenai",
        "anthropic",
        "google",
        "aws",
        "perplexity",
        "deepseek",
    }
)


def _text_has_ai_model(text: str) -> bool:
    """Check if text contains an AI model reference (case-insensitive)."""
    lower = text.lower()
    return "ai model" in lower or "ai_model" in lower or "ai-model" in lower


def _check_endor_targets(metadata: Any) -> bool:
    """Return True if endor_targets indicates an AI model rule."""
    if not metadata or not metadata.endor_targets:
        return False
    return any(
        "AI_MODEL" in str(t).upper() or "ECOSYSTEM_AI_MODEL" in str(t).upper()
        for t in metadata.endor_targets
    )


def _check_rule_id(rule_id: str | None) -> bool:
    """Return True if the rule ID indicates an AI model rule."""
    if not rule_id:
        return False
    rid = rule_id.lower()
    if "ai_model" in rid or "ai-model" in rid:
        return True
    return "-detect-" in rid and "model" in rid and any(p in rid for p in _AI_PROVIDERS)


def _check_metadata_fields(metadata: Any) -> bool:
    """Return True if metadata category/subcategory/desc/tech match AI model."""
    if not metadata:
        return False
    if metadata.category and _text_has_ai_model(metadata.category):
        return True
    if metadata.subcategory and any(
        _text_has_ai_model(str(s)) for s in metadata.subcategory
    ):
        return True
    if metadata.description and _text_has_ai_model(metadata.description):
        return True
    return bool(
        metadata.technology
        and any(_text_has_ai_model(str(t)) for t in metadata.technology)
    )


def is_ai_model_rule(rule: SemgrepRule) -> bool:
    """Determine whether a Semgrep rule targets AI models.

    Checks multiple indicators: ``endor_targets``, rule ID patterns,
    metadata category/subcategory, description, message, and technology
    tags.

    This is a **pure function** — no API calls, no side effects.

    Args:
        rule: A ``SemgrepRule`` resource from the API.

    Returns:
        True if the rule is classified as an AI model rule.
    """
    if not rule.spec or not rule.spec.rule:
        return False

    native = rule.spec.rule

    if _check_endor_targets(native.metadata):
        return True
    if _check_rule_id(native.id):
        return True
    if rule.meta and rule.meta.name and _text_has_ai_model(rule.meta.name):
        return True
    if _check_metadata_fields(native.metadata):
        return True
    return bool(native.message and _text_has_ai_model(native.message))


# ---------------------------------------------------------------------------
# YAML parsing helpers
# ---------------------------------------------------------------------------


def _parse_yaml_file(path: Path) -> list[dict[str, Any]]:
    """Parse a Semgrep-compatible YAML file into rule dicts.

    Handles ``rules: [...]`` wrappers and bare rule dicts.

    Args:
        path: Path to the YAML file.

    Returns:
        List of parsed rule dicts. Empty list on parse failure.
    """
    text = path.read_text(encoding="utf-8")
    doc = yaml.safe_load(text)

    if doc is None:
        logger.warning("Empty YAML file: %s", path)
        return []

    doc_dict = as_dict(doc)
    if "rules" in doc_dict:
        rules_raw = doc_dict["rules"]
        if isinstance(rules_raw, list):
            rules_list = cast("list[Any]", rules_raw)
            return [
                cast("dict[str, Any]", item)
                for item in rules_list
                if isinstance(item, dict)
            ]
        return []

    if isinstance(doc, dict):
        return [cast("dict[str, Any]", doc)]

    logger.warning("Unexpected YAML structure in %s", path)
    return []


def _rule_display_id(rule_dict: dict[str, Any]) -> str:
    """Return a human-readable identifier from a parsed rule dict."""
    return str(rule_dict.get("id", rule_dict.get("message", "unknown")))[:80]


def _wrap_yaml(rule_dict: dict[str, Any], raw_yaml: str) -> str:
    """Ensure YAML content is wrapped in a ``rules:`` envelope."""
    if raw_yaml.lstrip().startswith("rules:"):
        return raw_yaml
    return yaml.dump(
        {"rules": [rule_dict]},
        default_flow_style=False,
        allow_unicode=True,
        sort_keys=False,
    )


# ---------------------------------------------------------------------------
# Import rules from YAML
# ---------------------------------------------------------------------------


def _extract_rule_description(rule_dict: dict[str, Any]) -> str:
    """Extract a description from a parsed rule dict, truncated to 1024 bytes."""
    metadata = nested_dict(rule_dict, "metadata")
    desc = dict_str(metadata, "description") or dict_str(rule_dict, "message")
    if len(desc.encode("utf-8")) > 1024:
        desc = desc[:1020] + "..."
    return desc


def _import_single_rule(
    client: Client,
    namespace: str,
    rule_dict: dict[str, Any],
    wrapped_yaml: str,
    *,
    force: bool,
    result: ImportResult,
) -> None:
    """Import (create or update) a single rule, mutating *result* in place."""
    from endorlabs.resources.semgrep_rule import (
        CreateSemgrepRulePayload,
        SemgrepNativeRule,
        SemgrepRuleMetaCreate,
        SemgrepRuleSpec,
        UpdateSemgrepRulePayload,
    )

    display_id = _rule_display_id(rule_dict)
    rule_name = str(rule_dict.get("id", ""))

    from endorlabs import F

    existing_rules = client.SemgrepRule.list(
        namespace=namespace,
        filter=F("meta.name") == rule_name,
        max_pages=1,
    )
    existing = existing_rules[0] if existing_rules else None

    if existing and not force:
        existing_uuid = dict_str(model_to_dict(existing), "uuid")
        logger.info(
            "SKIP: Rule '%s' already exists (uuid=%s).", display_id, existing_uuid
        )
        result.skipped += 1
        return

    desc = _extract_rule_description(rule_dict)

    if existing and force:
        try:
            payload = UpdateSemgrepRulePayload(
                meta=SemgrepRuleMetaCreate(name=rule_name, description=desc),
                spec=SemgrepRuleSpec(yaml=wrapped_yaml),
            )
            client.SemgrepRule.update(
                existing, payload=payload, update_mask="spec,meta.description"
            )
            existing_uuid = dict_str(model_to_dict(existing), "uuid")
            logger.info("Updated: %s (uuid=%s)", display_id, existing_uuid)
            result.updated += 1
        except Exception as exc:
            logger.error("Unable to update '%s': %s", display_id, exc)
            result.failed += 1
            result.errors.append(f"update {display_id}: {exc}")
        return

    try:
        native_rule = SemgrepNativeRule(
            id=rule_dict.get("id"),
            languages=rule_dict.get("languages"),
            message=rule_dict.get("message"),
            severity=rule_dict.get("severity"),
            pattern=rule_dict.get("pattern"),
            mode=rule_dict.get("mode"),
        )
        payload = CreateSemgrepRulePayload(
            meta=SemgrepRuleMetaCreate(name=rule_name, description=desc),
            spec=SemgrepRuleSpec(rule=native_rule, yaml=wrapped_yaml),
            propagate=True,
        )
        created_rule = client.SemgrepRule.create(payload=payload, namespace=namespace)
        created_uuid = dict_str(model_to_dict(created_rule), "uuid")
        logger.info("Created: %s (uuid=%s)", display_id, created_uuid)
        result.created += 1
    except Exception as exc:
        logger.error("Unable to create '%s': %s", display_id, exc)
        result.failed += 1
        result.errors.append(f"create {display_id}: {exc}")


def import_rules_from_yaml(
    client: Client,
    namespace: str,
    paths: list[Path],
    *,
    dry_run: bool = False,
    force: bool = False,
) -> ImportResult:
    """Import Semgrep rules from YAML files into the platform.

    Parses each YAML file, checks for existing rules by name, and
    creates or updates rules via the Client facade.

    Args:
        client: Authenticated ``endorlabs.Client`` instance.
        namespace: Namespace to import into.
        paths: List of YAML file paths to import.
        dry_run: When True, parse and validate but skip API calls.
        force: When True, overwrite existing rules with the same name.

    Returns:
        ImportResult with counts of created / updated / skipped / failed.
    """
    result = ImportResult()

    for yaml_path in paths:
        try:
            rule_dicts = _parse_yaml_file(yaml_path)
        except Exception as exc:
            logger.error("Unable to parse %s: %s", yaml_path, exc)
            result.failed += 1
            result.errors.append(f"{yaml_path}: {exc}")
            continue

        if not rule_dicts:
            continue

        raw_yaml = yaml_path.read_text(encoding="utf-8")

        for rule_dict in rule_dicts:
            if dry_run:
                logger.info("[DRY RUN] Would import: %s", _rule_display_id(rule_dict))
                result.skipped += 1
                continue

            wrapped_yaml = _wrap_yaml(rule_dict, raw_yaml)
            _import_single_rule(
                client, namespace, rule_dict, wrapped_yaml, force=force, result=result
            )

    if result.failed:
        result.status = "partial" if (result.created or result.updated) else "error"
    result.message = (
        f"Import complete: created={result.created}, updated={result.updated}, "
        f"skipped={result.skipped}, failed={result.failed}."
    )
    return result


# ---------------------------------------------------------------------------
# Export rules to YAML
# ---------------------------------------------------------------------------


def export_rules_to_yaml(
    client: Client,
    namespace: str,
    output_dir: Path,
    *,
    filter_expr: str | None = None,
    name: str | None = None,
    uuid: str | None = None,
    export_all: bool = False,
    dry_run: bool = False,
) -> ExportResult:
    """Export Semgrep rules from the platform to YAML files.

    Args:
        client: Authenticated ``endorlabs.Client`` instance.
        namespace: Namespace to export from.
        output_dir: Directory to write YAML files into.
        filter_expr: API filter expression for rule selection.
        name: Export rule(s) matching this name.
        uuid: Export a single rule by UUID.
        export_all: Export all rules in the namespace.
        dry_run: When True, list rules but skip writing files.

    Returns:
        ExportResult with counts and written file paths.
    """
    # Resolve rules to export
    rules: list[Any] = []
    if uuid:
        rule = client.SemgrepRule.get(uuid, namespace=namespace)
        rules = [rule]
    elif name:
        from endorlabs import F

        rules = client.SemgrepRule.list(
            namespace=namespace,
            filter=F("meta.name") == name,
        )
        if not rules:
            rules = client.SemgrepRule.list(
                namespace=namespace,
                filter=F("meta.name").matches(name),
            )
    elif filter_expr:
        rules = client.SemgrepRule.list(namespace=namespace, filter=filter_expr)
    elif export_all:
        rules = client.SemgrepRule.list(namespace=namespace)

    result = ExportResult(total=len(rules))

    if not rules:
        result.message = "No matching rules found."
        return result

    import re

    for rule in rules:
        rule_wire = model_to_dict(rule)
        spec = nested_dict(rule_wire, "spec")
        # Determine display ID and filename
        native_rule = nested_dict(spec, "rule")
        display_id = (
            dict_str(native_rule, "id")
            or nested_str(rule_wire, "meta", "name")
            or dict_str(rule_wire, "uuid")
        )
        sanitized = re.sub(r'[<>:"/\\|?*\s]+', "-", display_id)
        sanitized = re.sub(r"-{2,}", "-", sanitized).strip("-.")
        filename = (sanitized or "unknown") + ".yaml"

        # Build YAML content
        if dict_str(spec, "yaml"):
            yaml_content = dict_str(spec, "yaml")
        else:
            yaml_content = yaml.dump(
                {
                    "rules": [
                        {
                            "id": dict_str(rule_wire, "uuid"),
                            "message": "No rule definition available",
                        }
                    ]
                },
                default_flow_style=False,
            )

        if dry_run:
            logger.info(
                "[DRY RUN] Would write: %s (%d bytes)", filename, len(yaml_content)
            )
            result.exported += 1
            continue

        from endorlabs.utils.path_safety import safe_write_text

        dest = output_dir / filename
        safe_write_text(output_dir, dest, yaml_content)
        result.exported += 1
        result.paths.append(str(dest))
        logger.info("Exported: %s (%d bytes)", dest, len(yaml_content))

    result.message = f"Exported {result.exported}/{result.total} rule(s)."
    return result


# ---------------------------------------------------------------------------
# Calibrate rules
# ---------------------------------------------------------------------------


def calibrate_rules(
    client: Client,
    namespace: str,
    *,
    enable_ai_models: bool = True,
    disable_third_party: bool = True,
    dry_run: bool = False,
) -> CalibrationResult:
    """Day-1 rules calibration: enable AI model rules, disable others.

    Iterates all Semgrep rules in *namespace* and applies the following
    priority logic:

    - AI model rules are always enabled (regardless of ``defined_by``).
    - Non-AI rules with ``defined_by`` in ``{"3rd-Party", "Endor Labs"}``
      are disabled.
    - User-defined rules are left as-is.

    Args:
        client: Authenticated ``endorlabs.Client`` instance.
        namespace: Namespace to calibrate.
        enable_ai_models: When True, enable all AI model rules.
        disable_third_party: When True, disable 3rd-party / Endor Labs rules.
        dry_run: When True, compute changes but skip API calls.

    Returns:
        CalibrationResult with counts.
    """
    from endorlabs.resources.semgrep_rule import (
        SemgrepRuleSpec,
        UpdateSemgrepRulePayload,
    )

    all_rules = client.SemgrepRule.list(namespace=namespace)

    result = CalibrationResult(total=len(all_rules))

    for rule in all_rules:
        rule_wire = model_to_dict(rule)
        spec = nested_dict(rule_wire, "spec")
        is_ai = is_ai_model_rule(rule)
        defined_by = dict_str(spec, "defined_by") or None
        is_third_party = defined_by in {"3rd-Party", "Endor Labs"}

        is_currently_disabled = (
            rule_wire.get("disabled") is True or spec.get("disabled") is True
        )

        # Determine desired state
        if is_ai and enable_ai_models:
            want_enabled = True
        elif not is_ai and is_third_party and disable_third_party:
            want_enabled = False
        else:
            result.skipped += 1
            continue

        # Check if already correct
        if want_enabled and not is_currently_disabled:
            result.already_correct += 1
            continue
        if not want_enabled and is_currently_disabled:
            result.already_correct += 1
            continue

        if dry_run:
            action = "enable" if want_enabled else "disable"
            native_rule = nested_dict(spec, "rule")
            rule_id = dict_str(native_rule, "id") or dict_str(rule_wire, "uuid")
            logger.info("[DRY RUN] Would %s: %s", action, rule_id)
            if want_enabled:
                result.enabled += 1
            else:
                result.disabled += 1
            continue

        # Perform update
        try:
            payload = UpdateSemgrepRulePayload(
                disabled=not want_enabled,
                spec=SemgrepRuleSpec(disabled=not want_enabled) if spec else None,
            )
            client.SemgrepRule.update(
                rule, payload=payload, update_mask="disabled,spec.disabled"
            )
            if want_enabled:
                result.enabled += 1
            else:
                result.disabled += 1
        except Exception as exc:
            exc_str = str(exc)
            rule_uuid = dict_str(rule_wire, "uuid")
            if "501" in exc_str or "Method Not Allowed" in exc_str:
                logger.warning("Cannot update read-only rule '%s'", rule_uuid)
            else:
                logger.error("Unable to update rule '%s': %s", rule_uuid, exc)
            result.failed += 1
            result.errors.append(f"{rule_uuid}: {exc}")

    if result.failed:
        result.status = "partial"
    result.message = (
        f"Calibration complete: enabled={result.enabled}, disabled={result.disabled}, "
        f"skipped={result.skipped}, already_correct={result.already_correct}, "
        f"failed={result.failed}."
    )
    return result
