#!/usr/bin/env python3
"""
Create Notification Policy Maneuver

A repeatable script for creating notification policies using the Endor Labs API client.
This script creates notification policies that trigger actions (JIRA tickets, Slack messages, etc.)
when specific findings are detected based on configurable criteria.

Supported Finding Categories:
- VULNERABILITY: Vulnerability findings
- SECRETS: Exposed secrets (passwords, tokens, keys)
- SAST: Static Application Security Testing findings
- SCA: Software Composition Analysis findings
- MALWARE: Malware findings
- LICENSE_RISK: License risk findings
- SUPPLY_CHAIN: Supply chain issues
- OPERATIONAL: Operational issues
- SECURITY: General security issues
- CICD: CI/CD pipeline issues
- GHACTIONS: GitHub Actions findings
- CONTAINER: Container findings
- AI_MODELS: AI model findings
- TOOLS: Tool-related findings
- SCPM: Repository security posture management

Based on the OpenAPI schema and notification policy structure.

Example:

# Vulnerability notification policy with Endor Patch
uv run python maneuvers/create_notification_policy.py \
  --namespace "tenant.namespace" \
  --name "Vulnerability Notifications with Endor Patch" \
  --description "Notification policy for reachable dependency vulnerabilities with Endor Patch available" \
  --finding-categories "VULNERABILITY" \
  --severity "MEDIUM" \
  --notification-target-uuid "68fb086e4f911525a05e387e" \
  --propagate \
  --dry-run

# SAST notification policy
uv run python maneuvers/create_notification_policy.py \
  --namespace "tenant.namespace" \
  --name "SAST Notifications" \
  --description "Notification policy for SAST findings" \
  --finding-categories "SAST" \
  --severity "HIGH" \
  --notification-target-uuid "your-target-uuid" \
  --propagate \
  --dry-run

## Note: This maneuver creates notification policies that reference notification targets.
## The policy defines which findings trigger notifications and the target defines the action.
"""

import argparse
import json
import logging
import os
import sys
from typing import Any, Dict, List, Optional

# Add the src directory to the path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from endorlabs.api_client import APIClient

# Configure logging to reduce verbosity
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger('endorlabs').setLevel(logging.INFO)

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_notification_policy(
    client: APIClient,
    namespace: str,
    name: str,
    description: str,
    finding_categories: List[str],
    notification_target_uuid: str,
    propagate: bool = False,
    severity: Optional[str] = None,
    finding_tags: Optional[List[str]] = None,
    project_selector: Optional[List[str]] = None,
    project_exceptions: Optional[List[str]] = None,
    aggregation_type: str = "AGGREGATION_TYPE_PROJECT",
    bypass_exceptions: bool = False,
    tags: Optional[List[str]] = None
) -> Optional[Dict[str, Any]]:
    """
    Create a notification policy using the API client.
    
    Args:
        client: Authenticated APIClient instance
        namespace: Target namespace
        name: Policy name
        description: Policy description
        finding_categories: List of finding categories to target
        notification_target_uuid: UUID of the notification target to use
        propagate: Whether to propagate to child namespaces
        severity: Optional severity level filter
        finding_tags: Optional system finding tags to filter by
        project_selector: Optional project selector tags
        project_exceptions: Optional project exception tags
        aggregation_type: How to aggregate notifications
        bypass_exceptions: Whether to bypass exception policies
        tags: Optional tags for the policy
        
    Returns:
        Created policy data or None if creation failed
    """
    try:
        # Generate Rego rule for the specified finding categories
        rego_rule = generate_rego_rule(finding_categories, severity, finding_tags)
        
        # Build the complete payload
        payload = {
            "meta": {
                "name": name,
                "description": description,
                "kind": "Policy",
                "version": "v1",
                "tags": tags or []
            },
            "spec": {
                "policy_type": "POLICY_TYPE_NOTIFICATION",
                "rule": rego_rule,
                "query_statements": [generate_query_statement(finding_categories)],
                "resource_kinds": ["Finding"],
                "disable": False,
                "project_selector": project_selector,
                "project_exceptions": project_exceptions,
                "finding_level": severity,
                "notification": {
                    "notification_target_uuids": [notification_target_uuid],
                    "aggregation_type": aggregation_type,
                    "bypass_exceptions": bypass_exceptions
                }
            },
            "propagate": propagate
        }
        
        logger.info(f"Creating notification policy: {name}")
        logger.debug(f"Payload: {json.dumps(payload, indent=2)}")
        
        # Make the API call
        res = client.post(
            f"v1/namespaces/{namespace}/policies",
            json=payload,
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
        )
        
        if res.status_code == 200:
            data = res.json()
            logger.info(f"Successfully created notification policy: {data.get('uuid', 'unknown')}")
            return data
        else:
            logger.error(f"Failed to create notification policy: {res.status_code} - {res.text}")
            return None
            
    except Exception as e:
        logger.error(f"Error creating notification policy: {e}", exc_info=True)
        return None


