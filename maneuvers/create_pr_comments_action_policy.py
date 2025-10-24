#!/usr/bin/env python3
"""
PR Comments Action Policy Maneuver

A repeatable script for creating notification policies that enable PR comments for various
finding categories using the Endor Labs API client. This script provides parameterized inputs 
for creating comprehensive notification policies with proper targeting and GitHub PR comment 
configuration.

Supported Finding Categories:
- SAST: Static Application Security Testing findings
- SECRETS: Exposed secrets (passwords, tokens, keys)
- SCA: Software Composition Analysis findings
- VULNERABILITY: Vulnerability findings
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

# SAST findings
uv run python maneuvers/create_pr_comments_action_policy.py \
  --tenant-namespace "endor-solutions-tgowan.cockpit" \
  --name "SAST PR Comments Policy" \
  --description "Notification policy for SAST findings to generate PR comments" \
  --finding-categories "SAST" \
  --severity "MEDIUM" \
  --tags "sast,pr-comments" \
  --project-tags "sast-enabled" \
  --dry-run

# SECRETS findings
uv run python maneuvers/create_pr_comments_action_policy.py \
  --tenant-namespace "endor-solutions-tgowan.cockpit" \
  --name "SECRETS PR Comments Policy" \
  --description "Notification policy for SECRETS findings to generate PR comments" \
  --finding-categories "SECRETS" \
  --severity "HIGH" \
  --tags "secrets,pr-comments" \
  --project-tags "secrets-enabled" \
  --dry-run

# Multiple finding categories
uv run python maneuvers/create_pr_comments_action_policy.py \
  --tenant-namespace "endor-solutions-tgowan.cockpit" \
  --name "Security PR Comments Policy" \
  --description "Notification policy for security findings to generate PR comments" \
  --finding-categories "SAST,SECRETS,VULNERABILITY" \
  --severity "MEDIUM" \
  --tags "security,pr-comments" \
  --project-tags "security-enabled" \
  --dry-run

## Note: Notification policies are required for PR comments to appear. This policy can target
## multiple finding categories and configures them to generate PR comments on pull requests.
## The policy creates both a notification target (GitHub PR) and a notification policy.
"""

import argparse
import json
import logging
import os
import sys
from typing import Any, Dict, List, Optional

# Add the src directory to the path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from pydantic import BaseModel, Field

from endor_cockpit.api_client import APIClient

# Configure logging to reduce verbosity
logging.getLogger('urllib3.connectionpool').setLevel(logging.WARNING)
logging.getLogger('endor_cockpit').setLevel(logging.INFO)

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class NotificationTargetMeta(BaseModel):
    """Metadata for notification target creation."""

    name: str = Field(..., description="Notification target name - descriptive identifier for the GitHub PR integration")
    description: str = Field(..., description="Notification target description - explains the purpose and scope of the GitHub PR integration")
    kind: str = Field(default="NotificationTarget", description="Resource kind - always 'NotificationTarget' for notification targets")
    version: str = Field(default="v1", description="Version identifier - API version for the notification target metadata")
    tags: Optional[List[str]] = Field(None, description="Notification target tags - optional labels for categorization and filtering")


class GitHubPRConfig(BaseModel):
    """GitHub PR configuration for notification target."""

    enabled: bool = Field(default=True, description="Enabled flag - whether GitHub PR comments are enabled")


class NotificationTargetAction(BaseModel):
    """Notification target action configuration."""

    action_type: str = Field(default="ACTION_TYPE_GITHUB_PR", description="Action type - always 'ACTION_TYPE_GITHUB_PR' for GitHub PR integrations")
    public: bool = Field(default=False, description="Public flag - whether the action endpoint is public")
    exclude_endor_url: bool = Field(default=False, description="Exclude Endor URL - whether to exclude the Endor Labs app URL from notifications")
    github_pr_config: GitHubPRConfig = Field(..., description="GitHub PR configuration - settings for PR comments")


class NotificationTargetSpec(BaseModel):
    """Specification for notification target creation."""

    action: NotificationTargetAction = Field(..., description="Notification action - GitHub PR configuration and settings")


