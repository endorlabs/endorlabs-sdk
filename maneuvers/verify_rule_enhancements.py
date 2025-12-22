"""
Script to verify that enabled rules satisfy the requested enhancements.

This script:
1. Loads all rules from the API
2. Checks for enhanced versions (-v2) of rules that should have been enhanced
3. Verifies that the enhancements match the requirements from FN_ANALYSIS.md
4. Checks for new rules (XPath Injection, Insecure Cookie)
5. Reports on the status of each requirement
"""

import argparse
import sys
from pathlib import Path
from typing import Dict, List, Optional, Set

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from endor_cockpit.api_client import APIClient
from endor_cockpit.resources.semgrep_rule import (
    SemgrepRule,
    list_semgrep_rules,
)
from endor_cockpit.utils.logging_config import setup_logging

import logging

logger = logging.getLogger(__name__)

# Rules that should have enhanced versions
RULES_TO_ENHANCE = {
    "python-path-traversal",
    "python_random_rule-random",
    "python_crypto_rule-hashlib-new-insecure-functions",
    "java-spring-sql-injection-comprehensive",
    "java_crypto_rule-WeakMessageDigest",
    "java_crypto_rule-CipherDESInsecure",
}

# New rules that should exist
NEW_RULES = {
    "python-xpath-injection",
    "python-flask-insecure-cookie",
}


def check_pattern_in_rule(rule: SemgrepRule, pattern_type: str, pattern_text: str) -> bool:
    """Check if a pattern exists in a rule."""
    if not rule.spec or not rule.spec.rule:
        return False
    
    native_rule = rule.spec.rule
    rule_dict = native_rule.model_dump(exclude_none=True)
    
    # Check pattern_sources
    if pattern_type == "source":
        sources = rule_dict.get("pattern_sources", [])
        for source in sources:
            if isinstance(source, dict):
                pat = source.get("pattern", "")
            else:
                pat = getattr(source, "pattern", "") if hasattr(source, "pattern") else ""
            if pattern_text.lower() in pat.lower():
                return True
    
    # Check pattern_sinks
    if pattern_type == "sink":
        sinks = rule_dict.get("pattern_sinks", [])
        for sink in sinks:
            if isinstance(sink, dict):
                pat = sink.get("pattern", "")
            else:
                pat = getattr(sink, "pattern", "") if hasattr(sink, "pattern") else ""
            if pattern_text.lower() in pat.lower():
                return True
    
    # Check pattern_propagators
    if pattern_type == "propagator":
        propagators = rule_dict.get("pattern_propagators", [])
        for prop in propagators:
            if isinstance(prop, dict):
                pat = prop.get("pattern", "")
            else:
                pat = getattr(prop, "pattern", "") if hasattr(prop, "pattern") else ""
            if pattern_text.lower() in pat.lower():
                return True
    
    # Check pattern_either
    if pattern_type == "pattern":
        patterns = rule_dict.get("pattern_either", [])
        for pat_obj in patterns:
            if isinstance(pat_obj, dict):
                pat = pat_obj.get("pattern", "")
            else:
                pat = getattr(pat_obj, "pattern", "") if hasattr(pat_obj, "pattern") else ""
            if pattern_text.lower() in pat.lower():
                return True
    
    # Check patterns (nested structure)
    patterns_list = rule_dict.get("patterns", [])
    for pat_obj in patterns_list:
        if isinstance(pat_obj, dict):
            # Check pattern_either_new (raw JSON field)
            if "pattern_either_new" in pat_obj:
                for sub_pat in pat_obj["pattern_either_new"]:
                    if isinstance(sub_pat, dict):
                        pat = sub_pat.get("pattern", "")
                    else:
                        pat = str(sub_pat)
                    if pattern_text.lower() in pat.lower():
                        return True
            # Check pattern field directly
            pat = pat_obj.get("pattern", "")
            if pattern_text.lower() in pat.lower():
                return True
        else:
            pat = getattr(pat_obj, "pattern", "") if hasattr(pat_obj, "pattern") else ""
            if pattern_text.lower() in pat.lower():
                return True
    
    return False


