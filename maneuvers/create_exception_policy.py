#!/usr/bin/env python3
"""
Create Exception Policy Maneuver

A comprehensive script for creating exception policies to suppress non-actionable findings
using the Endor Labs API client. This script creates Rego-based exception policies that
automatically suppress findings to help teams focus on actionable security issues.

SUPPORTS MULTIPLE MATCHING CRITERIA:
- Custom tags (meta.tags) - manual triage
- System finding tags (spec.finding_tags) - automatic analysis
- Finding categories (e.g., SAST, SECRETS)
- CWE identifiers (e.g., CWE-22 for path traversal)
- File path patterns (e.g., scripts/, tests/)
- Project tags (for global or scoped policies)
- Project UUID (for project-specific policies)

Based on the OpenAPI schema and policy resource structure.

Examples:

# Suppress custom tagged findings (manual triage)
uv run python maneuvers/create_exception_policy.py \
  --namespace "tenant.namespace" \
  --project-uuid "your-project-uuid" \
  --policy-name "False Positive Exceptions" \
  --tag "false-positive"

# Suppress system finding tags (automatic analysis)
uv run python maneuvers/create_exception_policy.py \
  --namespace "tenant.namespace" \
  --project-uuid "your-project-uuid" \
  --policy-name "Unreachable Dependency Exceptions" \
  --finding-tag "FINDING_TAGS_UNREACHABLE_DEPENDENCY"

# Suppress SAST findings in scripts directory for specific CWEs (global scope)
uv run python maneuvers/create_exception_policy.py \
  --namespace "tenant.namespace" \
  --policy-name "Scripts Directory Exception - Path Traversal" \
  --finding-category "FINDING_CATEGORY_SAST" \
  --file-path "scripts/" \
  --cwe "CWE-22" \
  --global-scope

# Suppress multiple CWEs in specific directory with project tags
uv run python maneuvers/create_exception_policy.py \
  --namespace "tenant.namespace" \
  --policy-name "Test Directory Exceptions" \
  --finding-category "FINDING_CATEGORY_SAST" \
  --file-path "tests/" \
  --cwe "CWE-22" --cwe "CWE-78" \
  --project-tag "sdk" \
  --project-tag "python"
"""

import argparse
import json
import logging
import os
import sys
from typing import List, Optional

# Add the src directory to the path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from endorlabs.api_client import APIClient
from endorlabs.resources import policy, project
from endorlabs.resources.policy import (
    CreatePolicyPayload,
    ExceptionReason,
    PolicyMeta,
    PolicySpec,
    PolicyType,
)

# Import common utilities
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
from common.project_lookup import find_project_by_repository_url