def generate_rego_rule(finding_categories: List[str], severity: Optional[str] = None, finding_tags: Optional[List[str]] = None) -> str:
    """Generate Rego rule for the specified finding categories and filters."""
    if not finding_categories:
        raise ValueError("At least one finding category must be specified")
    
    # Create the package name based on the first category
    first_category = finding_categories[0].replace('FINDING_CATEGORY_', '').lower()
    package_name = f"{first_category}_notification"
    
    # Generate the match conditions for each category
    category_conditions = []
    for category in finding_categories:
        category_conditions.append(f'    data.resources.Finding[i].spec.finding_categories[_] == "{category}"')
    
    # Join conditions with OR logic
    category_match = " or\n".join(category_conditions)
    
    # Add severity filter if specified
    severity_condition = ""
    if severity:
        severity_condition = f'    data.resources.Finding[i].spec.level == "FINDING_LEVEL_{severity}"\n'
    
    # Add finding tags filter if specified
    finding_tags_condition = ""
    if finding_tags:
        tag_conditions = []
        for tag in finding_tags:
            tag_conditions.append(f'    data.resources.Finding[i].spec.finding_tags[_] == "{tag}"')
        finding_tags_condition = " or\n".join(tag_conditions) + "\n"
    
    # Generate the complete rule
    rule = f"""package {package_name}

match_baseline(finding) {{
    some i
    data.baseline.Finding[i].spec.extra_key == finding.spec.extra_key
    count(data.baseline.Finding[i].spec.finding_metadata.source_policy_info.results) == count(finding.spec.finding_metadata.source_policy_info.results)
}}

match_findings[result] {{
    some i
    ({category_match})
    not match_baseline(data.resources.Finding[i])
{severity_condition}{finding_tags_condition}    result = {{
        "Endor": {{
            "Finding": data.resources.Finding[i].uuid
        }}
    }}
}}"""
    
    return rule


def generate_query_statement(finding_categories: List[str]) -> str:
    """Generate query statement for the specified finding categories."""
    if not finding_categories:
        raise ValueError("At least one finding category must be specified")
    
    # Create the package name based on the first category
    first_category = finding_categories[0].replace('FINDING_CATEGORY_', '').lower()
    package_name = f"{first_category}_notification"
    
    return f"data.{package_name}.match_findings"


def get_notification_policy(
    client: APIClient,
    namespace: str,
    policy_uuid: str
) -> Optional[Dict[str, Any]]:
    """
    Retrieve a notification policy by UUID.
    
    Args:
        client: Authenticated APIClient instance
        namespace: Target namespace
        policy_uuid: UUID of the notification policy
        
    Returns:
        Policy data or None if retrieval failed
    """
    try:
        logger.info(f"Retrieving notification policy: {policy_uuid}")
        
        res = client.get(
            f"v1/namespaces/{namespace}/policies/{policy_uuid}"
        )
        
        if res.status_code == 200:
            data = res.json()
            logger.info(f"Successfully retrieved notification policy: {policy_uuid}")
            return data
        else:
            logger.error(f"Failed to retrieve notification policy: {res.status_code} - {res.text}")
            return None
            
    except Exception as e:
        logger.error(f"Error retrieving notification policy: {e}", exc_info=True)
        return None