def check_regex_in_rule(rule: SemgrepRule, regex_pattern: str) -> bool:
    """Check if a regex pattern exists in metavariable_regex."""
    if not rule.spec or not rule.spec.rule:
        return False
    
    native_rule = rule.spec.rule
    rule_dict = native_rule.model_dump(exclude_none=True)
    
    patterns_list = rule_dict.get("patterns", [])
    for pat_obj in patterns_list:
        if isinstance(pat_obj, dict):
            if "metavariable_regex" in pat_obj:
                mv_regex = pat_obj["metavariable_regex"]
                if isinstance(mv_regex, dict):
                    regex = mv_regex.get("regex", "")
                else:
                    regex = getattr(mv_regex, "regex", "") if hasattr(mv_regex, "regex") else ""
                if regex_pattern.lower() in regex.lower():
                    return True
        else:
            if hasattr(pat_obj, "metavariable_regex") and pat_obj.metavariable_regex:
                regex = getattr(pat_obj.metavariable_regex, "regex", "")
                if regex_pattern.lower() in regex.lower():
                    return True
    
    return False


def verify_python_path_traversal(rule: SemgrepRule) -> Dict[str, bool]:
    """Verify python-path-traversal enhancements."""
    results = {
        "has_cookies_source": False,
        "has_codecs_sink": False,
    }
    
    results["has_cookies_source"] = check_pattern_in_rule(rule, "source", "request.cookies.get")
    results["has_codecs_sink"] = check_pattern_in_rule(rule, "sink", "codecs.open")
    
    return results


def verify_python_random(rule: SemgrepRule) -> Dict[str, bool]:
    """Verify python_random_rule-random enhancements."""
    results = {
        "has_normalvariate": False,
    }
    
    results["has_normalvariate"] = check_pattern_in_rule(rule, "pattern", "random.normalvariate")
    
    return results


def verify_python_hashlib(rule: SemgrepRule) -> Dict[str, bool]:
    """Verify python_crypto_rule-hashlib-new-insecure-functions enhancements."""
    results = {
        "has_hashlib_new_md5": False,
    }
    
    # Check for hashlib.new('md5') pattern
    results["has_hashlib_new_md5"] = check_pattern_in_rule(rule, "pattern", "hashlib.new") and \
                                      check_pattern_in_rule(rule, "pattern", "md5")
    
    return results


def verify_java_sql_injection(rule: SemgrepRule) -> Dict[str, bool]:
    """Verify java-spring-sql-injection-comprehensive enhancements."""
    results = {
        "has_arraylist_add": False,
        "has_arraylist_get": False,
        "has_list_add": False,
        "has_list_get": False,
        "has_map_put": False,
        "has_map_get": False,
        "has_jdbc_sink": False,
    }
    
    results["has_arraylist_add"] = check_pattern_in_rule(rule, "propagator", "ArrayList.add")
    results["has_arraylist_get"] = check_pattern_in_rule(rule, "propagator", "ArrayList.get")
    results["has_list_add"] = check_pattern_in_rule(rule, "propagator", "List.add")
    results["has_list_get"] = check_pattern_in_rule(rule, "propagator", "List.get")
    results["has_map_put"] = check_pattern_in_rule(rule, "propagator", "Map.put")
    results["has_map_get"] = check_pattern_in_rule(rule, "propagator", "Map.get")
    results["has_jdbc_sink"] = check_pattern_in_rule(rule, "sink", "JDBCtemplate.execute")
    
    return results


def verify_java_crypto_weak_message_digest(rule: SemgrepRule) -> Dict[str, bool]:
    """Verify java_crypto_rule-WeakMessageDigest enhancements."""
    results = {
        "has_cipher_getinstance": False,
        "has_des_regex": False,
    }
    
    results["has_cipher_getinstance"] = check_pattern_in_rule(rule, "pattern", "Cipher.getInstance")
    results["has_des_regex"] = check_regex_in_rule(rule, "DES")
    
    return results


def verify_java_crypto_cipher_des(rule: SemgrepRule) -> Dict[str, bool]:
    """Verify java_crypto_rule-CipherDESInsecure enhancements."""
    results = {
        "has_des_cbc_regex": False,
    }
    
    # Check if regex includes DES/CBC/PKCS5PADDING
    results["has_des_cbc_regex"] = check_regex_in_rule(rule, "CBC") or check_regex_in_rule(rule, "PKCS5PADDING")
    
    return results