# Configure logging to reduce verbosity
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger('endorlabs').setLevel(logging.INFO)

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_exception_policy(
    client: APIClient,
    namespace: str,
    policy_name: str,
    policy_description: str,
    project_uuid: Optional[str] = None,
    project_tags: Optional[List[str]] = None,
    tag: Optional[str] = None,
    finding_tag: Optional[str] = None,
    finding_category: Optional[str] = None,
    cwe_list: Optional[List[str]] = None,
    file_path: Optional[str] = None,
    global_scope: bool = False,
    propagate: bool = False,
    use_templated: bool = True,
) -> Optional[dict]:
    """
    Create an exception policy to suppress findings with various matching criteria.
    
    Args:
        client: Authenticated APIClient instance
        namespace: Target namespace
        policy_name: Name for the exception policy
        policy_description: Description for the exception policy
        project_uuid: Project UUID to target (optional, use with global_scope=False)
        project_tags: List of project tags to target (optional, for global scope)
        tag: Custom tag to suppress (e.g., 'false-positive') - uses meta.tags
        finding_tag: System finding tag to suppress - uses spec.finding_tags
        finding_category: Finding category to match (e.g., 'FINDING_CATEGORY_SAST')
        cwe_list: List of CWE identifiers to suppress (e.g., ['CWE-22'])
        file_path: File path pattern to match (e.g., 'scripts/', 'tests/')
        global_scope: If True, applies to all projects (no project_uuid required)
        propagate: Whether to propagate to child namespaces
        use_templated: If True, use templated pattern (data.resources.Finding[i])
                      If False, use custom pattern (input.resource)
        
    Returns:
        Created policy data or None if creation failed
    """
    try:
        # Determine if we should use templated pattern
        # Templated is recommended for SAST/SECRETS as it evaluates all stored findings
        should_use_templated = use_templated
        
        # Auto-detect templated pattern for SAST/SECRETS if not explicitly set
        if finding_category in ["FINDING_CATEGORY_SAST", "FINDING_CATEGORY_SECRETS"]:
            if not use_templated:
                logger.warning(
                    f"⚠️  WARNING: Using custom pattern for {finding_category}. "
                    "Templated pattern is recommended for SAST/SECRETS findings "
                    "as it evaluates all stored findings, not just new ones. "
                    "Consider using --use-templated (default) for better results."
                )
            should_use_templated = True
        
        # Determine package name based on finding category
        if should_use_templated:
            if finding_category == "FINDING_CATEGORY_SAST":
                package_name = "sast"
            elif finding_category == "FINDING_CATEGORY_SECRETS":
                package_name = "secrets"
            else:
                # Default to sast for templated if category not specified
                package_name = "sast"
                if finding_category:
                    logger.warning(
                        f"⚠️  Finding category {finding_category} not SAST/SECRETS. "
                        "Using 'sast' package for templated policy. "
                        "Consider using --use-custom for other categories."
                    )
        else:
            package_name = "exceptions"
        # Build Rego rule conditions
        conditions = []
        helper_functions = []
        
        # Project matching
        if not global_scope and project_uuid:
            conditions.append(f'finding.spec.project_uuid == "{project_uuid}"')
        elif project_tags:
            # Match projects by tags (requires project lookup in Rego)
            tag_conditions = " OR ".join([
                f'project_tags[_] == "{tag}"' for tag in project_tags
            ])
            conditions.append(f'({tag_conditions})')
        
        # Custom tag matching
        if tag:
            conditions.append(f'finding.meta.tags[_] == "{tag}"')
            tag_type = "custom tag"
            tag_value = tag
        elif finding_tag:
            conditions.append(f'finding.spec.finding_tags[_] == "{finding_tag}"')
            tag_type = "system finding tag"
            tag_value = finding_tag
        else:
            tag_type = "custom criteria"
            tag_value = "custom"
        
        # Finding category matching
        if finding_category:
            conditions.append(
                f'finding.spec.finding_categories[_] == "{finding_category}"'
            )
        
        # File path matching
        if file_path:
            helper_functions.append(f"""# Helper function: check if finding is in target path
file_path_match(finding, path) {{
  contains(finding.spec.finding_metadata.custom.uri, path)
}}

file_path_match(finding, path) {{
  contains(finding.spec.finding_metadata.custom.location, path)
}}

file_path_match(finding, path) {{
  contains(finding.spec.finding_metadata.file_path, path)
}}""")
            conditions.append(f'file_path_match(finding, "{file_path}")')
        
        # CWE matching
        if cwe_list:
            cwe_rules = []
            for cwe in cwe_list:
                cwe_prefix = cwe if cwe.endswith(":") else f"{cwe}:"
                cwe_rules.append(
                    f'cwe_match(finding) {{\n  contains(finding.spec.finding_metadata.custom.cwes[i], "{cwe_prefix}")\n}}'
                )
            helper_functions.append(
                f"# Helper function: check if finding matches any of the specified CWEs\n"
                + "\n\n".join(cwe_rules)
            )
            conditions.append("cwe_match(finding)")
        
        # Build main Rego rule based on pattern type
        if should_use_templated:
            # Templated pattern: uses data.resources.Finding[i] and input parameters
            rego_rule = _build_templated_rego_rule(
                package_name, finding_category, cwe_list, file_path,
                tag, finding_tag, project_uuid, project_tags, global_scope
            )
        else:
            # Custom pattern: uses input.resource
            conditions_str = "\n  ".join(conditions) if conditions else "  true"
            
            rego_rule = f"""package {package_name}

match_finding[result] {{
  finding := input.resource
  {conditions_str}
  result = {{"Endor": {{"Finding": finding.uuid}}}}
}}
"""
            
            # Add helper functions if any
            if helper_functions:
                rego_rule += "\n" + "\n\n".join(helper_functions)

        # Build policy tags
        policy_tags = ["exception", "endor-cockpit"]
        if tag_value:
            policy_tags.append(tag_value)
        if file_path:
            policy_tags.append("file-path")
        if cwe_list:
            policy_tags.append("cwe-based")
        
        # Build project selector
        project_selector = None
        if not global_scope and project_uuid:
            project_selector = [f"$uuid={project_uuid}"]
        elif project_tags:
            project_selector = [f"${tag}" for tag in project_tags]
        
        # Create policy payload
        payload = CreatePolicyPayload(
            meta=PolicyMeta(
                name=policy_name,
                kind="Policy",
                description=policy_description,
                tags=policy_tags,
            ),
            spec=PolicySpec(
                policy_type=PolicyType.EXCEPTION,
                rule=rego_rule,
                query_statements=[f"data.{package_name}.match_finding"],
                project_selector=project_selector,
                resource_kinds=["Finding"],
                disable=False,
                exception={"reason": ExceptionReason.FALSE_POSITIVE},
            ),
            propagate=propagate,
        )

        # Create the policy
        exception_policy = policy.create_policy(client, namespace, payload)

        if exception_policy:
            logger.info(f"Created exception policy: {exception_policy.uuid}")
            result = {
                "uuid": exception_policy.uuid,
                "name": exception_policy.meta.name,
                "namespace": namespace,
                "tag_type": tag_type,
                "tag_value": tag_value,
            }
            if project_uuid:
                result["project_uuid"] = project_uuid
            if project_tags:
                result["project_tags"] = project_tags
            if file_path:
                result["file_path"] = file_path
            if cwe_list:
                result["cwe_list"] = cwe_list
            if finding_category:
                result["finding_category"] = finding_category
            result["global_scope"] = global_scope
            result["pattern"] = "templated" if should_use_templated else "custom"
            result["package"] = package_name
            return result
        else:
            logger.error("Failed to create exception policy")
            return None

    except Exception as e:
        logger.error(f"Error creating exception policy: {e}")
        
        # Log detailed error information
        if hasattr(e, "response"):
            try:
                error_details = (
                    e.response.json()
                    if hasattr(e.response, "json")
                    else str(e.response.text)
                )
                logger.error(f"API Error Details: {error_details}")
            except Exception:
                logger.error(
                    f"API Error Response: {
                        e.response.text
                        if hasattr(e.response, 'text')
                        else 'No response text'
                    }"
                )
        
        return None