class CreateNotificationTargetPayload(BaseModel):
    """Complete payload for creating a notification target."""

    meta: NotificationTargetMeta = Field(..., description="Notification target metadata - name, description, and other metadata")
    spec: NotificationTargetSpec = Field(..., description="Notification target specification - GitHub PR configuration and settings")
    propagate: bool = Field(default=False, description="Global propagation flag - whether notification target propagates to child namespaces")


class NotificationPolicyMeta(BaseModel):
    """Metadata for notification policy creation."""

    name: str = Field(..., description="Policy name - descriptive identifier for the notification policy")
    description: str = Field(..., description="Policy description - explains the purpose and scope of the notification policy")
    kind: str = Field(default="Policy", description="Resource kind - always 'Policy' for policies")
    version: str = Field(default="v1", description="Resource version")
    tags: Optional[List[str]] = Field(None, description="Policy tags - optional labels for categorization and filtering")


class SASTFindingConfig(BaseModel):
    """SAST-specific finding configuration for notification policy."""

    severity: Optional[str] = Field(None, description="Severity level - only match findings with this severity (LOW, MEDIUM, HIGH, CRITICAL)")
    confidence: Optional[str] = Field(None, description="Confidence level - only match findings for SAST rules with this confidence")
    language: Optional[str] = Field(None, description="Language - only match findings for this SAST result language")
    sast_tag: Optional[str] = Field(None, description="SAST tag - only match findings that have this SAST tag (e.g., A01:2021, Cryptographic-Failures)")
    custom_tag: Optional[str] = Field(None, description="Custom tag - only match findings that have this custom tag")
    cwe: Optional[str] = Field(None, description="CWE - only match findings with this CWE (e.g., CWE-123, CWE-456)")
    file_scope: Optional[str] = Field(None, description="File scope - only match findings with this file scope (Normal, Test)")
    include_path: Optional[str] = Field(None, description="Include path - only match findings for files that match this glob pattern (e.g., src/golang/**)")
    exclude_path: Optional[str] = Field(None, description="Exclude path - do not match findings for files that match this glob pattern")
    code_owner: Optional[str] = Field(None, description="Code owner - only match findings with this code owner (e.g., @octocat, @team)")


class NotificationPolicySpec(BaseModel):
    """Specification for notification policy creation."""

    policy_type: str = Field(default="POLICY_TYPE_NOTIFICATION", description="Policy type - always NOTIFICATION for notification policies")
    rule: str = Field(..., description="Policy rule in Rego format - required for all policies")
    template_uuid: Optional[str] = Field(None, description="Template UUID - reference to policy template")
    template_version: Optional[str] = Field(None, description="Template version - version of the policy template")
    template_values: Optional[Dict[str, Any]] = Field(None, description="Template values - configuration values for the template")
    project_selector: Optional[List[str]] = Field(None, description="Project selector tags - projects that match these tags will be affected")
    project_exceptions: Optional[List[str]] = Field(None, description="Project exception tags - projects with these tags will be excluded")
    resource_kinds: Optional[List[str]] = Field(None, description="Resource kinds - types of resources this policy applies to")
    disable: bool = Field(default=False, description="Disable flag - whether the policy is disabled")
    finding: Optional[Dict[str, Any]] = Field(None, description="Finding configuration - criteria for matching findings")
    finding_level: Optional[str] = Field(None, description="Finding level - severity level for findings")
    branch_type: str = Field(default="Pull Request", description="Branch type - must be 'Pull Request' for PR comments")
    action: str = Field(default="Warn", description="Action to take - 'Warn' for comments, 'Break the Build' to fail builds")
    sast_config: Optional[SASTFindingConfig] = Field(None, description="SAST-specific configuration")
    query_statements: Optional[List[str]] = Field(None, description="Query statements - OPA query statements to execute")
    notification: Optional[Dict[str, Any]] = Field(None, description="Notification configuration - references notification targets")


class CreateNotificationPolicyPayload(BaseModel):
    """Complete payload for creating a notification policy."""

    meta: NotificationPolicyMeta = Field(..., description="Policy metadata - name, description, and other metadata")
    spec: NotificationPolicySpec = Field(..., description="Policy specification - notification rules and configuration")
    propagate: bool = Field(default=True, description="Global propagation flag - whether policy propagates to child namespaces")


