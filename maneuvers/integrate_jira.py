#!/usr/bin/env python3
"""
JIRA Integration Maneuver

A repeatable script for creating JIRA notification targets using the Endor Labs API client.
This script provides parameterized inputs for all necessary fields to create comprehensive
JIRA notification targets with proper authentication and configuration.

Based on the OpenAPI schema and NotificationTarget resource structure.

Example:

uv run python maneuvers/integrate_jira.py \
  --tenant-namespace "endor-solutions-tgowan.cockpit" \
  --name "Test JIRA notification" \
  --description "Test Installation created by maneuver" \
  --issue-type "VULN" \
  --auth-method "basic" \
  --project-key "CSJIT" \
  --resolved-status "Done" \
  --atlassian-username "tgowan@endor.ai" \
  --atlassian-pat "$JIRA_BOARD_TEST_PAT" \
  --force

## Note: The JIRA installation integrates with Endor Labs notification system to create
## JIRA issues for security findings and policy violations.
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

    name: str = Field(
        ..., description="Notification target name - descriptive identifier for the JIRA integration"
    )
    description: str = Field(
        ..., description="Notification target description - explains the purpose and scope of the JIRA integration"
    )
    kind: str = Field(
        default="NotificationTarget", description="Resource kind - always 'NotificationTarget' for notification targets"
    )
    version: str = Field(
        default="v1", description="Version identifier - API version for the notification target metadata"
    )
    tags: Optional[List[str]] = Field(None, description="Notification target tags - optional labels for categorization and filtering")


class JIRAConfig(BaseModel):
    """JIRA configuration for notification target."""

    url: str = Field(..., description="JIRA endpoint URL - the base URL of your JIRA instance")
    user_name: str = Field(..., description="Atlassian username - the username for JIRA authentication")
    api_key: str = Field(..., description="Atlassian Personal Access Token (PAT) - API key for JIRA authentication")
    project_key: str = Field(..., description="JIRA project key - the project where issues will be created")
    jira_issue_type: str = Field(..., description="JIRA issue type - the type of issues to create (e.g., VULN, Bug, Task)")
    resolve_state: str = Field(..., description="Resolved status - the final status when issues are resolved")
    use_bearer_token: bool = Field(default=False, description="Use bearer token authentication - set to true for bearer token auth")
    bearer_token: Optional[str] = Field(None, description="Bearer token for authentication - required if use_bearer_token is true")
    labels: Optional[List[str]] = Field(None, description="JIRA issue labels - optional labels to apply to created issues")
    components: Optional[List[str]] = Field(None, description="JIRA components - optional components to assign to issues")


class NotificationTargetAction(BaseModel):
    """Notification target action configuration."""

    action_type: str = Field(
        default="ACTION_TYPE_JIRA", description="Action type - always 'ACTION_TYPE_JIRA' for JIRA integrations"
    )
    public: bool = Field(
        default=False, description="Public flag - whether the action endpoint is public"
    )
    exclude_endor_url: bool = Field(
        default=False, description="Exclude Endor URL - whether to exclude the Endor Labs app URL from notifications"
    )
    jira_config: JIRAConfig = Field(
        ..., description="JIRA configuration - authentication and project settings"
    )


class NotificationTargetSpec(BaseModel):
    """Specification for notification target creation."""

    action: NotificationTargetAction = Field(
        ..., description="Notification action - JIRA configuration and settings"
    )


class CreateNotificationTargetPayload(BaseModel):
    """Complete payload for creating a notification target."""

    meta: NotificationTargetMeta = Field(
        ..., description="Notification target metadata - name, description, and other metadata"
    )
    spec: NotificationTargetSpec = Field(..., description="Notification target specification - JIRA configuration and settings")
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
        headers = client.default_headers
        headers.update({
            "Accept": "application/json"
        })

        logger.info(f"Deleting notification target: {notification_target_uuid}")

        res = client.delete(
            f"v1/namespaces/{tenant_namespace}/notification-targets/{notification_target_uuid}",
            headers=headers
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
        headers = client.default_headers
        headers.update({
            "Accept": "application/json",
            "Content-Type": "application/json"
        })

        logger.info(f"Creating notification target in namespace: {tenant_namespace}")

        # Create sanitized payload for debug logging (remove sensitive data)
        debug_payload = payload.model_dump()
        if 'spec' in debug_payload and 'action' in debug_payload['spec']:
            if 'jira_config' in debug_payload['spec']['action']:
                jira_config = debug_payload['spec']['action']['jira_config'].copy()
                if 'api_key' in jira_config:
                    jira_config['api_key'] = '<redacted>'
                if 'bearer_token' in jira_config:
                    jira_config['bearer_token'] = '<redacted>'
                debug_payload['spec']['action']['jira_config'] = jira_config

        logger.debug(f"Request data: {json.dumps(debug_payload, indent=2)}")

        res = client.post(
            f"v1/namespaces/{tenant_namespace}/notification-targets",
            headers=headers,
            data=payload.model_dump()
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
        headers = client.default_headers
        headers.update({
            "Accept": "application/json"
        })

        logger.info(f"Retrieving notification target: {notification_target_uuid}")

        res = client.get(
            f"v1/namespaces/{tenant_namespace}/notification-targets/{notification_target_uuid}",
            headers=headers
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

    output = []
    output.append("=" * 80)
    output.append("JIRA NOTIFICATION TARGET DETAILS")
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
    """Main function to create JIRA installation with command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Create JIRA installation using Endor Labs API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic JIRA integration with Basic Authentication
  python integrate_jira.py \\
    --tenant-namespace "endor-solutions-tgowan.cockpit" \\
    --name "Test JIRA notification" \\
    --description "Test Installation created by maneuver" \\
    --issue-type "VULN" \\
    --auth-method "basic" \\
    --project-key "CSJIT" \\
    --resolved-status "Done" \\
    --atlassian-username "tgowan@endor.ai" \\
    --atlassian-pat "$JIRA_BOARD_TEST_PAT"

  # Force overwrite existing installation
  python integrate_jira.py \\
    --tenant-namespace "endor-solutions-tgowan.cockpit" \\
    --name "Updated JIRA notification" \\
    --description "Updated Installation with force flag" \\
    --issue-type "VULN" \\
    --auth-method "basic" \\
    --project-key "CSJIT" \\
    --resolved-status "Done" \\
    --atlassian-username "tgowan@endor.ai" \\
    --atlassian-pat "$JIRA_BOARD_TEST_PAT" \\
    --force

  # JIRA integration with Bearer Token Authentication
  python integrate_jira.py \\
    --tenant-namespace "tenant.namespace" \\
    --name "JIRA Integration with Bearer Token" \\
    --description "JIRA integration using bearer token authentication" \\
    --issue-type "Bug" \\
    --auth-method "bearer" \\
    --project-key "PROJ" \\
    --resolved-status "Closed" \\
    --atlassian-username "user@company.com" \\
    --bearer-token "$JIRA_BEARER_TOKEN" \\
    --labels "security,vulnerability" \\
    --components "Security,Compliance"

  # JIRA integration with labels and components
  python integrate_jira.py \\
    --tenant-namespace "tenant.namespace" \\
    --name "Security JIRA Integration" \\
    --description "JIRA integration for security findings" \\
    --issue-type "Task" \\
    --auth-method "basic" \\
    --project-key "SEC" \\
    --resolved-status "Resolved" \\
    --atlassian-username "security@company.com" \\
    --atlassian-pat "$JIRA_SECURITY_PAT" \\
    --labels "security,automated,endor" \\
    --components "Security,DevOps" \\
    --tags "jira,security,automation"
        """
    )

    # Required arguments
    parser.add_argument(
        "--tenant-namespace",
        required=True,
        help="Tenant namespace (canonical name) where the installation will be created"
    )
    parser.add_argument(
        "--name",
        required=True,
        help="Installation name - descriptive identifier for the JIRA integration"
    )
    parser.add_argument(
        "--description",
        required=True,
        help="Installation description - explains the purpose and scope of the JIRA integration"
    )
    parser.add_argument(
        "--issue-type",
        required=True,
        help="JIRA issue type - the type of issues to create (e.g., VULN, Bug, Task, Story)"
    )
    parser.add_argument(
        "--auth-method",
        required=True,
        choices=["basic", "bearer"],
        help="Authentication method - 'basic' for username/API key or 'bearer' for bearer token"
    )
    parser.add_argument(
        "--project-key",
        required=True,
        help="JIRA project key - the project where issues will be created"
    )
    parser.add_argument(
        "--resolved-status",
        required=True,
        help="Resolved status - the final status when issues are resolved (e.g., Done, Closed, Resolved)"
    )
    parser.add_argument(
        "--atlassian-username",
        required=True,
        help="Atlassian username - the username for JIRA authentication"
    )

    # Authentication arguments (conditional)
    auth_group = parser.add_argument_group(
        "Authentication",
        "Authentication credentials (required based on auth-method)"
    )
    auth_group.add_argument(
        "--atlassian-pat",
        help="Atlassian Personal Access Token (PAT) - required for basic authentication"
    )
    auth_group.add_argument(
        "--bearer-token",
        help="Bearer token for authentication - required for bearer token authentication"
    )

    # JIRA Configuration arguments
    config_group = parser.add_argument_group(
        "JIRA Configuration",
        "JIRA-specific configuration options"
    )
    config_group.add_argument(
        "--jira-url",
        default="https://endorlabs.atlassian.net/",
        help="JIRA endpoint URL - the base URL of your JIRA instance (default: https://endorlabs.atlassian.net/)"
    )
    config_group.add_argument(
        "--labels",
        help="JIRA issue labels - comma-separated list of labels to apply to created issues"
    )
    config_group.add_argument(
        "--components",
        help="JIRA components - comma-separated list of components to assign to issues"
    )

    # Installation Configuration arguments
    install_group = parser.add_argument_group(
        "Installation Configuration",
        "Installation-specific configuration options"
    )
    install_group.add_argument(
        "--external-id",
        help="External ID - unique identifier for the JIRA integration (default: auto-generated)"
    )
    install_group.add_argument(
        "--public",
        action="store_true",
        help="Public flag - whether installation applies to public repositories"
    )
    install_group.add_argument(
        "--suspended",
        action="store_true",
        help="Suspended flag - whether the installation is suspended"
    )
    install_group.add_argument(
        "--include-archived-repos",
        action="store_true",
        help="Include archived repos - whether to include archived repositories"
    )

    # Optional arguments
    parser.add_argument(
        "--tags",
        help="Installation tags - comma-separated list of tags for categorization"
    )
    parser.add_argument(
        "--propagate",
        action="store_true",
        help="Enable propagation to child namespaces"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show the payload that would be sent without creating the installation"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force overwrite - delete existing installation with same external_id before creating new one"
    )

    args = parser.parse_args()

    # Set logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Validate authentication arguments
    if args.auth_method == "basic" and not args.atlassian_pat:
        parser.error("--atlassian-pat is required when using basic authentication")
    if args.auth_method == "bearer" and not args.bearer_token:
        parser.error("--bearer-token is required when using bearer token authentication")

    try:
        # Initialize API client
        logger.info("Initializing API client...")
        client = APIClient()

        # Parse arguments
        labels = parse_labels(args.labels) if args.labels else None
        components = parse_components(args.components) if args.components else None
        tags = parse_tags(args.tags) if args.tags else None

        # Create JIRA configuration
        jira_config = JIRAConfig(
            url=args.jira_url,
            user_name=args.atlassian_username,
            api_key=args.atlassian_pat if args.auth_method == "basic" else None,
            project_key=args.project_key,
            jira_issue_type=args.issue_type,
            resolve_state=args.resolved_status,
            use_bearer_token=(args.auth_method == "bearer"),
            bearer_token=args.bearer_token if args.auth_method == "bearer" else None,
            labels=labels,
            components=components
        )

        # Create notification target action
        action = NotificationTargetAction(
            action_type="ACTION_TYPE_JIRA",
            public=args.public,
            exclude_endor_url=args.exclude_endor_url if hasattr(args, 'exclude_endor_url') else False,
            jira_config=jira_config
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
            print("=== DRY RUN - JIRA Notification Target Payload ===")

            # Create sanitized payload for dry run (remove sensitive data)
            dry_run_payload = payload.model_dump()
            if 'spec' in dry_run_payload and 'action' in dry_run_payload['spec']:
                if 'jira_config' in dry_run_payload['spec']['action']:
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
                headers = client.default_headers
                headers.update({"Accept": "application/json"})
                res = client.get(f"v1/namespaces/{args.tenant_namespace}/notification-targets", headers=headers)
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
            print("=== JIRA Notification Target Created Successfully ===")
            print(f"UUID: {notification_target_uuid}")
            print(f"Name: {result.get('meta', {}).get('name', 'unknown')}")
            print(f"Namespace: {result.get('tenant_meta', {}).get('namespace', 'unknown')}")
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
            print("Failed to create JIRA notification target")
            sys.exit(1)

    except KeyboardInterrupt:
        logger.info("Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