def format_notification_policy_for_display(policy_data: Dict[str, Any]) -> str:
    """
    Format notification policy data for human-readable display.
    
    Args:
        policy_data: Notification policy data from API
        
    Returns:
        Formatted string for display
    """
    if not policy_data:
        return "No policy data available"
    
    meta = policy_data.get('meta', {})
    spec = policy_data.get('spec', {})
    tenant_meta = policy_data.get('tenant_meta', {})
    notification_config = spec.get('notification', {})
    
    output = []
    output.append("=" * 80)
    output.append("NOTIFICATION POLICY DETAILS")
    output.append("=" * 80)
    
    # Basic Information
    output.append(f"UUID: {policy_data.get('uuid', 'N/A')}")
    output.append(f"Name: {meta.get('name', 'N/A')}")
    output.append(f"Description: {meta.get('description', 'N/A')}")
    output.append(f"Kind: {meta.get('kind', 'N/A')}")
    output.append(f"Version: {meta.get('version', 'N/A')}")
    output.append(f"Namespace: {tenant_meta.get('namespace', 'N/A')}")
    output.append(f"Propagate: {policy_data.get('propagate', 'N/A')}")
    output.append("")
    
    # Timestamps
    output.append("TIMESTAMPS:")
    output.append("-" * 40)
    output.append(f"Created: {meta.get('create_time', 'N/A')}")
    output.append(f"Created By: {meta.get('created_by', 'N/A')}")
    output.append(f"Updated: {meta.get('update_time', 'N/A')}")
    output.append(f"Updated By: {meta.get('updated_by', 'N/A')}")
    output.append("")
    
    # Policy Configuration
    output.append("POLICY CONFIGURATION:")
    output.append("-" * 40)
    output.append(f"Policy Type: {spec.get('policy_type', 'N/A')}")
    output.append(f"Disabled: {spec.get('disable', 'N/A')}")
    output.append(f"Finding Level: {spec.get('finding_level', 'N/A')}")
    output.append("")
    
    # Project Configuration
    if spec.get('project_selector'):
        output.append("PROJECT SELECTOR TAGS:")
        output.append("-" * 40)
        for tag in spec.get('project_selector', []):
            output.append(f"  • {tag}")
        output.append("")
    
    if spec.get('project_exceptions'):
        output.append("PROJECT EXCEPTION TAGS:")
        output.append("-" * 40)
        for tag in spec.get('project_exceptions', []):
            output.append(f"  • {tag}")
        output.append("")
    
    # Notification Configuration
    if notification_config:
        output.append("NOTIFICATION CONFIGURATION:")
        output.append("-" * 40)
        output.append(f"Target UUIDs: {', '.join(notification_config.get('notification_target_uuids', []))}")
        output.append(f"Aggregation Type: {notification_config.get('aggregation_type', 'N/A')}")
        output.append(f"Bypass Exceptions: {notification_config.get('bypass_exceptions', 'N/A')}")
        output.append("")
    
    # Query Statements
    if spec.get('query_statements'):
        output.append("QUERY STATEMENTS:")
        output.append("-" * 40)
        for query in spec.get('query_statements', []):
            output.append(f"  • {query}")
        output.append("")
    
    # Tags
    if meta.get('tags'):
        output.append("TAGS:")
        output.append("-" * 40)
        for tag in meta.get('tags', []):
            output.append(f"  • {tag}")
        output.append("")
    
    output.append("=" * 80)
    
    return "\n".join(output)


def parse_tags(tags_str: str) -> List[str]:
    """Parse comma-separated tags string into list."""
    return [tag.strip() for tag in tags_str.split(',') if tag.strip()]


