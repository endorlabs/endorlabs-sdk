"""
Day1 Rules Calibration Script.

This script performs initial rules calibration by:
1. Ensuring AI model rules are ALWAYS enabled (regardless of defined_by)
2. Disabling 3rd-party and Endor Labs rules (unless they're AI model rules)

Priority Logic:
- AI model rules take precedence: if a rule is identified as an AI model rule,
  it will be enabled even if defined_by="Endor Labs" or "3rd-Party"
- Non-AI model rules with defined_by="3rd-Party" or "Endor Labs" will be disabled
- User-defined rules (defined_by = tenant name) are left as-is
"""

import argparse
import logging
import os
import sys
from pathlib import Path
from typing import List, Tuple

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from endor_cockpit.api_client import APIClient
from endor_cockpit.resources.semgrep_rule import (
    SemgrepRule,
    SemgrepRuleSpec,
    UpdateSemgrepRulePayload,
    list_semgrep_rules,
    update_semgrep_rule,
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
        # Check for AI model detection patterns (e.g., py-detect-openai-models, js-detect-azureopenai-models)
        if "-detect-" in rule_id_lower and "model" in rule_id_lower:
            # Common AI model detection patterns
            ai_providers = ["openai", "azureopenai", "anthropic", "google", "aws", "perplexity", "deepseek"]
            for provider in ai_providers:
                if provider in rule_id_lower:
                    return True
    
    # Check rule name for ai_model patterns
    if rule.meta and rule.meta.name:
        name_lower = rule.meta.name.lower()
        if "ai model" in name_lower or "ai_model" in name_lower or "ai-model" in name_lower:
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


def should_disable_rule(rule: SemgrepRule) -> bool:
    """
    Determine if a rule should be disabled.
    
    Rules should be disabled if:
    - defined_by is "3rd-Party" or "Endor Labs"
    - AND the rule is NOT an AI model rule (AI model rules take precedence)
    """
    # AI model rules should never be disabled
    if is_ai_model_rule(rule):
        return False
    
    # Check defined_by
    if rule.spec and rule.spec.defined_by:
        defined_by = rule.spec.defined_by
        if defined_by in ["3rd-Party", "Endor Labs"]:
            return True
    
    return False


def should_enable_rule(rule: SemgrepRule) -> bool:
    """
    Determine if a rule should be enabled.
    
    Rules should be enabled if:
    - They are AI model rules (regardless of defined_by)
    """
    return is_ai_model_rule(rule)


def update_rule_state(
    client: APIClient, namespace: str, rule: SemgrepRule, enable: bool
) -> bool:
    """Update a rule's enabled/disabled state."""
    # Check current state
    is_currently_enabled = (
        rule.disabled is False and 
        (not rule.spec or rule.spec.disabled is False)
    )
    is_currently_disabled = (
        rule.disabled is True or 
        (rule.spec and rule.spec.disabled is True)
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
        description="Day1 rules calibration: Enable AI model rules, disable 3rd-party/Endor Labs rules"
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
    parser.add_argument(
        "--skip-disable",
        action="store_true",
        help="Skip disabling 3rd-party/Endor Labs rules (only enable AI model rules)",
    )
    parser.add_argument(
        "--skip-enable",
        action="store_true",
        help="Skip enabling AI model rules (only disable 3rd-party/Endor Labs rules)",
    )

    args = parser.parse_args()

    # Validate namespace is provided
    if not args.namespace:
        logger.error(
            "Namespace is required. Set --namespace argument or ENDOR_NAMESPACE environment variable."
        )
        return 1

    setup_logging()
    logger.info("Starting Day1 rules calibration")

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

    # Categorize rules
    ai_model_rules: List[SemgrepRule] = []
    rules_to_disable: List[SemgrepRule] = []
    user_rules: List[SemgrepRule] = []
    
    for rule in all_rules:
        if is_ai_model_rule(rule):
            ai_model_rules.append(rule)
        elif should_disable_rule(rule):
            rules_to_disable.append(rule)
        else:
            user_rules.append(rule)
    
    logger.info(f"\nRule categorization:")
    logger.info(f"  - AI model rules: {len(ai_model_rules)}")
    logger.info(f"  - Rules to disable (3rd-party/Endor Labs): {len(rules_to_disable)}")
    logger.info(f"  - User-defined rules: {len(user_rules)}")
    
    # Enable AI model rules
    if not args.skip_enable:
        logger.info(f"\n{'[DRY RUN] ' if args.dry_run else ''}Enabling {len(ai_model_rules)} AI model rules...")
        
        enabled_count = 0
        already_enabled_count = 0
        failed_count = 0
        
        for rule in sorted(
            ai_model_rules,
            key=lambda r: r.spec.rule.id if r.spec and r.spec.rule else "unknown",
        ):
            rule_id = rule.spec.rule.id if rule.spec and rule.spec.rule else "unknown"
            defined_by = rule.spec.defined_by if rule.spec else "unknown"
            
            is_already_enabled = (
                rule.disabled is False and 
                (not rule.spec or rule.spec.disabled is False)
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
                        logger.warning(f"  ✗ Failed to enable: {rule_id}")
                        failed_count += 1
        
        logger.info(f"\n✓ Enabled {enabled_count} AI model rules")
        if already_enabled_count > 0:
            logger.info(f"⊘ {already_enabled_count} were already enabled")
        if failed_count > 0:
            logger.warning(f"✗ Failed to enable {failed_count} rules")
    
    # Disable 3rd-party/Endor Labs rules
    if not args.skip_disable:
        logger.info(f"\n{'[DRY RUN] ' if args.dry_run else ''}Disabling {len(rules_to_disable)} 3rd-party/Endor Labs rules...")
        
        disabled_count = 0
        already_disabled_count = 0
        failed_count = 0
        
        for rule in sorted(
            rules_to_disable,
            key=lambda r: r.spec.rule.id if r.spec and r.spec.rule else "unknown",
        ):
            rule_id = rule.spec.rule.id if rule.spec and rule.spec.rule else "unknown"
            defined_by = rule.spec.defined_by if rule.spec else "unknown"
            
            is_already_disabled = (
                rule.disabled is True or 
                (rule.spec and rule.spec.disabled is True)
            )
            
            if args.dry_run:
                status = "already disabled" if is_already_disabled else "would disable"
                logger.info(f"  [DRY RUN] {status}: {rule_id} (defined_by={defined_by})")
                if not is_already_disabled:
                    disabled_count += 1
                else:
                    already_disabled_count += 1
            else:
                if is_already_disabled:
                    logger.debug(f"  ⊘ Already disabled: {rule_id}")
                    already_disabled_count += 1
                else:
                    if update_rule_state(client, args.namespace, rule, enable=False):
                        logger.info(f"  ✓ Disabled: {rule_id} (defined_by={defined_by})")
                        disabled_count += 1
                    else:
                        logger.warning(f"  ✗ Failed to disable: {rule_id}")
                        failed_count += 1
        
        logger.info(f"\n✓ Disabled {disabled_count} rules")
        if already_disabled_count > 0:
            logger.info(f"⊘ {already_disabled_count} were already disabled")
        if failed_count > 0:
            logger.warning(f"✗ Failed to disable {failed_count} rules")
    
    logger.info("\n✓ Rules calibration complete")
    return 0


if __name__ == "__main__":
    sys.exit(main())










