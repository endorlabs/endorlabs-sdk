#!/usr/bin/env python3
"""
Tag Findings Maneuver

A repeatable script for tagging security findings as false-positive using the Endor Labs API client.
This script searches for specific findings (e.g., secrets findings) and tags them with the
'false-positive' tag for subsequent policy-based suppression.

Based on the OpenAPI schema and finding resource structure.

Example:

uv run python maneuvers/tag_findings.py \
  --namespace "tenant.namespace" \
  --project-uuid "your-project-uuid" \
  --finding-categories "FINDING_CATEGORY_SECRETS" \
  --tag "false-positive" \
  --dry-run

## Note: This maneuver tags findings for subsequent exception policy creation.
"""

import argparse
import logging
import os
import sys
from typing import List, Optional

# Add the src directory to the path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from endor_cockpit.api_client import APIClient
from endor_cockpit.resources import finding, project
from endor_cockpit.types import ListParameters

# Import common utilities
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
from common.project_lookup import find_project_by_repository_url

# Configure logging to reduce verbosity
logging.getLogger('urllib3.connectionpool').setLevel(logging.WARNING)
logging.getLogger('endor_cockpit').setLevel(logging.INFO)

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_findings_by_criteria(
    client: APIClient,
    namespace: str,
    project_uuid: str,
    finding_categories: List[str],
    file_path: Optional[str] = None
) -> List:
    """
    Retrieve findings based on specified criteria.
    
    Args:
        client: Authenticated APIClient instance
        namespace: Target namespace
        project_uuid: Project UUID to filter findings
        finding_categories: List of finding categories to filter by
        file_path: Optional file path to filter by
        
    Returns:
        List of findings matching criteria
    """
    try:
        # Build filter expression
        filter_parts = [f'spec.project_uuid=="{project_uuid}"']
        
        if finding_categories:
            category_filter = " OR ".join([f'spec.finding_categories=="{cat}"' for cat in finding_categories])
            filter_parts.append(f"({category_filter})")
        
        if file_path:
            # Use dependency_file_paths array field for file path filtering
            filter_parts.append(f'spec.dependency_file_paths contains ["{file_path}"]')
        
        filter_expr = " AND ".join(filter_parts)
        
        list_params = ListParameters(
            filter=filter_expr,
            sort_field="spec.level",
            sort_order="desc"
        )
        
        findings = finding.list_findings(client, namespace, list_params)
        logger.info(f"Found {len(findings)} findings matching criteria")
        
        return findings
        
    except Exception as e:
        logger.error(f"Error retrieving findings: {e}")
        return []