def parse_finding_categories(categories_str: str) -> List[str]:
    """Parse comma-separated finding categories string into list."""
    if not categories_str:
        return []
    
    # Map user-friendly names to API constants
    category_mapping = {
        'VULNERABILITY': 'FINDING_CATEGORY_VULNERABILITY',
        'SECRETS': 'FINDING_CATEGORY_SECRETS',
        'SAST': 'FINDING_CATEGORY_SAST',
        'SCA': 'FINDING_CATEGORY_SCA',
        'MALWARE': 'FINDING_CATEGORY_MALWARE',
        'LICENSE_RISK': 'FINDING_CATEGORY_LICENSE_RISK',
        'SUPPLY_CHAIN': 'FINDING_CATEGORY_SUPPLY_CHAIN',
        'OPERATIONAL': 'FINDING_CATEGORY_OPERATIONAL',
        'SECURITY': 'FINDING_CATEGORY_SECURITY',
        'CICD': 'FINDING_CATEGORY_CICD',
        'GHACTIONS': 'FINDING_CATEGORY_GHACTIONS',
        'CONTAINER': 'FINDING_CATEGORY_CONTAINER',
        'AI_MODELS': 'FINDING_CATEGORY_AI_MODELS',
        'TOOLS': 'FINDING_CATEGORY_TOOLS',
        'SCPM': 'FINDING_CATEGORY_SCPM'
    }
    
    categories = []
    for category in categories_str.split(','):
        category = category.strip().upper()
        if category in category_mapping:
            categories.append(category_mapping[category])
        else:
            # If it's already in API format, use as-is
            if category.startswith('FINDING_CATEGORY_'):
                categories.append(category)
            else:
                raise ValueError(f"Unknown finding category: {category}. "
                               f"Available categories: {', '.join(category_mapping.keys())}")
    
    return categories


def parse_finding_tags(tags_str: str) -> List[str]:
    """Parse comma-separated finding tags string into list."""
    return [tag.strip() for tag in tags_str.split(',') if tag.strip()]