def create_notification_target(
    client: APIClient,
    tenant_namespace: str,
    payload: CreateNotificationTargetPayload
) -> Optional[Dict[str, Any]]:
    """
    Create a notification target using the API client.

    Args:
        client: Authenticated APIClient instance
        tenant_namespace: Target tenant namespace (canonical name)
        payload: Notification target creation payload

    Returns:
        Created notification target data or None if creation failed
    """
    try:
        headers = client.default_headers
        headers.update({
            "Accept": "application/json",
            "Content-Type": "application/json"
        })

        # Convert payload to dict
        request_data = {
            "meta": payload.meta.model_dump(),
            "spec": payload.spec.model_dump(),
            "propagate": payload.propagate
        }

        logger.info(f"Creating notification target in namespace: {tenant_namespace}")
        logger.debug(f"Request data: {json.dumps(request_data, indent=2)}")

        res = client.post(
            f"v1/namespaces/{tenant_namespace}/notification-targets",
            headers=headers,
            data=request_data
        )

        if res.status_code == 200:
            data = res.json()
            logger.info(f"Successfully created notification target: {data.get('uuid', 'unknown')}")
            return data
        else:
            logger.error(f"Failed to create notification target: {res.status_code} - {res.text}")
            return None

    except Exception as e:
        logger.error(f"Error creating notification target: {e}", exc_info=True)
        return None


