#!/usr/bin/env python3
"""
Installation Creation Maneuver

A repeatable script for creating installations using the Endor Labs API client.
This script provides parameterized inputs for creating GitHub installations with
proper configuration and feature settings.

Based on the OpenAPI schema and installation resource structure.

Example:

uv run python maneuvers/create_installation.py \
  --tenant-namespace "${ENDOR_NAMESPACE}" \
  --name "GitHub Endor Pro App - kessel" \
  --external-id "91278704" \
  --github-app-id "977385" \
  --github-user "tgowan-endor" \
  --target-user "tgowan@endor.ai@google" \
  --enable-sast \
  --enable-pr-comments \
  --dry-run

## Note: Installations connect external platforms (GitHub, GitLab, etc.) to Endor Labs for scanning.
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
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger('endorlabs').setLevel(logging.INFO)

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class InstallationMeta(BaseModel):
    """Metadata for installation creation."""

    name: str = Field(..., description="Installation name - descriptive identifier for the installation")
    kind: str = Field(default="Installation", description="Resource kind - always 'Installation' for installations")
    version: str = Field(default="v1", description="Resource version")


class GitHubConfig(BaseModel):
    """GitHub configuration for installation."""

    app_id: str = Field(..., description="GitHub App ID - the GitHub App identifier")
    enable_full_scan: bool = Field(default=False, description="Enable full scan - whether to perform full repository scans")
    enable_pr_comments: bool = Field(default=True, description="Enable PR comments - whether to post comments on pull requests")
    enable_pr_scans: bool = Field(default=True, description="Enable PR scans - whether to scan pull requests")
    include_archived_repos: bool = Field(default=False, description="Include archived repos - whether to scan archived repositories")
    installation_github_user: str = Field(..., description="GitHub user - the GitHub username for the installation")


class InstallationSpec(BaseModel):
    """Specification for installation creation."""

    external_id: str = Field(..., description="External ID - unique identifier from the external platform")
    platform_type: str = Field(default="PLATFORM_SOURCE_GITHUB", description="Platform type - the type of external platform")
    target_type: str = Field(default="User", description="Target type - the type of target (User, Organization)")
    user: str = Field(..., description="Target user - the user who owns this installation")
    login: str = Field(..., description="Login - the login identifier for the installation")
    github_config: GitHubConfig = Field(..., description="GitHub configuration - GitHub-specific settings")
    enabled_features: List[str] = Field(..., description="Enabled features - list of features to enable for this installation")
    project_uuids: Optional[List[str]] = Field(None, description="Project UUIDs - list of project UUIDs to associate with this installation")
    ingestion_time: Optional[str] = Field(None, description="Ingestion time - when the installation was ingested")
    invalid: bool = Field(default=False, description="Invalid flag - whether the installation is invalid")


class CreateInstallationPayload(BaseModel):
    """Complete payload for creating an installation."""

    meta: InstallationMeta = Field(..., description="Installation metadata - name and other metadata")
    spec: InstallationSpec = Field(..., description="Installation specification - platform configuration and settings")


def delete_installation(
    client: APIClient,
    tenant_namespace: str,
    installation_uuid: str
) -> bool:
    """
    Delete an installation by UUID.

    Args:
        client: API client instance
        tenant_namespace: Tenant namespace
        installation_uuid: Installation UUID to delete

    Returns:
        True if deletion successful, False otherwise
    """
    try:
        logger.info(f"Deleting installation: {installation_uuid}")

        res = client.delete(
            f"v1/namespaces/{tenant_namespace}/installations/{installation_uuid}"
        )

        if res.status_code == 200:
            logger.info(f"Successfully deleted installation: {installation_uuid}")
            return True
        else:
            logger.error(f"Failed to delete installation: {res.status_code} - {res.text}")
            return False

    except Exception as e:
        logger.error(f"Error deleting installation: {e}", exc_info=True)
        return False


def create_installation(
    client: APIClient,
    tenant_namespace: str,
    payload: CreateInstallationPayload
) -> Optional[Dict[str, Any]]:
    """
    Create an installation using the API client.

    Args:
        client: API client instance
        tenant_namespace: Parent namespace (e.g., "tenant.namespace")
        payload: Installation creation payload

    Returns:
        Created installation data or None if creation failed
    """
    try:
        logger.info(f"Creating installation in namespace: {tenant_namespace}")

        # Create sanitized payload for debug logging (remove sensitive data)
        debug_payload = payload.model_dump()
        logger.debug(f"Request data: {json.dumps(debug_payload, indent=2)}")

        res = client.post(
            f"v1/namespaces/{tenant_namespace}/installations",
            json=payload.model_dump(),
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
        )

        if res.status_code == 200:
            data = res.json()
            logger.info(f"Successfully created installation: {data.get('uuid', 'unknown')}")
            return data
        else:
            logger.error(f"Failed to create installation: {res.status_code} - {res.text}")
            return None

    except Exception as e:
        logger.error(f"Error creating installation: {e}", exc_info=True)
        return None


def get_installation(
    client: APIClient,
    tenant_namespace: str,
    installation_uuid: str
) -> Optional[Dict[str, Any]]:
    """
    Retrieve an installation by UUID.

    Args:
        client: API client instance
        tenant_namespace: Tenant namespace
        installation_uuid: Installation UUID

    Returns:
        Installation data or None if retrieval failed
    """
    try:
        logger.info(f"Retrieving installation: {installation_uuid}")

        res = client.get(
            f"v1/namespaces/{tenant_namespace}/installations/{installation_uuid}"
        )

        if res.status_code == 200:
            data = res.json()
            logger.info(f"Successfully retrieved installation: {installation_uuid}")
            return data
        else:
            logger.error(f"Failed to retrieve installation: {res.status_code} - {res.text}")
            return None

    except Exception as e:
        logger.error(f"Error retrieving installation: {e}", exc_info=True)
        return None


def format_installation_for_display(installation_data: Dict[str, Any]) -> str:
    """
    Format installation data for human-readable display.

    Args:
        installation_data: Installation data from API

    Returns:
        Formatted string for display
    """
    if not installation_data:
        return "No installation data available"

    meta = installation_data.get('meta', {})
    spec = installation_data.get('spec', {})
    tenant_meta = installation_data.get('tenant_meta', {})
    processing_status = installation_data.get('processing_status', {})
    github_config = spec.get('github_config', {})

    output = []
    output.append("=" * 80)
    output.append("INSTALLATION DETAILS")
    output.append("=" * 80)

    # Basic Information
    output.append(f"UUID: {installation_data.get('uuid', 'N/A')}")
    output.append(f"Name: {meta.get('name', 'N/A')}")
    output.append(f"Kind: {meta.get('kind', 'N/A')}")
    output.append(f"Version: {meta.get('version', 'N/A')}")
    output.append(f"Namespace: {tenant_meta.get('namespace', 'N/A')}")
    output.append("")

    # Timestamps
    output.append("TIMESTAMPS:")
    output.append("-" * 40)
    output.append(f"Created: {meta.get('create_time', 'N/A')}")
    output.append(f"Created By: {meta.get('created_by', 'N/A')}")
    output.append(f"Updated: {meta.get('update_time', 'N/A')}")
    output.append(f"Updated By: {meta.get('updated_by', 'N/A')}")
    if meta.get('upsert_time'):
        output.append(f"Upsert Time: {meta.get('upsert_time', 'N/A')}")
    output.append("")

    # Installation Configuration
    output.append("INSTALLATION CONFIGURATION:")
    output.append("-" * 40)
    output.append(f"External ID: {spec.get('external_id', 'N/A')}")
    output.append(f"Platform Type: {spec.get('platform_type', 'N/A')}")
    output.append(f"Target Type: {spec.get('target_type', 'N/A')}")
    output.append(f"User: {spec.get('user', 'N/A')}")
    output.append(f"Login: {spec.get('login', 'N/A')}")
    output.append(f"Invalid: {spec.get('invalid', 'N/A')}")
    if spec.get('ingestion_time'):
        output.append(f"Ingestion Time: {spec.get('ingestion_time', 'N/A')}")
    output.append("")

    # GitHub Configuration
    output.append("GITHUB CONFIGURATION:")
    output.append("-" * 40)
    output.append(f"App ID: {github_config.get('app_id', 'N/A')}")
    output.append(f"GitHub User: {github_config.get('installation_github_user', 'N/A')}")
    output.append(f"Enable Full Scan: {github_config.get('enable_full_scan', 'N/A')}")
    output.append(f"Enable PR Comments: {github_config.get('enable_pr_comments', 'N/A')}")
    output.append(f"Enable PR Scans: {github_config.get('enable_pr_scans', 'N/A')}")
    output.append(f"Include Archived Repos: {github_config.get('include_archived_repos', 'N/A')}")
    output.append("")

    # Enabled Features
    output.append("ENABLED FEATURES:")
    output.append("-" * 40)
    for feature in spec.get('enabled_features', []):
        output.append(f"  • {feature}")
    output.append("")

    # Processing Status
    if processing_status:
        output.append("PROCESSING STATUS:")
        output.append("-" * 40)
        output.append(f"Scan State: {processing_status.get('scan_state', 'N/A')}")
        output.append(f"Disable Automated Scan: {processing_status.get('disable_automated_scan', 'N/A')}")
        if processing_status.get('queue_time'):
            output.append(f"Queue Time: {processing_status.get('queue_time', 'N/A')}")
        if processing_status.get('scan_time'):
            output.append(f"Scan Time: {processing_status.get('scan_time', 'N/A')}")
        output.append("")

    # Project UUIDs
    if spec.get('project_uuids'):
        output.append("PROJECT UUIDs:")
        output.append("-" * 40)
        for project_uuid in spec.get('project_uuids', []):
            output.append(f"  • {project_uuid}")
        output.append("")

    output.append("=" * 80)

    return "\n".join(output)


def parse_features(features_str: str) -> List[str]:
    """Parse comma-separated features string into list."""
    return [feature.strip() for feature in features_str.split(',') if feature.strip()]


def parse_project_uuids(uuids_str: str) -> List[str]:
    """Parse comma-separated project UUIDs string into list."""
    return [uuid.strip() for uuid in uuids_str.split(',') if uuid.strip()]


def main():
    """Main function to create installation with command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Create installation using Endor Labs API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic GitHub installation
  python create_installation.py \\
    --tenant-namespace "${ENDOR_NAMESPACE}" \\
    --name "GitHub Endor Pro App" \\
    --external-id "91278704" \\
    --github-app-id "977385" \\
    --github-user "tgowan-endor" \\
    --target-user "tgowan@endor.ai@google" \\
    --enable-sast \\
    --enable-pr-comments

  # Full-featured installation
  python create_installation.py \\
    --tenant-namespace "tenant.namespace" \\
    --name "GitHub Installation" \\
    --external-id "12345678" \\
    --github-app-id "123456" \\
    --github-user "company-user" \\
    --target-user "user@company.com@google" \\
    --features "ENABLED_FEATURE_TYPE_GIT_SCAN,ENABLED_FEATURE_TYPE_GITHUB_SCAN,ENABLED_FEATURE_TYPE_SAST_SCAN" \\
    --enable-full-scan \\
    --enable-pr-comments \\
    --enable-pr-scans \\
    --include-archived-repos

  # Installation with specific projects
  python create_installation.py \\
    --tenant-namespace "tenant.namespace" \\
    --name "Project-Specific Installation" \\
    --external-id "87654321" \\
    --github-app-id "654321" \\
    --github-user "project-user" \\
    --target-user "admin@company.com@google" \\
    --project-uuids "68fa34e780f75bc158af8a54,68fa34e795ce93fa2d5c7d65" \\
    --enable-sast \\
    --enable-pr-comments
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
        help="Installation name - descriptive identifier for the installation"
    )
    parser.add_argument(
        "--external-id",
        required=True,
        help="External ID - unique identifier from the external platform (e.g., GitHub installation ID)"
    )
    parser.add_argument(
        "--github-app-id",
        required=True,
        help="GitHub App ID - the GitHub App identifier"
    )
    parser.add_argument(
        "--github-user",
        required=True,
        help="GitHub user - the GitHub username for the installation"
    )
    parser.add_argument(
        "--target-user",
        required=True,
        help="Target user - the user who owns this installation (e.g., 'user@company.com@google')"
    )

    # Feature flags
    feature_group = parser.add_argument_group(
        "Feature Configuration",
        "Configure which features to enable for the installation"
    )
    feature_group.add_argument(
        "--features",
        help="Enabled features - comma-separated list of features (e.g., 'ENABLED_FEATURE_TYPE_GIT_SCAN,ENABLED_FEATURE_TYPE_SAST_SCAN')"
    )
    feature_group.add_argument(
        "--enable-sast",
        action="store_true",
        help="Enable SAST scan feature (ENABLED_FEATURE_TYPE_SAST_SCAN)"
    )
    feature_group.add_argument(
        "--enable-git-scan",
        action="store_true",
        help="Enable Git scan feature (ENABLED_FEATURE_TYPE_GIT_SCAN)"
    )
    feature_group.add_argument(
        "--enable-github-scan",
        action="store_true",
        help="Enable GitHub scan feature (ENABLED_FEATURE_TYPE_GITHUB_SCAN)"
    )
    feature_group.add_argument(
        "--enable-secrets-scan",
        action="store_true",
        help="Enable secrets scan feature (ENABLED_FEATURE_TYPE_SECRETS_SCAN)"
    )
    feature_group.add_argument(
        "--enable-tools-scan",
        action="store_true",
        help="Enable tools scan feature (ENABLED_FEATURE_TYPE_TOOLS_SCAN)"
    )
    feature_group.add_argument(
        "--enable-github-action-scan",
        action="store_true",
        help="Enable GitHub Action scan feature (ENABLED_FEATURE_TYPE_GITHUB_ACTION_SCAN)"
    )

    # GitHub Configuration
    github_group = parser.add_argument_group(
        "GitHub Configuration",
        "GitHub-specific configuration options"
    )
    github_group.add_argument(
        "--enable-full-scan",
        action="store_true",
        help="Enable full scan - whether to perform full repository scans"
    )
    github_group.add_argument(
        "--enable-pr-comments",
        action="store_true",
        default=True,
        help="Enable PR comments - whether to post comments on pull requests (default: True)"
    )
    github_group.add_argument(
        "--enable-pr-scans",
        action="store_true",
        default=True,
        help="Enable PR scans - whether to scan pull requests (default: True)"
    )
    github_group.add_argument(
        "--include-archived-repos",
        action="store_true",
        help="Include archived repos - whether to scan archived repositories"
    )

    # Optional arguments
    parser.add_argument(
        "--project-uuids",
        help="Project UUIDs - comma-separated list of project UUIDs to associate with this installation"
    )
    parser.add_argument(
        "--platform-type",
        default="PLATFORM_SOURCE_GITHUB",
        help="Platform type - the type of external platform (default: PLATFORM_SOURCE_GITHUB)"
    )
    parser.add_argument(
        "--target-type",
        default="User",
        help="Target type - the type of target (default: User)"
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

    try:
        # Initialize API client
        logger.info("Initializing API client...")
        client = APIClient()

        # Build enabled features list
        enabled_features = []

        # Add features from --features argument
        if args.features:
            enabled_features.extend(parse_features(args.features))

        # Add features from individual flags
        if args.enable_sast:
            enabled_features.append("ENABLED_FEATURE_TYPE_SAST_SCAN")
        if args.enable_git_scan:
            enabled_features.append("ENABLED_FEATURE_TYPE_GIT_SCAN")
        if args.enable_github_scan:
            enabled_features.append("ENABLED_FEATURE_TYPE_GITHUB_SCAN")
        if args.enable_secrets_scan:
            enabled_features.append("ENABLED_FEATURE_TYPE_SECRETS_SCAN")
        if args.enable_tools_scan:
            enabled_features.append("ENABLED_FEATURE_TYPE_TOOLS_SCAN")
        if args.enable_github_action_scan:
            enabled_features.append("ENABLED_FEATURE_TYPE_GITHUB_ACTION_SCAN")

        # If no features specified, use default set
        if not enabled_features:
            enabled_features = [
                "ENABLED_FEATURE_TYPE_GIT_SCAN",
                "ENABLED_FEATURE_TYPE_GITHUB_SCAN",
                "ENABLED_FEATURE_TYPE_SECRETS_SCAN",
                "ENABLED_FEATURE_TYPE_TOOLS_SCAN",
                "ENABLED_FEATURE_TYPE_SAST_SCAN",
                "ENABLED_FEATURE_TYPE_GITHUB_ACTION_SCAN"
            ]

        # Parse project UUIDs
        project_uuids = parse_project_uuids(args.project_uuids) if args.project_uuids else None

        # Create GitHub configuration
        github_config = GitHubConfig(
            app_id=args.github_app_id,
            enable_full_scan=args.enable_full_scan,
            enable_pr_comments=args.enable_pr_comments,
            enable_pr_scans=args.enable_pr_scans,
            include_archived_repos=args.include_archived_repos,
            installation_github_user=args.github_user
        )

        # Create installation spec
        spec = InstallationSpec(
            external_id=args.external_id,
            platform_type=args.platform_type,
            target_type=args.target_type,
            user=args.target_user,
            login=args.github_user,
            github_config=github_config,
            enabled_features=enabled_features,
            project_uuids=project_uuids
        )

        # Create meta object
        meta = InstallationMeta(
            name=args.name
        )

        # Create payload
        payload = CreateInstallationPayload(
            meta=meta,
            spec=spec
        )

        if args.dry_run:
            print("=== DRY RUN - Installation Creation Payload ===")
            print(json.dumps(payload.model_dump(), indent=2))
            return

        # Handle force flag - delete existing installation with same external_id
        if args.force:
            logger.info(f"Force flag enabled - checking for existing installation with external_id: {args.external_id}")
            try:
                res = client.get(f"v1/namespaces/{args.tenant_namespace}/installations")
                if res.status_code == 200:
                    data = res.json()
                    installations = data.get('list', {}).get('objects', [])
                    for installation in installations:
                        if installation.get('spec', {}).get('external_id') == args.external_id:
                            existing_uuid = installation.get('uuid')
                            logger.info(f"Found existing installation with external_id '{args.external_id}': {existing_uuid}")
                            if delete_installation(client, args.tenant_namespace, existing_uuid):
                                logger.info(f"Successfully deleted existing installation: {existing_uuid}")
                            else:
                                logger.warning(f"Failed to delete existing installation: {existing_uuid}")
                            break
                    else:
                        logger.info(f"No existing installation found with external_id: {args.external_id}")
                else:
                    logger.warning(f"Failed to list installations: {res.status_code} - {res.text}")
            except Exception as e:
                logger.warning(f"Error checking for existing installations: {e}")

        # Create the installation
        result = create_installation(client, args.tenant_namespace, payload)

        if result:
            installation_uuid = result.get('uuid')
            print("=== Installation Created Successfully ===")
            print(f"UUID: {installation_uuid}")
            print(f"Name: {result.get('meta', {}).get('name', 'unknown')}")
            print(f"Namespace: {result.get('tenant_meta', {}).get('namespace', 'unknown')}")
            print(f"Created: {result.get('meta', {}).get('create_time', 'unknown')}")

            # Retrieve the installation and display in human-readable format
            if installation_uuid:
                print("\n" + "=" * 80)
                print("RETRIEVING INSTALLATION DETAILS...")
                print("=" * 80)

                retrieved_installation = get_installation(client, args.tenant_namespace, installation_uuid)
                if retrieved_installation:
                    print("\n" + format_installation_for_display(retrieved_installation))
                else:
                    print("Failed to retrieve installation details after creation")
            else:
                print("Warning: No UUID returned from installation creation")
        else:
            print("Failed to create installation")
            sys.exit(1)

    except KeyboardInterrupt:
        logger.info("Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()