def main():
    """Main function to create notification policy with command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Create notification policy using Endor Labs API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Vulnerability notification policy with Endor Patch
  python maneuvers/create_notification_policy.py \\
    --namespace "tenant.namespace" \\
    --name "Vulnerability Notifications with Endor Patch" \\
    --description "Notification policy for reachable dependency vulnerabilities with Endor Patch available" \\
    --finding-categories "VULNERABILITY" \\
    --severity "MEDIUM" \\
    --notification-target-uuid "68fb086e4f911525a05e387e" \\
    --propagate

  # SAST notification policy
  python maneuvers/create_notification_policy.py \\
    --namespace "tenant.namespace" \\
    --name "SAST Notifications" \\
    --description "Notification policy for SAST findings" \\
    --finding-categories "SAST" \\
    --severity "HIGH" \\
    --notification-target-uuid "your-target-uuid" \\
    --propagate

  # Multiple finding categories
  python maneuvers/create_notification_policy.py \\
    --namespace "tenant.namespace" \\
    --name "Security Notifications" \\
    --description "Notification policy for security findings" \\
    --finding-categories "VULNERABILITY,SECRETS,SAST" \\
    --severity "MEDIUM" \\
    --notification-target-uuid "your-target-uuid" \\
    --propagate

  # With system finding tags filter
  python maneuvers/create_notification_policy.py \\
    --namespace "tenant.namespace" \\
    --name "Reachable Dependency Notifications" \\
    --description "Notification policy for reachable dependencies" \\
    --finding-categories "VULNERABILITY" \\
    --finding-tags "FINDING_TAGS_REACHABLE_DEPENDENCY" \\
    --notification-target-uuid "your-target-uuid" \\
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
        "--name",
        required=True,
        help="Name for the notification policy"
    )
    parser.add_argument(
        "--description",
        required=True,
        help="Description for the notification policy"
    )
    parser.add_argument(
        "--finding-categories",
        required=True,
        help="Finding categories - comma-separated list of finding categories to target. "
             "Available categories: VULNERABILITY, SECRETS, SAST, SCA, MALWARE, LICENSE_RISK, "
             "SUPPLY_CHAIN, OPERATIONAL, SECURITY, CICD, GHACTIONS, CONTAINER, AI_MODELS, TOOLS, SCPM. "
             "Examples: 'VULNERABILITY', 'SECRETS', 'VULNERABILITY,SECRETS,SAST'"
    )
    parser.add_argument(
        "--notification-target-uuid",
        required=True,
        help="UUID of the notification target to use for this policy"
    )
    
    # Optional arguments
    parser.add_argument(
        "--severity",
        choices=["LOW", "MEDIUM", "HIGH", "CRITICAL"],
        help="Severity level - only match findings with this severity level"
    )
    parser.add_argument(
        "--finding-tags",
        help="System finding tags - comma-separated list of system finding tags to filter by. "
             "Examples: 'FINDING_TAGS_REACHABLE_DEPENDENCY', 'FINDING_TAGS_VALID_SECRET'"
    )
    parser.add_argument(
        "--project-selector",
        help="Project selector tags - comma-separated list of tags that projects must have to be affected"
    )
    parser.add_argument(
        "--project-exceptions",
        help="Project exception tags - comma-separated list of tags for projects to exclude"
    )
    parser.add_argument(
        "--aggregation-type",
        default="AGGREGATION_TYPE_PROJECT",
        choices=["AGGREGATION_TYPE_PROJECT", "AGGREGATION_TYPE_DEPENDENCY", "AGGREGATION_TYPE_FINDING"],
        help="How to aggregate notifications (default: AGGREGATION_TYPE_PROJECT)"
    )
    parser.add_argument(
        "--bypass-exceptions",
        action="store_true",
        help="Bypass exception policies when sending notifications"
    )
    parser.add_argument(
        "--tags",
        help="Policy tags - comma-separated list of tags for categorization"
    )
    parser.add_argument(
        "--propagate",
        action="store_true",
        help="Propagate to child namespaces"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show the payload that would be created without creating it"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force creation even if policy already exists (will create with unique name)"
    )
    
    args = parser.parse_args()
    
    # Set logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    try:
        # Initialize API client
        logger.info("Initializing API client...")
        client = APIClient()
        
        # Parse arguments
        tags = parse_tags(args.tags) if args.tags else None
        finding_categories = parse_finding_categories(args.finding_categories)
        finding_tags = parse_finding_tags(args.finding_tags) if args.finding_tags else None
        project_selector = parse_tags(args.project_selector) if args.project_selector else None
        project_exceptions = parse_tags(args.project_exceptions) if args.project_exceptions else None
        
        # Handle force mode - generate unique name if needed
        policy_name = args.name
        if args.force:
            import time
            timestamp = int(time.time())
            policy_name = f"{args.name}-{timestamp}"
        
        if args.dry_run:
            print("=== DRY RUN - Notification Policy Payload ===")
            print(f"Policy Name: {policy_name}")
            print(f"Description: {args.description}")
            print(f"Finding Categories: {finding_categories}")
            print(f"Notification Target UUID: {args.notification_target_uuid}")
            print(f"Severity: {args.severity}")
            print(f"Finding Tags: {finding_tags}")
            print(f"Propagate: {args.propagate}")
            print("\nRego Rule:")
            print(generate_rego_rule(finding_categories, args.severity, finding_tags))
            return
        
        # Create the notification policy
        logger.info("Creating notification policy...")
        result = create_notification_policy(
            client=client,
            namespace=args.namespace,
            name=policy_name,
            description=args.description,
            finding_categories=finding_categories,
            notification_target_uuid=args.notification_target_uuid,
            propagate=args.propagate,
            severity=args.severity,
            finding_tags=finding_tags,
            project_selector=project_selector,
            project_exceptions=project_exceptions,
            aggregation_type=args.aggregation_type,
            bypass_exceptions=args.bypass_exceptions,
            tags=tags
        )
        
        if result:
            print("=== Notification Policy Created Successfully ===")
            print(f"UUID: {result.get('uuid')}")
            print(f"Name: {result.get('meta', {}).get('name')}")
            print(f"Namespace: {result.get('tenant_meta', {}).get('namespace')}")
            print(f"Finding Categories: {finding_categories}")
            print(f"Notification Target: {args.notification_target_uuid}")
            print(f"Propagate: {args.propagate}")
            print(f"Created: {result.get('meta', {}).get('create_time')}")
            
            # Retrieve and display full details
            if args.verbose:
                print("\n" + "=" * 80)
                print("RETRIEVING NOTIFICATION POLICY DETAILS...")
                print("=" * 80)
                
                retrieved_policy = get_notification_policy(
                    client, args.namespace, result.get('uuid')
                )
                if retrieved_policy:
                    print("\n" + format_notification_policy_for_display(retrieved_policy))
                else:
                    print("Failed to retrieve notification policy details after creation")
        else:
            print("Failed to create notification policy")
            sys.exit(1)
            
    except KeyboardInterrupt:
        logger.info("Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()