def _build_templated_rego_rule(
    package_name: str,
    finding_category: Optional[str],
    cwe_list: Optional[List[str]],
    file_path: Optional[str],
    tag: Optional[str],
    finding_tag: Optional[str],
    project_uuid: Optional[str],
    project_tags: Optional[List[str]],
    global_scope: bool,
) -> str:
    """
    Build templated exception policy Rego rule.
    
    Templated policies use data.resources.Finding[i] to iterate over all stored findings.
    This version hardcodes matching criteria for immediate functionality.
    """
    # Base templated rule structure
    helper_functions = [
        """contains_any_substring(s, substrings) {
    some i
    contains(lower(s), lower(substrings[i]))
}

list_contains(list, elem) {
    list[_] == elem
}

match_path(finding, paths) {
    some i, j
    glob.match(paths[j], ["/"], finding.spec.dependency_file_paths[i])
}"""
    ]
    
    # Build matching conditions (hardcoded, not using input parameters)
    match_conditions = []
    
    # Meta tags matching
    if tag:
        match_conditions.append(f'finding.meta.tags[_] == "{tag}"')
    
    # Finding tags matching
    if finding_tag:
        match_conditions.append(f'finding.spec.finding_tags[_] == "{finding_tag}"')
    
    # CWE matching
    if cwe_list:
        cwe_match_rules = []
        for cwe in cwe_list:
            cwe_prefix = cwe if cwe.endswith(":") else f"{cwe}:"
            cwe_match_rules.append(
                f'cwe_match(finding) {{\n  cwe := lower("{cwe_prefix}")\n  finding_cwe := lower(finding.spec.finding_metadata.custom.cwes[_])\n  startswith(finding_cwe, cwe)\n}}'
            )
        helper_functions.append(
            "# Helper function: check if finding matches any of the specified CWEs\n"
            + "\n\n".join(cwe_match_rules)
        )
        match_conditions.append("cwe_match(finding)")
    
    # File path matching
    if file_path:
        helper_functions.append(f"""# Helper function: check if finding is in target path
file_path_match(finding, path) {{
  contains(finding.spec.finding_metadata.custom.uri, path)
}}

file_path_match(finding, path) {{
  contains(finding.spec.finding_metadata.custom.location, path)
}}

file_path_match(finding, path) {{
  contains(finding.spec.finding_metadata.file_path, path)
}}

file_path_match(finding, path) {{
  some i
  glob.match(path, ["/"], finding.spec.dependency_file_paths[i])
}}""")
        match_conditions.append(f'file_path_match(finding, "{file_path}")')
    
    # Build main rule
    rule_conditions = [
        "some i",
        "finding := data.resources.Finding[i]",
    ]
    
    # Finding category check
    if finding_category:
        rule_conditions.append(
            f'finding.spec.finding_categories[_] == "{finding_category}"'
        )
    
    # Add hardcoded matching conditions
    rule_conditions.extend(match_conditions)
    
    # Project matching (if not global scope)
    if not global_scope and project_uuid:
        rule_conditions.append(f'finding.spec.project_uuid == "{project_uuid}"')
    
    conditions_str = "\n        ".join(rule_conditions)
    
    rego_rule = f"""package {package_name}
{chr(10).join(helper_functions)}

match_finding[result] {{
        {conditions_str}
        result = {{
                "Endor" : {{
                        "Finding" : finding.uuid
                }}
        }}
}}"""
    
    return rego_rule