def create_notification_policy(
    client: APIClient,
    tenant_namespace: str,
    payload: CreateNotificationPolicyPayload
) -> Optional[Dict[str, Any]]:
    """
    Create a notification policy using the API client.

    Args:
        client: Authenticated APIClient instance
        tenant_namespace: Target tenant namespace (canonical name)
        payload: Notification policy creation payload

    Returns:
        Created policy data or None if creation failed
    """
    try:
        headers = client.default_headers
        headers.update({
            "Accept": "application/json",
            "Content-Type": "application/json"
        })

        # Convert payload to dict
        request_data = {
            "meta": payload.meta.model_dump(),
            "spec": payload.spec.model_dump(),
            "propagate": payload.propagate
        }

        logger.info(f"Creating notification policy in namespace: {tenant_namespace}")
        logger.debug(f"Request data: {json.dumps(request_data, indent=2)}")

        res = client.post(
            f"v1/namespaces/{tenant_namespace}/policies",
            headers=headers,
            data=request_data
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


def get_notification_target(
    client: APIClient,
    tenant_namespace: str,
    target_uuid: str
) -> Optional[Dict[str, Any]]:
    """
    Retrieve a notification target by UUID.

    Args:
        client: Authenticated APIClient instance
        tenant_namespace: Target tenant namespace (canonical name)
        target_uuid: UUID of the notification target

    Returns:
        Notification target data or None if retrieval failed
    """
    try:
        headers = client.default_headers
        headers.update({
            "Accept": "application/json"
        })

        logger.info(f"Retrieving notification target: {target_uuid}")

        res = client.get(
            f"v1/namespaces/{tenant_namespace}/notification-targets/{target_uuid}",
            headers=headers
        )

        if res.status_code == 200:
            data = res.json()
            logger.info(f"Successfully retrieved notification target: {target_uuid}")
            return data
        else:
            logger.error(f"Failed to retrieve notification target: {res.status_code} - {res.text}")
            return None

    except Exception as e:
        logger.error(f"Error retrieving notification target: {e}", exc_info=True)
        return None


def get_notification_policy(
    client: APIClient,
    tenant_namespace: str,
    policy_uuid: str
) -> Optional[Dict[str, Any]]:
    """
    Retrieve a notification policy by UUID.

    Args:
        client: Authenticated APIClient instance
        tenant_namespace: Target tenant namespace (canonical name)
        policy_uuid: UUID of the notification policy

    Returns:
        Policy data or None if retrieval failed
    """
    try:
        headers = client.default_headers
        headers.update({
            "Accept": "application/json"
        })

        logger.info(f"Retrieving notification policy: {policy_uuid}")

        res = client.get(
            f"v1/namespaces/{tenant_namespace}/policies/{policy_uuid}",
            headers=headers
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


def format_notification_target_for_display(target_data: Dict[str, Any]) -> str:
    """
    Format notification target data for human-readable display.

    Args:
        target_data: Notification target data from API

    Returns:
        Formatted string for display
    """
    if not target_data:
        return "No notification target data available"

    meta = target_data.get('meta', {})
    spec = target_data.get('spec', {})
    tenant_meta = target_data.get('tenant_meta', {})
    action = spec.get('action', {})
    github_pr_config = action.get('github_pr_config', {})

    output = []
    output.append("=" * 80)
    output.append("NOTIFICATION TARGET DETAILS")
    output.append("=" * 80)

    # Basic Information
    output.append(f"UUID: {target_data.get('uuid', 'N/A')}")
    output.append(f"Name: {meta.get('name', 'N/A')}")
    output.append(f"Description: {meta.get('description', 'N/A')}")
    output.append(f"Kind: {meta.get('kind', 'N/A')}")
    output.append(f"Version: {meta.get('version', 'N/A')}")
    output.append(f"Namespace: {tenant_meta.get('namespace', 'N/A')}")
    output.append(f"Propagate: {target_data.get('propagate', 'N/A')}")
    output.append("")

    # Timestamps
    output.append("TIMESTAMPS:")
    output.append("-" * 40)
    output.append(f"Created: {meta.get('create_time', 'N/A')}")
    output.append(f"Created By: {meta.get('created_by', 'N/A')}")
    output.append(f"Updated: {meta.get('update_time', 'N/A')}")
    output.append(f"Updated By: {meta.get('updated_by', 'N/A')}")
    output.append("")

    # Action Configuration
    output.append("ACTION CONFIGURATION:")
    output.append("-" * 40)
    output.append(f"Action Type: {action.get('action_type', 'N/A')}")
    output.append(f"Public: {action.get('public', 'N/A')}")
    output.append(f"Exclude Endor URL: {action.get('exclude_endor_url', 'N/A')}")
    output.append("")

    # GitHub PR Configuration
    output.append("GITHUB PR CONFIGURATION:")
    output.append("-" * 40)
    output.append(f"Enabled: {github_pr_config.get('enabled', 'N/A')}")
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
    finding_config = spec.get('finding', {})
    template_values = spec.get('template_values', {})
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
    output.append(f"Branch Type: {spec.get('branch_type', 'N/A')}")
    output.append(f"Action: {spec.get('action', 'N/A')}")
    output.append(f"Disabled: {spec.get('disable', 'N/A')}")
    if spec.get('template_uuid'):
        output.append(f"Template UUID: {spec.get('template_uuid', 'N/A')}")
    if spec.get('template_version'):
        output.append(f"Template Version: {spec.get('template_version', 'N/A')}")
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

    # Finding Configuration
    if finding_config:
        output.append("FINDING CONFIGURATION:")
        output.append("-" * 40)
        for key, value in finding_config.items():
            if value is not None:
                output.append(f"  {key}: {value}")
        output.append("")

    # Notification Configuration
    if notification_config:
        output.append("NOTIFICATION CONFIGURATION:")
        output.append("-" * 40)
        for key, value in notification_config.items():
            if value is not None:
                output.append(f"  {key}: {value}")
        output.append("")

    # Template Values
    if template_values:
        output.append("TEMPLATE VALUES:")
        output.append("-" * 40)
        for key, value in template_values.items():
            output.append(f"  {key}: {value}")
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
        'SAST': 'FINDING_CATEGORY_SAST',
        'SECRETS': 'FINDING_CATEGORY_SECRETS',
        'SCA': 'FINDING_CATEGORY_SCA',
        'VULNERABILITY': 'FINDING_CATEGORY_VULNERABILITY',
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


def parse_project_tags(tags_str: str) -> List[str]:
    """Parse comma-separated project tags string into list."""
    return [tag.strip() for tag in tags_str.split(',') if tag.strip()]


def build_sast_finding_config(args) -> Optional[SASTFindingConfig]:
    """Build SAST finding configuration from command line arguments."""
    if not any([args.severity, args.confidence, args.language, args.sast_tag,
                args.custom_tag, args.cwe, args.file_scope, args.include_path,
                args.exclude_path, args.code_owner]):
        return None

    return SASTFindingConfig(
        severity=args.severity,
        confidence=args.confidence,
        language=args.language,
        sast_tag=args.sast_tag,
        custom_tag=args.custom_tag,
        cwe=args.cwe,
        file_scope=args.file_scope,
        include_path=args.include_path,
        exclude_path=args.exclude_path,
        code_owner=args.code_owner
    )


def build_finding_config(sast_config: Optional[SASTFindingConfig], args) -> Dict[str, Any]:
    """Build finding configuration dictionary."""
    finding_config = {}

    # Add SAST-specific configuration
    if sast_config:
        sast_dict = sast_config.model_dump(exclude_none=True)
        finding_config.update(sast_dict)

    # Add branch type (required for PR comments)
    finding_config['branch_type'] = args.branch_type

    return finding_config


def generate_rego_rule(finding_categories: List[str]) -> str:
    """Generate Rego rule for the specified finding categories."""
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
    
    result = {{
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


def main():
    """Main function to create notification target and policy for PR comments."""
    parser = argparse.ArgumentParser(
        description="Create notification target and policy for PR comments using Endor Labs API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic SAST PR comments setup
  python create_pr_comments_action_policy.py \\
    --tenant-namespace "endor-solutions-tgowan.cockpit" \\
    --name "SAST PR Comments" \\
    --description "Notification target and policy for SAST findings to generate PR comments" \\
    --severity "MEDIUM" \\
    --tags "sast,pr-comments" \\
    --project-tags "sast-enabled"

  # High severity SAST policy with specific language
  python create_pr_comments_action_policy.py \\
    --tenant-namespace "tenant.namespace" \\
    --name "Python SAST PR Comments" \\
    --description "SAST notification for Python code with high severity findings" \\
    --severity "HIGH" \\
    --language "python" \\
    --tags "sast,python,high-severity" \\
    --project-tags "python-project" \\
    --action "Break the Build"

  # SAST policy with specific CWE and file patterns
  python create_pr_comments_action_policy.py \\
    --tenant-namespace "tenant.namespace" \\
    --name "Security SAST PR Comments" \\
    --description "SAST notification for security-related findings" \\
    --severity "CRITICAL" \\
    --cwe "CWE-89" \\
    --include-path "src/**" \\
    --exclude-path "test/**" \\
    --tags "sast,security,critical" \\
    --project-tags "security-critical"

  # SAST policy with custom template
  python create_pr_comments_action_policy.py \\
    --tenant-namespace "tenant.namespace" \\
    --name "Custom SAST PR Comments" \\
    --description "SAST notification using custom template" \\
    --template-uuid "custom-sast-template-uuid" \\
    --template-version "v1.0" \\
    --severity "MEDIUM" \\
    --tags "sast,custom" \\
    --project-tags "custom-sast"
        """
    )

    # Required arguments
    parser.add_argument(
        "--tenant-namespace",
        required=True,
        help="Tenant namespace (canonical name) where the policy will be created"
    )
    parser.add_argument(
        "--name",
        required=True,
        help="Policy name - descriptive identifier for the action policy"
    )
    parser.add_argument(
        "--description",
        required=True,
        help="Policy description - explains the purpose and scope of the action policy"
    )

    # Finding Categories Configuration
    parser.add_argument(
        "--finding-categories",
        required=True,
        help="Finding categories - comma-separated list of finding categories to target. "
             "Available categories: SAST, SECRETS, SCA, VULNERABILITY, MALWARE, LICENSE_RISK, "
             "SUPPLY_CHAIN, OPERATIONAL, SECURITY, CICD, GHACTIONS, CONTAINER, AI_MODELS, TOOLS, SCPM. "
             "Examples: 'SAST', 'SECRETS', 'SAST,SECRETS,VULNERABILITY'"
    )

    # Finding-Specific Configuration
    finding_group = parser.add_argument_group(
        "Finding-Specific Configuration",
        "Configure finding-specific criteria (SAST, SECRETS, etc.)"
    )
    finding_group.add_argument(
        "--severity",
        choices=["LOW", "MEDIUM", "HIGH", "CRITICAL"],
        help="Severity level - only match findings with this severity level"
    )
    finding_group.add_argument(
        "--confidence",
        help="Confidence level - only match findings for SAST rules with this confidence level"
    )
    finding_group.add_argument(
        "--language",
        help="Language - only match findings for this SAST result language (e.g., python, javascript, java)"
    )
    finding_group.add_argument(
        "--sast-tag",
        help="SAST tag - only match findings that have this SAST tag (e.g., A01:2021, Cryptographic-Failures)"
    )
    finding_group.add_argument(
        "--custom-tag",
        help="Custom tag - only match findings that have this custom tag"
    )
    finding_group.add_argument(
        "--cwe",
        help="CWE - only match findings with this CWE (e.g., CWE-123, CWE-456)"
    )
    finding_group.add_argument(
        "--file-scope",
        choices=["Normal", "Test"],
        help="File scope - only match findings with this file scope"
    )
    finding_group.add_argument(
        "--include-path",
        help="Include path - only match findings for files that match this glob pattern (e.g., src/golang/**)"
    )
    finding_group.add_argument(
        "--exclude-path",
        help="Exclude path - do not match findings for files that match this glob pattern"
    )
    finding_group.add_argument(
        "--code-owner",
        help="Code owner - only match findings with this code owner (e.g., @octocat, @team)"
    )

    # Policy Configuration
    policy_group = parser.add_argument_group(
        "Policy Configuration",
        "Configure policy behavior and targeting"
    )
    policy_group.add_argument(
        "--branch-type",
        default="Pull Request",
        choices=["Default", "Ref", "Pull Request"],
        help="Branch type - must be 'Pull Request' for PR comments (default: Pull Request)"
    )
    policy_group.add_argument(
        "--action",
        default="Warn",
        choices=["Warn", "Break the Build"],
        help="Action to take - 'Warn' for comments, 'Break the Build' to fail builds (default: Warn)"
    )
    policy_group.add_argument(
        "--project-tags",
        help="Project selector tags - comma-separated list of tags that projects must have to be affected"
    )
    policy_group.add_argument(
        "--project-exceptions",
        help="Project exception tags - comma-separated list of tags for projects to exclude"
    )

    # Template Configuration
    template_group = parser.add_argument_group(
        "Template Configuration",
        "Configure policy template (optional)"
    )
    template_group.add_argument(
        "--template-uuid",
        help="Template UUID - reference to policy template"
    )
    template_group.add_argument(
        "--template-version",
        help="Template version - version of the policy template"
    )

    # Optional arguments
    parser.add_argument(
        "--tags",
        help="Policy tags - comma-separated list of tags for categorization"
    )
    parser.add_argument(
        "--no-propagate",
        action="store_true",
        help="Don't propagate to child namespaces (default: propagate=True)"
    )
    parser.add_argument(
        "--disable",
        action="store_true",
        help="Create the policy in disabled state"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show the payload that would be sent without creating the policy"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force creation even if resources already exist (will create with unique names)"
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
        project_selector = (
            parse_project_tags(args.project_tags) if args.project_tags else None
        )
        project_exceptions = (
            parse_project_tags(args.project_exceptions) if args.project_exceptions else None
        )

        # Build SAST configuration
        sast_config = build_sast_finding_config(args)

        # Build finding configuration
        finding_config = build_finding_config(sast_config, args)

        # Build template values if template is specified
        template_values = {}
        if args.template_uuid:
            template_values['template_uuid'] = args.template_uuid
        if args.template_version:
            template_values['template_version'] = args.template_version

        # Handle force mode - generate unique names if needed
        target_name = args.name
        policy_name = f"{args.name} Policy"

        if args.force:
            import time
            timestamp = int(time.time())
            target_name = f"{args.name}-{timestamp}"
            policy_name = f"{args.name} Policy-{timestamp}"

        # Create notification target payload
        target_payload = CreateNotificationTargetPayload(
            meta=NotificationTargetMeta(
                name=target_name,
                description=args.description,
                tags=tags
            ),
            spec=NotificationTargetSpec(
                action=NotificationTargetAction(
                    action_type="ACTION_TYPE_GITHUB_PR",
                    public=False,
                    exclude_endor_url=False,
                    github_pr_config=GitHubPRConfig(enabled=True)
                )
            ),
            propagate=False
        )

        if args.dry_run:
            print("=== DRY RUN - Notification Target Payload ===")
            print(json.dumps(target_payload.model_dump(), indent=2))
            print("\n=== DRY RUN - Notification Policy Payload ===")
            print("(Policy payload would reference the notification target)")
            return

        # Create the notification target first
        target_result = create_notification_target(
            client, args.tenant_namespace, target_payload
        )

        if not target_result:
            if args.force:
                # Try with a unique name
                import time
                timestamp = int(time.time())
                target_name = f"{args.name}-{timestamp}"
                target_payload.meta.name = target_name
                target_result = create_notification_target(
                    client, args.tenant_namespace, target_payload
                )

                if not target_result:
                    print("Failed to create notification target even with unique name")
                    sys.exit(1)
            else:
                print(
                    "Failed to create notification target. Use --force to create with unique name."
                )
                sys.exit(1)

        target_uuid = target_result.get('uuid')
        print("=== Notification Target Created Successfully ===")
        print(f"Target UUID: {target_uuid}")
        print(f"Name: {target_result.get('meta', {}).get('name', 'unknown')}")
        print(
            f"Namespace: {target_result.get('tenant_meta', {}).get('namespace', 'unknown')}"
        )
        print(f"Created: {target_result.get('meta', {}).get('create_time', 'unknown')}")

        # Create the notification policy that references the target
        policy_payload = CreateNotificationPolicyPayload(
            meta=NotificationPolicyMeta(
                name=policy_name,
                description=f"Notification policy for {args.description}",
                tags=tags
            ),
            spec=NotificationPolicySpec(
                policy_type="POLICY_TYPE_NOTIFICATION",
                rule=generate_rego_rule(finding_categories),
                template_uuid=args.template_uuid,
                template_version=args.template_version,
                template_values=template_values if template_values else None,
                project_selector=project_selector,
                project_exceptions=project_exceptions,
                resource_kinds=["Finding"],
                disable=args.disable,
                finding_level=args.severity,
                branch_type=args.branch_type,
                action=args.action,
                sast_config=sast_config,
                finding=finding_config if finding_config else None,
                query_statements=[generate_query_statement(finding_categories)],
                notification={
                    "notification_target_uuids": [target_uuid],
                    "aggregation_type": "AGGREGATION_TYPE_PROJECT",
                    "bypass_exceptions": False
                }
            ),
            propagate=not args.no_propagate
        )

        # Create the notification policy
        policy_result = create_notification_policy(
            client, args.tenant_namespace, policy_payload
        )

        if policy_result:
            policy_uuid = policy_result.get('uuid')
            print("\n=== Notification Policy Created Successfully ===")
            print(f"Policy UUID: {policy_uuid}")
            print(f"Name: {policy_result.get('meta', {}).get('name', 'unknown')}")
            print(
                f"Namespace: {policy_result.get('tenant_meta', {}).get('namespace', 'unknown')}"
            )
            print(
                f"Created: {policy_result.get('meta', {}).get('create_time', 'unknown')}"
            )
            print(
                f"Branch Type: {policy_result.get('spec', {}).get('branch_type', 'unknown')}"
            )
            print(f"Action: {policy_result.get('spec', {}).get('action', 'unknown')}")

            # Retrieve and display both target and policy details
            if target_uuid and policy_uuid:
                print("\n" + "=" * 80)
                print("RETRIEVING NOTIFICATION TARGET DETAILS...")
                print("=" * 80)

                retrieved_target = get_notification_target(
                    client, args.tenant_namespace, target_uuid
                )
                if retrieved_target:
                    print(
                        "\n" + format_notification_target_for_display(retrieved_target)
                    )
                else:
                    print(
                        "Failed to retrieve notification target details after creation"
                    )

                print("\n" + "=" * 80)
                print("RETRIEVING NOTIFICATION POLICY DETAILS...")
                print("=" * 80)

                retrieved_policy = get_notification_policy(
                    client, args.tenant_namespace, policy_uuid
                )
                if retrieved_policy:
                    print(
                        "\n" + format_notification_policy_for_display(retrieved_policy)
                    )
                else:
                    print("Failed to retrieve notification policy details after creation")
            else:
                print("Warning: No UUID returned from creation")
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
