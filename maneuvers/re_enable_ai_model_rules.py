"""
Re-enable all SAST/Semgrep rules around AI models.

This script is a convenience wrapper around calibrate_rules.py that:
1. Enables all AI model rules (regardless of defined_by)
2. Skips disabling any other rules (only enables AI model rules)

Usage:
    python maneuvers/re_enable_ai_model_rules.py [--namespace NAMESPACE] [--dry-run]

If --namespace is not provided, it will use ENDOR_NAMESPACE environment variable.
"""

import argparse
import logging
import os
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from endor_cockpit.api_client import APIClient
from endor_cockpit.resources.semgrep_rule import (
    SemgrepRule,
    list_semgrep_rules,
    update_semgrep_rule,
    UpdateSemgrepRulePayload,
    SemgrepRuleSpec,
)
from endor_cockpit.utils.logging_config import setup_logging

logger = logging.getLogger(__name__)


def is_ai_model_rule(rule: SemgrepRule) -> bool:
    """
    Determine if a rule is an AI model rule.
    
    Checks multiple indicators:
    - endor_targets contains ECOSYSTEM_AI_MODEL
    - Rule ID or name contains ai_model/ai-model patterns
    - Rule ID matches AI model detection patterns (e.g., *-detect-*-models)
    - Metadata category indicates AI models
    """
    if not rule.spec or not rule.spec.rule:
        return False
    
    native_rule = rule.spec.rule
    
    # Check endor_targets in metadata
    if native_rule.metadata and native_rule.metadata.endor_targets:
        for target in native_rule.metadata.endor_targets:
            target_str = str(target).upper()
            if "AI_MODEL" in target_str or "ECOSYSTEM_AI_MODEL" in target_str:
                return True
    
    # Check rule ID for ai_model patterns
    if native_rule.id:
        rule_id_lower = native_rule.id.lower()
        # Check for explicit ai_model/ai-model patterns
        if "ai_model" in rule_id_lower or "ai-model" in rule_id_lower:
            return True
        # Check for AI model detection patterns
        if "-detect-" in rule_id_lower and "model" in rule_id_lower:
            # Common AI model detection patterns
            ai_providers = [
                "openai",
                "azureopenai",
                "anthropic",
                "google",
                "aws",
                "perplexity",
                "deepseek",
            ]
            for provider in ai_providers:
                if provider in rule_id_lower:
                    return True
    
    # Check rule name for ai_model patterns
    if rule.meta and rule.meta.name:
        name_lower = rule.meta.name.lower()
        if (
            "ai model" in name_lower
            or "ai_model" in name_lower
            or "ai-model" in name_lower
        ):
            return True
    
    # Check metadata category
    if native_rule.metadata:
        if native_rule.metadata.category:
            category_lower = native_rule.metadata.category.lower()
            if "ai" in category_lower and "model" in category_lower:
                return True
        
        # Check subcategory
        if native_rule.metadata.subcategory:
            for subcat in native_rule.metadata.subcategory:
                subcat_lower = str(subcat).lower()
                if "ai" in subcat_lower and "model" in subcat_lower:
                    return True
    
    # Check description for AI model references
    if native_rule.metadata and native_rule.metadata.description:
        desc_lower = native_rule.metadata.description.lower()
        if "ai model" in desc_lower or "ai_model" in desc_lower:
            return True
    
    # Check rule message for AI model references
    if native_rule.message:
        message_lower = native_rule.message.lower()
        if "ai model" in message_lower or "ai_model" in message_lower:
            return True
    
    # Check technology tags
    if native_rule.metadata and native_rule.metadata.technology:
        for tech in native_rule.metadata.technology:
            tech_lower = str(tech).lower()
            if "ai" in tech_lower and "model" in tech_lower:
                return True
    
    return False