def main():
    """Main function to create exception policy with command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Create exception policy to suppress tagged findings using Endor Labs API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Suppress false-positive tagged findings (manual triage)
  python maneuvers/create_exception_policy.py \\
    --namespace "tenant.namespace" \\
    --project-uuid "your-project-uuid" \\
    --policy-name "False Positive Exceptions" \\
    --tag "false-positive"

  # Suppress custom tagged findings (manual triage)
  python maneuvers/create_exception_policy.py \\
    --namespace "tenant.namespace" \\
    --project-uuid "your-project-uuid" \\
    --policy-name "False Positive Exceptions" \\
    --tag "false-positive" \\
    --description "Suppresses findings manually tagged as false-positive during triage"

  # Suppress system finding tags (automatic analysis)
  python maneuvers/create_exception_policy.py \\
    --namespace "tenant.namespace" \\
    --project-uuid "your-project-uuid" \\
    --policy-name "Unreachable Dependency Exceptions" \\
    --finding-tag "FINDING_TAGS_UNREACHABLE_DEPENDENCY" \\
    --description "Suppresses findings for unreachable dependencies to focus on actionable security issues"

  # Suppress invalid secrets (system-determined)
  python maneuvers/create_exception_policy.py \\
    --namespace "tenant.namespace" \\
    --project-uuid "your-project-uuid" \\
    --policy-name "Invalid Secret Exceptions" \\
    --finding-tag "FINDING_TAGS_INVALID_SECRET"

  # Suppress SAST findings in scripts directory for specific CWEs (global scope)
  python maneuvers/create_exception_policy.py \\
    --namespace "tenant.namespace" \\
    --policy-name "Scripts Directory Exception - Path Traversal" \\
    --finding-category "FINDING_CATEGORY_SAST" \\
    --file-path "scripts/" \\
    --cwe "CWE-22" \\
    --global-scope

  # Suppress multiple CWEs in test directory with project tags
  python maneuvers/create_exception_policy.py \\
    --namespace "tenant.namespace" \\
    --policy-name "Test Directory Exceptions" \\
    --finding-category "FINDING_CATEGORY_SAST" \\
    --file-path "tests/" \\
    --cwe "CWE-22" --cwe "CWE-78" \\
    --project-tag "sdk" \\
    --project-tag "python" \\
    --global-scope

  # Create exception policy with repository URL lookup
  python maneuvers/create_exception_policy.py \\
    --namespace "tenant.namespace" \\
    --repository-url "https://github.com/Endor-Solutions-Architecture/endor-cockpit" \\
    --policy-name "False Positive Exceptions" \\
    --tag "false-positive" \\
    --propagate
        """
    )

    # Required arguments
    parser.add_argument(
        "--namespace",
        required=True,
        help="Target namespace where the policy will be created"
    )
    parser.add_argument(
        "--policy-name",
        required=True,
        help="Name for the exception policy"
    )
    # Matching criteria (at least one required)
    match_group = parser.add_argument_group(
        "Matching Criteria",
        "Specify criteria to match findings (at least one required)"
    )
    match_group.add_argument(
        "--tag",
        help="Custom tag to suppress (e.g., 'false-positive', 'test-data') - uses meta.tags"
    )
    match_group.add_argument(
        "--finding-tag",
        help="System finding tag to suppress (e.g., 'FINDING_TAGS_UNREACHABLE_DEPENDENCY') - uses spec.finding_tags"
    )
    match_group.add_argument(
        "--finding-category",
        help="Finding category to match (e.g., 'FINDING_CATEGORY_SAST', 'FINDING_CATEGORY_SECRETS')"
    )
    match_group.add_argument(
        "--cwe",
        action="append",
        help="CWE identifier to suppress (e.g., 'CWE-22'). Can be specified multiple times."
    )
    match_group.add_argument(
        "--file-path",
        help="File path pattern to match (e.g., 'scripts/', 'tests/', '**/vendor/**')"
    )

    # Project identification (optional - can use global scope)
    project_group = parser.add_argument_group(
        "Project Scope",
        "Specify project scope (optional - use --global-scope for namespace-wide policy)"
    )
    project_group.add_argument(
        "--project-uuid",
        help="Project UUID to target with the exception policy"
    )
    project_group.add_argument(
        "--repository-url",
        help="Repository URL to find project and target with the exception policy"
    )
    project_group.add_argument(
        "--project-tag",
        action="append",
        help="Project tag to target (e.g., 'sdk', 'python'). Can be specified multiple times. Use with --global-scope."
    )
    project_group.add_argument(
        "--global-scope",
        action="store_true",
        help="Apply policy globally to all projects in namespace (no project_uuid required)"
    )

    # Optional arguments
    parser.add_argument(
        "--description",
        help="Description for the exception policy (defaults to auto-generated description)"
    )
    parser.add_argument(
        "--propagate",
        action="store_true",
        help="Enable propagation to child namespaces"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show the policy payload that would be created without creating it"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    parser.add_argument(
        "--use-templated",
        action="store_true",
        default=True,
        help="Use templated exception policy pattern (default: True for SAST/SECRETS). "
             "Templated policies evaluate all stored findings, not just new ones."
    )
    parser.add_argument(
        "--use-custom",
        action="store_true",
        help="Use custom exception policy pattern (input.resource). "
             "Not recommended for SAST/SECRETS findings."
    )

    args = parser.parse_args()

    # Set logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Validate arguments
    if not args.global_scope and not args.project_uuid and not args.repository_url:
        parser.error(
            "Must specify either --global-scope, --project-uuid, or --repository-url"
        )
    
    if not args.tag and not args.finding_tag and not args.finding_category and not args.cwe and not args.file_path:
        parser.error(
            "At least one matching criterion must be specified: "
            "--tag, --finding-tag, --finding-category, --cwe, or --file-path"
        )
    
    if args.tag and args.finding_tag:
        parser.error("Cannot specify both --tag and --finding-tag. Choose one.")
    
    if args.project_uuid and args.global_scope:
        parser.error("Cannot specify both --project-uuid and --global-scope.")
    
    # Determine pattern type
    use_templated = args.use_templated and not args.use_custom
    
    # Guardrails: Warn about pattern choice
    if args.finding_category in ["FINDING_CATEGORY_SAST", "FINDING_CATEGORY_SECRETS"]:
        if args.use_custom:
            logger.warning(
                "⚠️  WARNING: Using custom pattern for SAST/SECRETS findings. "
                "Templated pattern is strongly recommended as it evaluates all stored findings. "
                "Custom pattern only evaluates findings as they're processed."
            )
        else:
            logger.info(
                "✅ Using templated pattern for SAST/SECRETS findings. "
                "This will evaluate all stored findings, not just new ones."
            )

    try:
        # Initialize API client
        logger.info("Initializing API client...")
        client = APIClient()

        # Determine project UUID
        project_uuid = args.project_uuid
        if not project_uuid and args.repository_url and not args.global_scope:
            logger.info(f"Finding project for repository: {args.repository_url}")
            project_uuid = find_project_by_repository_url(
                client, args.namespace, args.repository_url
            )
            if not project_uuid:
                logger.error(
                    f"Could not find project for repository: {args.repository_url}"
                )
                sys.exit(1)

        # Generate description if not provided
        description = args.description
        if not description:
            parts = []
            if args.tag:
                parts.append(f"custom tag '{args.tag}'")
            if args.finding_tag:
                parts.append(f"system finding tag '{args.finding_tag}'")
            if args.finding_category:
                parts.append(f"category '{args.finding_category}'")
            if args.cwe:
                parts.append(f"CWEs {', '.join(args.cwe)}")
            if args.file_path:
                parts.append(f"file path '{args.file_path}'")
            
            scope_desc = (
                "globally" if args.global_scope
                else f"for project {project_uuid}"
                if project_uuid
                else "for matching projects"
            )
            
            description = (
                f"Suppresses findings with {', '.join(parts)} {scope_desc}"
            )

        # Build Rego rule for preview (simplified version)
        # Full rule will be built in create_exception_policy function
        rego_rule = "package exceptions\n\nmatch_finding[result] { ... }"

        # Build preview Rego rule for dry-run
        if args.dry_run:
            # Reconstruct rule for preview
            conditions = []
            helper_functions = []
            
            if not args.global_scope and project_uuid:
                conditions.append(f'finding.spec.project_uuid == "{project_uuid}"')
            elif args.project_tag:
                tag_conditions = " OR ".join([
                    f'project_tags[_] == "{tag}"' for tag in args.project_tag
                ])
                conditions.append(f'({tag_conditions})')
            
            if args.tag:
                conditions.append(f'finding.meta.tags[_] == "{args.tag}"')
            elif args.finding_tag:
                conditions.append(f'finding.spec.finding_tags[_] == "{args.finding_tag}"')
            
            if args.finding_category:
                conditions.append(
                    f'finding.spec.finding_categories[_] == "{args.finding_category}"'
                )
            
            if args.file_path:
                helper_functions.append(f"""file_path_match(finding, path) {{
  contains(finding.spec.finding_metadata.custom.uri, path)
}}

file_path_match(finding, path) {{
  contains(finding.spec.finding_metadata.custom.location, path)
}}

file_path_match(finding, path) {{
  contains(finding.spec.finding_metadata.file_path, path)
}}""")
                conditions.append(f'file_path_match(finding, "{args.file_path}")')
            
            if args.cwe:
                cwe_rules = []
                for cwe in args.cwe:
                    cwe_prefix = cwe if cwe.endswith(":") else f"{cwe}:"
                    cwe_rules.append(
                        f'cwe_match(finding) {{\n  contains(finding.spec.finding_metadata.custom.cwes[i], "{cwe_prefix}")\n}}'
                    )
                helper_functions.append("\n\n".join(cwe_rules))
                conditions.append("cwe_match(finding)")
            
            conditions_str = "\n  ".join(conditions) if conditions else "  true"
            rego_rule = f"""package exceptions

match_finding[result] {{
  finding := input.resource
  {conditions_str}
  result = {{"Endor": {{"Finding": finding.uuid}}}}
}}
"""
            if helper_functions:
                rego_rule += "\n" + "\n\n".join(helper_functions)
            
            print("=== DRY RUN - Exception Policy Payload ===")
            print(f"Policy Name: {args.policy_name}")
            print(f"Description: {description}")
            if project_uuid:
                print(f"Target Project UUID: {project_uuid}")
            if args.project_tag:
                print(f"Target Project Tags: {', '.join(args.project_tag)}")
            if args.global_scope:
                print("Scope: Global (all projects)")
            print(f"Finding Category: {args.finding_category or 'Any'}")
            print(f"File Path Pattern: {args.file_path or 'Any'}")
            print(f"CWEs: {', '.join(args.cwe) if args.cwe else 'Any'}")
            print(f"Custom Tag: {args.tag or 'None'}")
            print(f"Finding Tag: {args.finding_tag or 'None'}")
            print(f"Propagate: {args.propagate}")
            print("\nRego Rule:")
            print(rego_rule)
            package = "sast" if args.finding_category == "FINDING_CATEGORY_SAST" else (
                "secrets" if args.finding_category == "FINDING_CATEGORY_SECRETS" else "exceptions"
            )
            if use_templated and args.finding_category in ["FINDING_CATEGORY_SAST", "FINDING_CATEGORY_SECRETS"]:
                print(f"\nQuery Statement: data.{package}.match_finding")
                print("\n⚠️  NOTE: This is a templated policy. Input parameters (CWE, FilePath, etc.)")
                print("   are configured via the UI. The policy will evaluate all stored findings.")
            else:
                print("\nQuery Statement: data.exceptions.match_finding")
            return

        # Create the exception policy
        logger.info("Creating exception policy...")
        result = create_exception_policy(
            client=client,
            namespace=args.namespace,
            policy_name=args.policy_name,
            policy_description=description,
            project_uuid=project_uuid if not args.global_scope else None,
            project_tags=args.project_tag,
            tag=args.tag,
            finding_tag=args.finding_tag,
            finding_category=args.finding_category,
            cwe_list=args.cwe,
            file_path=args.file_path,
            global_scope=args.global_scope,
            propagate=args.propagate,
            use_templated=use_templated,
        )

        if result:
            print("=== Exception Policy Created Successfully ===")
            print(f"UUID: {result['uuid']}")
            print(f"Name: {result['name']}")
            print(f"Namespace: {result['namespace']}")
            if 'project_uuid' in result:
                print(f"Target Project: {result['project_uuid']}")
            if 'project_tags' in result:
                print(f"Target Project Tags: {', '.join(result['project_tags'])}")
            print(f"Scope: {'Global' if result.get('global_scope') else 'Project-specific'}")
            print(f"Tag Type: {result['tag_type']}")
            print(f"Tag Value: {result['tag_value']}")
            if 'finding_category' in result:
                print(f"Finding Category: {result['finding_category']}")
            if 'file_path' in result:
                print(f"File Path Pattern: {result['file_path']}")
            if 'cwe_list' in result:
                print(f"CWEs: {', '.join(result['cwe_list'])}")
            if 'pattern' in result:
                print(f"Pattern: {result['pattern']} ({result.get('package', 'unknown')} package)")
            print(f"Propagate: {args.propagate}")
        else:
            print("Failed to create exception policy")
            sys.exit(1)

    except KeyboardInterrupt:
        logger.info("Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()

