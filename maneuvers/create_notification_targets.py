#!/usr/bin/env python3
"""
Create Notification Targets Maneuver

A repeatable script for creating notification targets using the Endor Labs API client.
This script can create both JIRA and GitHub PR Remediation notification targets with
proper authentication and configuration.

Supported Action Types:
- JIRA: Creates JIRA issues for security findings and policy violations
- GitHub PR Remediation: Creates PR comments for security findings

Based on the OpenAPI schema and NotificationTarget resource structure.

Example:

# Create JIRA notification target
uv run python maneuvers/create_notification_targets.py \
  --tenant-namespace "tenant.namespace" \
  --name "Security JIRA Integration" \
  --description "JIRA integration for security findings" \
  --action-type "jira" \
  --jira-url "https://endorlabs.atlassian.net/" \
  --atlassian-username "tgowan@endor.ai" \
  --atlassian-pat "$JIRA_BOARD_TEST_PAT" \
  --project-key "CSJIT" \
  --issue-type "VULN" \
  --resolved-status "Done" \
  --force

# Create GitHub PR Remediation notification target
uv run python maneuvers/create_notification_targets.py \
  --tenant-namespace "tenant.namespace" \
  --name "GitHub PR Remediation" \
  --description "GitHub PR comments for security findings" \
  --action-type "github-pr" \
  --github-pr-enabled \
  --force

## Note: This maneuver creates notification targets that can be referenced by notification policies.
## The target defines the action (JIRA issue, PR comment) and the policy defines when to trigger it.
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

from endorlabs.api_client import APIClient

# Configure logging to reduce verbosity
logging.getLogger('urllib3.connectionpool').setLevel(logging.WARNING)
logging.getLogger('endorlabs').setLevel(logging.INFO)

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class NotificationTargetMeta(BaseModel):
    """Metadata for notification target creation."""

    name: str = Field(
        ..., description="Notification target name - descriptive identifier for the integration"
    )
    description: str = Field(
        ..., description="Notification target description - explains the purpose and scope of the integration"
    )
    kind: str = Field(
        default="NotificationTarget", description="Resource kind - always 'NotificationTarget' for notification targets"
    )
    version: str = Field(
        default="v1", description="Version identifier - API version for the notification target metadata"
    )
    tags: Optional[List[str]] = Field(None, description="Notification target tags - optional labels for categorization and filtering")


class JIRAConfigCustomField(BaseModel):
    """JIRA custom field configuration."""
    
    field_id: str = Field(..., description="JIRA custom field ID")
    field_value: str = Field(..., description="Value for the custom field")


class JIRAConfig(BaseModel):
    """JIRA configuration for notification target."""

    url: str = Field(..., description="JIRA endpoint URL - the base URL of your JIRA instance")
    user_name: Optional[str] = Field(None, description="Atlassian username - the username for JIRA authentication")
    api_key: Optional[str] = Field(None, description="Atlassian Personal Access Token (PAT) - API key for JIRA authentication")
    project_key: str = Field(..., description="JIRA project key - the project where issues will be created")
    issue_type: Optional[str] = Field(None, description="JIRA issue type enum (deprecated - use jira_issue_type instead)")
    jira_issue_type: Optional[str] = Field(None, description="JIRA issue type - the type of issues to create (e.g., VULN, Bug, Task)")
    labels: Optional[List[str]] = Field(None, description="JIRA issue labels - optional labels to apply to created issues")
    custom_fields: Optional[List[JIRAConfigCustomField]] = Field(None, description="JIRA custom fields - optional custom fields for the issue")
    resolve_state: Optional[str] = Field(None, description="Resolved status - the final status when issues are resolved")
    use_bearer_token: bool = Field(default=False, description="Use bearer token authentication - set to true for bearer token auth")
    bearer_token: Optional[str] = Field(None, description="Bearer token for authentication - required if use_bearer_token is true")
    components: Optional[List[str]] = Field(None, description="JIRA components - optional components to assign to issues")


class GitHubPRConfig(BaseModel):
    """GitHub PR configuration for notification target."""

    enabled: bool = Field(..., description="Enable GitHub PR remediation - whether to create PR comments for findings")


class NotificationTargetAction(BaseModel):
    """Notification target action configuration."""

    action_type: str = Field(
        ..., description="Action type - 'ACTION_TYPE_JIRA' for JIRA integrations or 'ACTION_TYPE_GITHUB_PR' for GitHub PR remediation"
    )
    public: bool = Field(
        default=False, description="Public flag - whether the action endpoint is public"
    )
    exclude_endor_url: bool = Field(
        default=False, description="Exclude Endor URL - whether to exclude the Endor Labs app URL from notifications"
    )
    jira_config: Optional[JIRAConfig] = Field(None, description="JIRA configuration - authentication and project settings (required for JIRA)")
    github_pr_config: Optional[GitHubPRConfig] = Field(None, description="GitHub PR configuration - PR remediation settings (required for GitHub PR)")


class NotificationTargetSpec(BaseModel):
    """Specification for notification target creation."""

    action: NotificationTargetAction = Field(
        ..., description="Notification action - JIRA or GitHub PR configuration and settings"
    )


class CreateNotificationTargetPayload(BaseModel):
    """Complete payload for creating a notification target."""

    meta: NotificationTargetMeta = Field(
        ..., description="Notification target metadata - name, description, and other metadata"
    )
    spec: NotificationTargetSpec = Field(..., description="Notification target specification - JIRA or GitHub PR configuration and settings")
    propagate: bool = Field(default=False, description="Global propagation flag - whether notification target propagates to child namespaces")


def delete_notification_target(
    client: APIClient,
    tenant_namespace: str,
    notification_target_uuid: str
) -> bool:
    """
    Delete a notification target by UUID.

    Args:
        client: Authenticated APIClient instance
        tenant_namespace: Target tenant namespace (canonical name)
        notification_target_uuid: UUID of the notification target to delete

    Returns:
        True if deletion successful, False otherwise
    """
    try:
        logger.info(f"Deleting notification target: {notification_target_uuid}")

        res = client.delete(
            f"v1/namespaces/{tenant_namespace}/notification-targets/{notification_target_uuid}"
        )

        if res.status_code == 200:
            logger.info(f"Successfully deleted notification target: {notification_target_uuid}")
            return True
        else:
            logger.error(f"Failed to delete notification target: {res.status_code} - {res.text}")
            return False

    except Exception as e:
        logger.error(f"Error deleting notification target: {e}", exc_info=True)
        return False


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
        logger.info(f"Creating notification target in namespace: {tenant_namespace}")

        # Create sanitized payload for debug logging (remove sensitive data)
        debug_payload = payload.model_dump()
        if 'spec' in debug_payload and 'action' in debug_payload['spec']:
            if 'jira_config' in debug_payload['spec']['action'] and debug_payload['spec']['action']['jira_config']:
                jira_config = debug_payload['spec']['action']['jira_config'].copy()
                if 'api_key' in jira_config:
                    jira_config['api_key'] = '<redacted>'
                if 'bearer_token' in jira_config:
                    jira_config['bearer_token'] = '<redacted>'
                debug_payload['spec']['action']['jira_config'] = jira_config

        logger.debug(f"Request data: {json.dumps(debug_payload, indent=2)}")

        res = client.post(
            f"v1/namespaces/{tenant_namespace}/notification-targets",
            json=payload.model_dump(),
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
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


def get_notification_target(
    client: APIClient,
    tenant_namespace: str,
    notification_target_uuid: str
) -> Optional[Dict[str, Any]]:
    """
    Retrieve a notification target by UUID.

    Args:
        client: Authenticated APIClient instance
        tenant_namespace: Target tenant namespace (canonical name)
        notification_target_uuid: UUID of the notification target

    Returns:
        Notification target data or None if retrieval failed
    """
    try:
        logger.info(f"Retrieving notification target: {notification_target_uuid}")

        res = client.get(
            f"v1/namespaces/{tenant_namespace}/notification-targets/{notification_target_uuid}"
        )

        if res.status_code == 200:
            data = res.json()
            logger.info(f"Successfully retrieved notification target: {notification_target_uuid}")
            return data
        else:
            logger.error(f"Failed to retrieve notification target: {res.status_code} - {res.text}")
            return None

    except Exception as e:
        logger.error(f"Error retrieving notification target: {e}", exc_info=True)
        return None


def format_notification_target_for_display(notification_target_data: Dict[str, Any]) -> str:
    """
    Format notification target data for human-readable display.

    Args:
        notification_target_data: Notification target data from API

    Returns:
        Formatted string for display
    """
    if not notification_target_data:
        return "No notification target data available"

    meta = notification_target_data.get('meta', {})
    spec = notification_target_data.get('spec', {})
    tenant_meta = notification_target_data.get('tenant_meta', {})
    action = spec.get('action', {})
    jira_config = action.get('jira_config', {})
    github_pr_config = action.get('github_pr_config', {})

    output = []
    output.append("=" * 80)
    output.append("NOTIFICATION TARGET DETAILS")
    output.append("=" * 80)

    # Basic Information
    output.append(f"UUID: {notification_target_data.get('uuid', 'N/A')}")
    output.append(f"Name: {meta.get('name', 'N/A')}")
    output.append(f"Description: {meta.get('description', 'N/A')}")
    output.append(f"Kind: {meta.get('kind', 'N/A')}")
    output.append(f"Version: {meta.get('version', 'N/A')}")
    output.append(f"Namespace: {tenant_meta.get('namespace', 'N/A')}")
    output.append(f"Propagate: {notification_target_data.get('propagate', 'N/A')}")

    # Timestamps
    output.append("")
    output.append("TIMESTAMPS:")
    output.append("-" * 40)
    output.append(f"Created: {meta.get('create_time', 'N/A')}")
    output.append(f"Created By: {meta.get('created_by', 'N/A')}")
    output.append(f"Updated: {meta.get('update_time', 'N/A')}")
    output.append(f"Updated By: {meta.get('updated_by', 'N/A')}")

    # Tags
    if meta.get('tags'):
        output.append("")
        output.append("TAGS:")
        output.append("-" * 40)
        for tag in meta.get('tags', []):
            output.append(f"  • {tag}")

    # Action Configuration
    output.append("")
    output.append("ACTION CONFIGURATION:")
    output.append("-" * 40)
    output.append(f"Action Type: {action.get('action_type', 'N/A')}")
    output.append(f"Public: {action.get('public', 'N/A')}")
    output.append(f"Exclude Endor URL: {action.get('exclude_endor_url', 'N/A')}")

    # JIRA Configuration
    if jira_config:
        output.append("")
        output.append("JIRA CONFIGURATION:")
        output.append("-" * 40)
        output.append(f"URL: {jira_config.get('url', 'N/A')}")
        output.append(f"Username: {jira_config.get('user_name', 'N/A')}")
        output.append(f"Project Key: {jira_config.get('project_key', 'N/A')}")
        output.append(f"Issue Type: {jira_config.get('jira_issue_type', 'N/A')}")
        output.append(f"Resolve State: {jira_config.get('resolve_state', 'N/A')}")
        output.append(f"Use Bearer Token: {jira_config.get('use_bearer_token', 'N/A')}")

        # Labels
        if jira_config.get('labels'):
            output.append("")
            output.append("JIRA LABELS:")
            output.append("-" * 40)
            for label in jira_config.get('labels', []):
                output.append(f"  • {label}")

        # Components
        if jira_config.get('components'):
            output.append("")
            output.append("JIRA COMPONENTS:")
            output.append("-" * 40)
            for component in jira_config.get('components', []):
                output.append(f"  • {component}")

    # GitHub PR Configuration
    if github_pr_config:
        output.append("")
        output.append("GITHUB PR CONFIGURATION:")
        output.append("-" * 40)
        output.append(f"Enabled: {github_pr_config.get('enabled', 'N/A')}")

    output.append("=" * 80)

    return "\n".join(output)


def parse_labels(labels_str: str) -> List[str]:
    """Parse comma-separated labels string into list."""
    return [label.strip() for label in labels_str.split(',') if label.strip()]


def parse_components(components_str: str) -> List[str]:
    """Parse comma-separated components string into list."""
    return [
        component.strip() for component in components_str.split(',') if component.strip()
    ]


def parse_tags(tags_str: str) -> List[str]:
    """Parse comma-separated tags string into list."""
    return [tag.strip() for tag in tags_str.split(',') if tag.strip()]


def main():
    """Main function to create notification target with command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Create notification target using Endor Labs API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Create JIRA notification target with Basic Authentication
  python create_notification_targets.py \\
    --tenant-namespace "tenant.namespace" \\
    --name "Security JIRA Integration" \\
    --description "JIRA integration for security findings" \\
    --action-type "jira" \\
    --jira-url "https://endorlabs.atlassian.net/" \\
    --atlassian-username "tgowan@endor.ai" \\
    --atlassian-pat "$JIRA_BOARD_TEST_PAT" \\
    --project-key "CSJIT" \\
    --issue-type "VULN" \\
    --resolved-status "Done" \\

  # Create JIRA notification target with Bearer Token Authentication
  python create_notification_targets.py \\
    --tenant-namespace "tenant.namespace" \\
    --name "JIRA Integration with Bearer Token" \\
    --description "JIRA integration using bearer token authentication" \\
    --action-type "jira" \\
    --jira-url "https://company.atlassian.net/" \\
    --atlassian-username "user@company.com" \\
    --bearer-token "$JIRA_BEARER_TOKEN" \\
    --project-key "PROJ" \\
    --issue-type "Bug" \\
    --resolved-status "Closed" \\
 \\
    --components "Security,Compliance"

  # Create GitHub PR Remediation notification target
  python create_notification_targets.py \\
    --tenant-namespace "tenant.namespace" \\
    --name "GitHub PR Remediation" \\
    --description "GitHub PR comments for security findings" \\
    --action-type "github-pr" \\
    --github-pr-enabled

  # Force overwrite existing notification target
  python create_notification_targets.py \\
    --tenant-namespace "tenant.namespace" \\
    --name "Updated JIRA Integration" \\
    --description "Updated JIRA integration with force flag" \\
    --action-type "jira" \\
    --jira-url "https://endorlabs.atlassian.net/" \\
    --atlassian-username "tgowan@endor.ai" \\
    --atlassian-pat "$JIRA_BOARD_TEST_PAT" \\
    --project-key "CSJIT" \\
    --issue-type "VULN" \\
    --resolved-status "Done" \\
 \\
    --force
        """
    )

    # Required arguments
    parser.add_argument(
        "--tenant-namespace",
        required=True,
        help="Tenant namespace (canonical name) where the notification target will be created"
    )
    parser.add_argument(
        "--name",
        required=True,
        help="Notification target name - descriptive identifier for the integration"
    )
    parser.add_argument(
        "--description",
        required=True,
        help="Notification target description - explains the purpose and scope of the integration"
    )
    parser.add_argument(
        "--action-type",
        required=True,
        choices=["jira", "github-pr", "webhook", "email", "vanta", "slack"],
        help="""Action type for the notification target:
        - 'jira': Create JIRA issues for security findings (requires JIRA credentials)
        - 'github-pr': Enable GitHub PR comments for security findings (GitHub App Pro required)
        - 'webhook': Send webhook notifications to external systems
        - 'email': Send email notifications
        - 'vanta': Integrate with Vanta compliance platform
        - 'slack': Send Slack notifications"""
    )

    # JIRA Configuration arguments (required for JIRA action type)
    jira_group = parser.add_argument_group(
        "JIRA Configuration",
        "JIRA-specific configuration options (required for --action-type jira)"
    )
    jira_group.add_argument(
        "--jira-url",
        default="https://endorlabs.atlassian.net/",
        help="JIRA endpoint URL - the base URL of your JIRA instance (e.g., https://company.atlassian.net/)"
    )
    jira_group.add_argument(
        "--atlassian-username",
        help="Atlassian username - the username for JIRA authentication"
    )
    jira_group.add_argument(
        "--atlassian-pat",
        help="Atlassian Personal Access Token (PAT) - API key for JIRA authentication (required for basic auth)"
    )
    jira_group.add_argument(
        "--bearer-token",
        help="Bearer token for authentication - required for bearer token authentication"
    )
    jira_group.add_argument(
        "--project-key",
        help="JIRA project key - the project where issues will be created (e.g., 'CSJIT' creates issues like CSJIT-123)"
    )
    jira_group.add_argument(
        "--issue-type",
        help="JIRA issue type - the type of issues to create (e.g., VULN, Bug, Task, Story). Must match exact issue type on your JIRA board (case-sensitive)"
    )
    jira_group.add_argument(
        "--resolved-status",
        help="Resolved status - the final status when issues are resolved (e.g., Done, Closed, Resolved, Fixed). If not specified, Endor Labs will attempt to determine your project's resolution status"
    )
    jira_group.add_argument(
        "--labels",
        help="JIRA issue labels - comma-separated list of labels to apply to created issues (optional). Endor Labs automatically adds 'endorlabs-scan' and 'endor-severity' labels"
    )
    jira_group.add_argument(
        "--components",
        help="JIRA components - comma-separated list of components to assign to issues (for company-managed JIRA projects)"
    )

    # GitHub PR Configuration arguments (required for GitHub PR action type)
    github_group = parser.add_argument_group(
        "GitHub PR Configuration",
        "GitHub PR-specific configuration options (required for --action-type github-pr)"
    )
    github_group.add_argument(
        "--github-pr-enabled",
        action="store_true",
        help="Enable GitHub PR remediation - whether to create PR comments for findings (requires GitHub App Pro and upgrades & remediation feature)"
    )

    # Optional arguments
    parser.add_argument(
        "--tags",
        help="Notification target tags - comma-separated list of tags for categorization"
    )
    parser.add_argument(
        "--public",
        action="store_true",
        help="Public flag - whether the action endpoint is public"
    )
    parser.add_argument(
        "--exclude-endor-url",
        action="store_true",
        help="Exclude Endor URL - whether to exclude the Endor Labs app URL from notifications"
    )
    parser.add_argument(
        "--propagate",
        action="store_true",
        help="Enable propagation to child namespaces"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show the payload that would be sent without creating the notification target"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force overwrite - delete existing notification target with same name before creating new one"
    )

    args = parser.parse_args()

    # Set logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Validate arguments based on action type
    if args.action_type == "jira":
        if not args.project_key:
            parser.error("--project-key is required for JIRA action type")
        # Labels are optional based on real-world usage
        if not args.atlassian_pat and not args.bearer_token:
            parser.error("Either --atlassian-pat or --bearer-token is required for JIRA action type")
        if args.atlassian_pat and args.bearer_token:
            parser.error("Cannot specify both --atlassian-pat and --bearer-token. Choose one.")
    elif args.action_type == "github-pr":
        if not args.github_pr_enabled:
            parser.error("--github-pr-enabled is required for GitHub PR action type")

    try:
        # Initialize API client
        logger.info("Initializing API client...")
        client = APIClient()

        # Parse arguments
        tags = parse_tags(args.tags) if args.tags else None
        labels = parse_labels(args.labels) if args.labels else None
        components = parse_components(args.components) if args.components else None

        # Create action configuration based on action type
        if args.action_type == "jira":
            # Create JIRA configuration
            jira_config = JIRAConfig(
                url=args.jira_url,
                user_name=args.atlassian_username,
                api_key=args.atlassian_pat if args.atlassian_pat else None,
                project_key=args.project_key,
                issue_type=None,  # Deprecated field
                jira_issue_type=args.issue_type,
                labels=labels,  # Required field
                custom_fields=None,  # Optional custom fields
                resolve_state=args.resolved_status,
                use_bearer_token=bool(args.bearer_token),
                bearer_token=args.bearer_token if args.bearer_token else None,
                components=components
            )

            # Create notification target action
            action = NotificationTargetAction(
                action_type="ACTION_TYPE_JIRA",
                public=args.public,
                exclude_endor_url=args.exclude_endor_url,
                jira_config=jira_config,
                github_pr_config=None
            )
        else:  # github-pr
            # Create GitHub PR configuration
            github_pr_config = GitHubPRConfig(
                enabled=args.github_pr_enabled
            )

            # Create notification target action
            action = NotificationTargetAction(
                action_type="ACTION_TYPE_GITHUB_PR",
                public=args.public,
                exclude_endor_url=args.exclude_endor_url,
                jira_config=None,
                github_pr_config=github_pr_config
            )

        # Create notification target spec
        spec = NotificationTargetSpec(
            action=action
        )

        # Create meta object
        meta = NotificationTargetMeta(
            name=args.name,
            description=args.description,
            tags=tags
        )

        # Create payload
        payload = CreateNotificationTargetPayload(
            meta=meta,
            spec=spec,
            propagate=args.propagate
        )

        if args.dry_run:
            print("=== DRY RUN - Notification Target Payload ===")

            # Create sanitized payload for dry run (remove sensitive data)
            dry_run_payload = payload.model_dump()
            if 'spec' in dry_run_payload and 'action' in dry_run_payload['spec']:
                if 'jira_config' in dry_run_payload['spec']['action'] and dry_run_payload['spec']['action']['jira_config']:
                    jira_config = dry_run_payload['spec']['action']['jira_config'].copy()
                    if 'api_key' in jira_config:
                        jira_config['api_key'] = '<redacted>'
                    if 'bearer_token' in jira_config:
                        jira_config['bearer_token'] = '<redacted>'
                    dry_run_payload['spec']['action']['jira_config'] = jira_config

            print(json.dumps(dry_run_payload, indent=2))
            return

        # Handle force flag - delete existing notification target with same name
        if args.force:
            logger.info(f"Force flag enabled - checking for existing notification target with name: {args.name}")
            # List notification targets to find existing one with same name
            try:
                res = client.get(f"v1/namespaces/{args.tenant_namespace}/notification-targets")
                if res.status_code == 200:
                    data = res.json()
                    notification_targets = data.get('list', {}).get('objects', [])
                    for notification_target in notification_targets:
                        if notification_target.get('meta', {}).get('name') == args.name:
                            existing_uuid = notification_target.get('uuid')
                            logger.info(f"Found existing notification target with name '{args.name}': {existing_uuid}")
                            if delete_notification_target(client, args.tenant_namespace, existing_uuid):
                                logger.info(f"Successfully deleted existing notification target: {existing_uuid}")
                            else:
                                logger.warning(f"Failed to delete existing notification target: {existing_uuid}")
                            break
                    else:
                        logger.info(f"No existing notification target found with name: {args.name}")
                else:
                    logger.warning(f"Failed to list notification targets: {res.status_code} - {res.text}")
            except Exception as e:
                logger.warning(f"Error checking for existing notification targets: {e}")

        # Create the notification target
        result = create_notification_target(client, args.tenant_namespace, payload)

        if result:
            notification_target_uuid = result.get('uuid')
            print("=== Notification Target Created Successfully ===")
            print(f"UUID: {notification_target_uuid}")
            print(f"Name: {result.get('meta', {}).get('name', 'unknown')}")
            print(f"Namespace: {result.get('tenant_meta', {}).get('namespace', 'unknown')}")
            print(f"Action Type: {args.action_type}")
            print(f"Created: {result.get('meta', {}).get('create_time', 'unknown')}")

            # Retrieve the notification target and display in human-readable format
            if notification_target_uuid:
                print("\n" + "=" * 80)
                print("RETRIEVING NOTIFICATION TARGET DETAILS...")
                print("=" * 80)

                retrieved_notification_target = get_notification_target(client, args.tenant_namespace, notification_target_uuid)
                if retrieved_notification_target:
                    print("\n" + format_notification_target_for_display(retrieved_notification_target))
                else:
                    print("Failed to retrieve notification target details after creation")
            else:
                print("Warning: No UUID returned from notification target creation")
        else:
            print("Failed to create notification target")
            sys.exit(1)

    except KeyboardInterrupt:
        logger.info("Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()