def tag_finding(
    client: APIClient,
    namespace: str,
    finding_uuid: str,
    tag: str
) -> bool:
    """
    Tag a finding with the specified tag.
    
    Args:
        client: Authenticated APIClient instance
        namespace: Target namespace
        finding_uuid: UUID of the finding to tag
        tag: Tag to add to the finding
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Get current finding
        current_finding = finding.get_finding(client, namespace, finding_uuid)
        if not current_finding:
            logger.warning(f"Finding {finding_uuid} not found")
            return False

        # Update with new tag
        existing_tags = current_finding.meta.tags or []
        new_tags = [tag] + [t for t in existing_tags if t != tag]

        # Use raw API client to update tags
        request_data = {
            "object": {
                "uuid": finding_uuid,
                "tenant_meta": {"namespace": namespace},
                "meta": {"tags": new_tags},
            },
            "request": {"update_mask": "meta.tags"},
        }

        res = client.patch(
            f"v1/namespaces/{namespace}/findings",
            json=request_data,
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
        )
        
        if res.status_code == 200:
            logger.info(f"Successfully tagged finding {finding_uuid} with '{tag}'")
            return True
        else:
            logger.error(f"Failed to tag finding {finding_uuid}: {res.status_code}")
            return False

    except Exception as e:
        logger.error(f"Error tagging finding {finding_uuid}: {e}")
        return False


def main():
    """Main function to tag findings with command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Tag security findings as false-positive using Endor Labs API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Tag all secrets findings in a project
  python maneuvers/tag_findings.py \\
    --namespace "endor-solutions-tgowan" \\
    --project-uuid "your-project-uuid" \\
    --finding-categories "FINDING_CATEGORY_SECRETS" \\
    --tag "false-positive"

  # Tag findings in a specific file
  python maneuvers/tag_findings.py \\
    --namespace "endor-solutions-tgowan" \\
    --project-uuid "your-project-uuid" \\
    --finding-categories "FINDING_CATEGORY_SECRETS" \\
    --file-path "maneuvers/create_auth_policy.py" \\
    --tag "false-positive"

  # Find project by repository URL and tag findings
  python maneuvers/tag_findings.py \\
    --namespace "endor-solutions-tgowan" \\
    --repository-url "https://github.com/Endor-Solutions-Architecture/endor-cockpit" \\
    --finding-categories "FINDING_CATEGORY_SECRETS" \\
    --tag "false-positive"
        """
    )

    # Required arguments
    parser.add_argument(
        "--namespace",
        required=True,
        help="Target namespace where findings are located"
    )
    parser.add_argument(
        "--tag",
        required=True,
        help="Tag to add to findings (e.g., 'false-positive')"
    )

    # Finding identification (at least one required)
    identification_group = parser.add_argument_group(
        "Finding Identification",
        "Specify how to identify findings to tag (at least one required)"
    )
    identification_group.add_argument(
        "--project-uuid",
        help="Project UUID to filter findings by"
    )
    identification_group.add_argument(
        "--repository-url",
        help="Repository URL to find project and filter findings"
    )
    identification_group.add_argument(
        "--finding-categories",
        help="Comma-separated list of finding categories to filter by (e.g., 'FINDING_CATEGORY_SECRETS,FINDING_CATEGORY_SAST')"
    )
    identification_group.add_argument(
        "--file-path",
        help="Specific file path to filter findings by"
    )

    # Optional arguments
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be tagged without making changes"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )

    args = parser.parse_args()

    # Set logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Validate arguments
    if not args.project_uuid and not args.repository_url:
        parser.error("At least one of --project-uuid or --repository-url must be specified")

    if not args.finding_categories and not args.file_path:
        parser.error("At least one of --finding-categories or --file-path must be specified")

    try:
        # Initialize API client
        logger.info("Initializing API client...")
        client = APIClient()

        # Determine project UUID
        project_uuid = args.project_uuid
        if not project_uuid and args.repository_url:
            logger.info(f"Finding project for repository: {args.repository_url}")
            project_uuid = find_project_by_repository_url(client, args.namespace, args.repository_url)
            if not project_uuid:
                logger.error(f"Could not find project for repository: {args.repository_url}")
                sys.exit(1)

        # Parse finding categories
        finding_categories = []
        if args.finding_categories:
            finding_categories = [cat.strip() for cat in args.finding_categories.split(',')]

        # Get findings
        logger.info("Retrieving findings...")
        findings = get_findings_by_criteria(
            client=client,
            namespace=args.namespace,
            project_uuid=project_uuid,
            finding_categories=finding_categories,
            file_path=args.file_path
        )

        if not findings:
            logger.info("No findings found matching criteria")
            return

        logger.info(f"Found {len(findings)} findings to tag")

        if args.dry_run:
            print("=== DRY RUN - Findings that would be tagged ===")
            for i, finding_obj in enumerate(findings, 1):
                print(f"{i}. {finding_obj.meta.name}")
                print(f"   UUID: {finding_obj.uuid}")
                print(f"   Level: {finding_obj.spec.level}")
                print(f"   Categories: {finding_obj.spec.finding_categories}")
                if hasattr(finding_obj.spec, 'file_path') and finding_obj.spec.file_path:
                    print(f"   File: {finding_obj.spec.file_path}")
                print()
            return

        # Tag findings
        tagged_count = 0
        for finding_obj in findings:
            if tag_finding(client, args.namespace, finding_obj.uuid, args.tag):
                tagged_count += 1

        logger.info(f"Successfully tagged {tagged_count} out of {len(findings)} findings")

        if tagged_count == len(findings):
            print(f"✅ Successfully tagged all {len(findings)} findings with '{args.tag}'")
        else:
            print(f"⚠️  Tagged {tagged_count} out of {len(findings)} findings")
            sys.exit(1)

    except KeyboardInterrupt:
        logger.info("Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