def update_rule_state(
    client: APIClient, namespace: str, rule: SemgrepRule, enable: bool
) -> bool:
    """Update a rule's enabled/disabled state."""
    # Check current state
    is_currently_enabled = (
        rule.disabled is False and (not rule.spec or rule.spec.disabled is False)
    )
    is_currently_disabled = (
        rule.disabled is True or (rule.spec and rule.spec.disabled is True)
    )
    
    if enable and is_currently_enabled:
        return True  # Already in desired state
    if not enable and is_currently_disabled:
        return True  # Already in desired state
    
    try:
        payload = UpdateSemgrepRulePayload(
            disabled=not enable,  # disabled=True means not enabled
            spec=SemgrepRuleSpec(disabled=not enable) if rule.spec else None,
        )
        update_mask = "disabled,spec.disabled"
        updated = update_semgrep_rule(
            client, namespace, rule.uuid, payload, update_mask
        )
        return updated is not None
    except Exception as e:
        # Check if it's a 501 Method Not Allowed error (read-only rules)
        if "501" in str(e) or "Method Not Allowed" in str(e):
            defined_by = rule.spec.defined_by if rule.spec else "unknown"
            rule_id = rule.spec.rule.id if rule.spec and rule.spec.rule else "unknown"
            logger.warning(
                f"⚠ Cannot update rule {rule_id}: "
                f"Rule is read-only (defined_by={defined_by})"
            )
        else:
            logger.error(f"✗ Error updating rule {rule.uuid}: {e}")
        return False


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description="Re-enable all SAST/Semgrep rules around AI models"
    )
    parser.add_argument(
        "--namespace",
        default=os.getenv("ENDOR_NAMESPACE"),
        help="Tenant namespace (e.g., 'tenant.namespace'). Defaults to ENDOR_NAMESPACE env var if set.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Dry run mode - don't make actual changes",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Verbose output - show all rule details",
    )

    args = parser.parse_args()

    # Validate namespace is provided
    if not args.namespace:
        logger.error(
            "Namespace is required. Set --namespace argument or ENDOR_NAMESPACE environment variable."
        )
        print(
            "\nERROR: Namespace is required.\n"
            "Set --namespace argument or ENDOR_NAMESPACE environment variable.\n"
            "Example: python maneuvers/re_enable_ai_model_rules.py --namespace tenant.namespace"
        )
        return 1

    setup_logging()
    logger.info("Re-enabling all AI model rules")

    # Initialize API client
    try:
        client = APIClient()
    except Exception as e:
        logger.error(f"Failed to initialize API client: {e}")
        return 1

    # Load all rules from API
    logger.info(f"Loading rules from API for namespace: {args.namespace}")
    try:
        all_rules = list_semgrep_rules(client, args.namespace)
        logger.info(f"Loaded {len(all_rules)} rules from API")
    except Exception as e:
        logger.error(f"Error loading rules: {e}", exc_info=True)
        return 1

    # Find AI model rules
    ai_model_rules: list[SemgrepRule] = []
    for rule in all_rules:
        if is_ai_model_rule(rule):
            ai_model_rules.append(rule)
    
    logger.info(f"\nFound {len(ai_model_rules)} AI model rules")

    # Enable AI model rules
    logger.info(
        f"\n{'[DRY RUN] ' if args.dry_run else ''}Enabling {len(ai_model_rules)} AI model rules..."
    )
    
    enabled_count = 0
    already_enabled_count = 0
    failed_count = 0
    read_only_count = 0
    
    for rule in sorted(
        ai_model_rules,
        key=lambda r: r.spec.rule.id if r.spec and r.spec.rule else "unknown",
    ):
        rule_id = rule.spec.rule.id if rule.spec and rule.spec.rule else "unknown"
        defined_by = rule.spec.defined_by if rule.spec else "unknown"
        
        is_already_enabled = (
            rule.disabled is False and (not rule.spec or rule.spec.disabled is False)
        )
        
        if args.dry_run:
            status = "already enabled" if is_already_enabled else "would enable"
            logger.info(f"  [DRY RUN] {status}: {rule_id} (defined_by={defined_by})")
            if not is_already_enabled:
                enabled_count += 1
            else:
                already_enabled_count += 1
        else:
            if is_already_enabled:
                logger.debug(f"  ⊘ Already enabled: {rule_id}")
                already_enabled_count += 1
            else:
                if update_rule_state(client, args.namespace, rule, enable=True):
                    logger.info(f"  ✓ Enabled: {rule_id} (defined_by={defined_by})")
                    enabled_count += 1
                else:
                    # Check if it's read-only
                    if rule.spec and rule.spec.defined_by in ["3rd-Party", "Endor Labs"]:
                        read_only_count += 1
                    logger.warning(f"  ✗ Failed to enable: {rule_id}")
                    failed_count += 1
    
    logger.info(f"\n✓ Enabled {enabled_count} AI model rules")
    if already_enabled_count > 0:
        logger.info(f"⊘ {already_enabled_count} were already enabled")
    if read_only_count > 0:
        logger.warning(
            f"⚠ {read_only_count} rules are read-only and cannot be modified"
        )
    if failed_count > 0:
        logger.warning(f"✗ Failed to enable {failed_count} rules")
    
    logger.info("\n✓ AI model rules re-enablement complete")
    return 0


if __name__ == "__main__":
    sys.exit(main())