def verify_xpath_injection(rule: SemgrepRule) -> Dict[str, bool]:
    """Verify python-xpath-injection rule exists and has correct patterns."""
    results = {
        "exists": True,  # Rule exists if we're checking it
        "has_xpath_sink": False,
        "has_request_sources": False,
    }
    
    results["has_xpath_sink"] = check_pattern_in_rule(rule, "sink", "lxml.etree.XPath")
    results["has_request_sources"] = (
        check_pattern_in_rule(rule, "source", "request.args.get") or
        check_pattern_in_rule(rule, "source", "request.form.get") or
        check_pattern_in_rule(rule, "source", "request.cookies.get")
    )
    
    return results


def verify_insecure_cookie(rule: SemgrepRule) -> Dict[str, bool]:
    """Verify python-flask-insecure-cookie rule exists and has correct patterns."""
    results = {
        "exists": True,  # Rule exists if we're checking it
        "has_set_cookie_pattern": False,
    }
    
    results["has_set_cookie_pattern"] = (
        check_pattern_in_rule(rule, "pattern", "set_cookie") and
        check_pattern_in_rule(rule, "pattern", "secure=False")
    )
    
    return results


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description="Verify that enabled rules satisfy requested enhancements"
    )
    parser.add_argument(
        "--namespace",
        required=True,
        help="Tenant namespace (e.g., 'tenant.namespace')",
    )
    
    args = parser.parse_args()
    
    setup_logging()
    logger.info("Starting rule enhancement verification")
    
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
    
    # Build rule lookup by rule_id
    rule_lookup: Dict[str, List[SemgrepRule]] = {}
    for rule in all_rules:
        if rule.spec and rule.spec.rule and rule.spec.rule.id:
            rule_id = rule.spec.rule.id
            if rule_id not in rule_lookup:
                rule_lookup[rule_id] = []
            rule_lookup[rule_id].append(rule)
    
    # Check enabled status
    enabled_rules: Dict[str, SemgrepRule] = {}
    for rule_id, rules in rule_lookup.items():
        for rule in rules:
            is_enabled = (
                rule.disabled is False and
                (not rule.spec or rule.spec.disabled is False)
            )
            if is_enabled:
                enabled_rules[rule_id] = rule
                break  # Use first enabled rule
    
    logger.info(f"\nFound {len(enabled_rules)} enabled rules")
    
    # Verification results
    verification_results = {}
    
    # Check enhanced rules
    logger.info("\n" + "="*80)
    logger.info("VERIFYING ENHANCED RULES")
    logger.info("="*80)
    
    for rule_id in RULES_TO_ENHANCE:
        enhanced_id = f"{rule_id}-v2"
        logger.info(f"\nChecking {rule_id} -> {enhanced_id}")
        
        enhanced_rule = enabled_rules.get(enhanced_id)
        if not enhanced_rule:
            logger.warning(f"  ✗ Enhanced rule {enhanced_id} not found or not enabled")
            verification_results[rule_id] = {"status": "missing", "details": {}}
            continue
        
        logger.info(f"  ✓ Found enabled enhanced rule: {enhanced_id}")
        
        # Verify based on rule type
        if rule_id == "python-path-traversal":
            results = verify_python_path_traversal(enhanced_rule)
            verification_results[rule_id] = {"status": "found", "details": results}
            logger.info(f"    - request.cookies.get() source: {'✓' if results['has_cookies_source'] else '✗'}")
            logger.info(f"    - codecs.open() sink: {'✓' if results['has_codecs_sink'] else '✗'}")
        
        elif rule_id == "python_random_rule-random":
            results = verify_python_random(enhanced_rule)
            verification_results[rule_id] = {"status": "found", "details": results}
            logger.info(f"    - random.normalvariate() pattern: {'✓' if results['has_normalvariate'] else '✗'}")
        
        elif rule_id == "python_crypto_rule-hashlib-new-insecure-functions":
            results = verify_python_hashlib(enhanced_rule)
            verification_results[rule_id] = {"status": "found", "details": results}
            logger.info(f"    - hashlib.new('md5') pattern: {'✓' if results['has_hashlib_new_md5'] else '✗'}")
        
        elif rule_id == "java-spring-sql-injection-comprehensive":
            results = verify_java_sql_injection(enhanced_rule)
            verification_results[rule_id] = {"status": "found", "details": results}
            logger.info(f"    - ArrayList.add() propagator: {'✓' if results['has_arraylist_add'] else '✗'}")
            logger.info(f"    - ArrayList.get() propagator: {'✓' if results['has_arraylist_get'] else '✗'}")
            logger.info(f"    - List.add() propagator: {'✓' if results['has_list_add'] else '✗'}")
            logger.info(f"    - List.get() propagator: {'✓' if results['has_list_get'] else '✗'}")
            logger.info(f"    - Map.put() propagator: {'✓' if results['has_map_put'] else '✗'}")
            logger.info(f"    - Map.get() propagator: {'✓' if results['has_map_get'] else '✗'}")
            logger.info(f"    - JDBCtemplate.execute() sink: {'✓' if results['has_jdbc_sink'] else '✗'}")
        
        elif rule_id == "java_crypto_rule-WeakMessageDigest":
            results = verify_java_crypto_weak_message_digest(enhanced_rule)
            verification_results[rule_id] = {"status": "found", "details": results}
            logger.info(f"    - Cipher.getInstance() pattern: {'✓' if results['has_cipher_getinstance'] else '✗'}")
            logger.info(f"    - DES regex: {'✓' if results['has_des_regex'] else '✗'}")
        
        elif rule_id == "java_crypto_rule-CipherDESInsecure":
            results = verify_java_crypto_cipher_des(enhanced_rule)
            verification_results[rule_id] = {"status": "found", "details": results}
            logger.info(f"    - DES/CBC/PKCS5PADDING regex: {'✓' if results['has_des_cbc_regex'] else '✗'}")
    
    # Check new rules
    logger.info("\n" + "="*80)
    logger.info("VERIFYING NEW RULES")
    logger.info("="*80)
    
    for rule_id in NEW_RULES:
        logger.info(f"\nChecking {rule_id}")
        
        new_rule = enabled_rules.get(rule_id)
        if not new_rule:
            logger.warning(f"  ✗ New rule {rule_id} not found or not enabled")
            verification_results[rule_id] = {"status": "missing", "details": {}}
            continue
        
        logger.info(f"  ✓ Found enabled new rule: {rule_id}")
        
        if rule_id == "python-xpath-injection":
            results = verify_xpath_injection(new_rule)
            verification_results[rule_id] = {"status": "found", "details": results}
            logger.info(f"    - lxml.etree.XPath() sink: {'✓' if results['has_xpath_sink'] else '✗'}")
            logger.info(f"    - request.* sources: {'✓' if results['has_request_sources'] else '✗'}")
        
        elif rule_id == "python-flask-insecure-cookie":
            results = verify_insecure_cookie(new_rule)
            verification_results[rule_id] = {"status": "found", "details": results}
            logger.info(f"    - set_cookie(secure=False) pattern: {'✓' if results['has_set_cookie_pattern'] else '✗'}")
    
    # Summary
    logger.info("\n" + "="*80)
    logger.info("VERIFICATION SUMMARY")
    logger.info("="*80)
    
    all_passed = True
    for rule_id, result in verification_results.items():
        if result["status"] == "missing":
            logger.error(f"✗ {rule_id}: Rule not found or not enabled")
            all_passed = False
        else:
            details = result["details"]
            if all(details.values()):
                logger.info(f"✓ {rule_id}: All enhancements verified")
            else:
                missing = [k for k, v in details.items() if not v]
                logger.warning(f"⚠ {rule_id}: Missing enhancements: {', '.join(missing)}")
                all_passed = False
    
    if all_passed:
        logger.info("\n✓ All requested enhancements are satisfied!")
        return 0
    else:
        logger.warning("\n⚠ Some enhancements are missing or incomplete")
        return 1


if __name__ == "__main__":
    sys.exit(main())



