#!/usr/bin/env python3
"""
Test Policy Cleanup Maneuver

A repeatable script for cleaning up test policies in the Endor Labs platform.
This script identifies and deletes all policies that contain "test" and "dummy" tags
in the specified namespace, with comprehensive safety features and confirmation.

Based on the policy resource structure and API patterns.

Example:

uv run python maneuvers/cleanup_test_policies.py \
  --tenant-namespace "endor-solutions-tgowan.cockpit" \
  --dry-run

uv run python maneuvers/cleanup_test_policies.py \
  --tenant-namespace "endor-solutions-tgowan.cockpit" \
  --confirm-delete

## Note: This script will delete ALL policies with "test" and "dummy" tags.
## Use --dry-run first to see what would be deleted.
"""

import argparse
import logging
import os
import sys
from typing import Any, Dict, List

# Add the src directory to the path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from endor_cockpit.api_client import APIClient
from endor_cockpit.resources.policy import (
    Policy,
    delete_policy,
    list_policies,
)
from endor_cockpit.types import ListParameters

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def find_test_policies(
    client: APIClient,
    tenant_namespace: str,
    include_child_namespaces: bool = True
) -> List[Policy]:
    """
    Find all policies with "test" and "dummy" tags in the specified namespace.

    Args:
        client: Authenticated APIClient instance
        tenant_namespace: Target tenant namespace (canonical name)
        include_child_namespaces: Whether to include child namespaces

    Returns:
        List of policies matching the criteria
    """
    try:
        logger.info(f"Searching for test policies in namespace: {tenant_namespace}")

        # Create filter for policies with test and dummy tags
        # Using OR logic to find policies that have either "test" OR "dummy" tags
        filter_expression = "meta.tags in ['test', 'dummy']"

        list_params = ListParameters(
            filter=filter_expression,
            mask="uuid,meta.name,meta.tags,meta.create_time,tenant_meta.namespace",
            page_size=100,
            page_token=None,
            sort_field="meta.create_time",
            sort_order="desc",
            count=None,
            include_child_namespaces=include_child_namespaces,
            from_date=None,
            to_date=None,
        )

        policies = list_policies(client, tenant_namespace, list_params=list_params)

        # Additional filtering to ensure we only get policies with BOTH test AND dummy tags
        test_policies = []
        for policy in policies:
            tags = policy.meta.tags or []
            if "test" in tags and "dummy" in tags:
                test_policies.append(policy)

        logger.info(f"Found {len(test_policies)} policies with both 'test' and 'dummy' tags")
        return test_policies

    except Exception as e:
        logger.error(f"Error finding test policies: {e}", exc_info=True)
        return []


def format_policy_summary(policy: Policy) -> str:
    """
    Format a policy for display in the summary.

    Args:
        policy: Policy object to format

    Returns:
        Formatted string for display
    """
    tags = ", ".join(policy.meta.tags or [])
    namespace = policy.tenant_meta.namespace if policy.tenant_meta else "unknown"

    return (
        f"  • {policy.meta.name} (UUID: {policy.uuid})\n"
        f"    Namespace: {namespace}\n"
        f"    Tags: {tags}\n"
        f"    Created: {policy.meta.create_time}"
    )


def display_policy_summary(policies: List[Policy]) -> None:
    """
    Display a summary of policies that will be deleted.

    Args:
        policies: List of policies to display
    """
    if not policies:
        print("No test policies found.")
        return

    print("=" * 80)
    print("POLICIES TO BE DELETED")
    print("=" * 80)
    print(f"Total policies: {len(policies)}")
    print()

    for i, policy in enumerate(policies, 1):
        print(f"{i}. {format_policy_summary(policy)}")
        print()

    print("=" * 80)


def delete_policies_batch(
    client: APIClient,
    tenant_namespace: str,
    policies: List[Policy],
    dry_run: bool = False
) -> Dict[str, Any]:
    """
    Delete a batch of policies with comprehensive error handling.

    Args:
        client: Authenticated APIClient instance
        tenant_namespace: Target tenant namespace
        policies: List of policies to delete
        dry_run: If True, don't actually delete

    Returns:
        Dictionary with deletion results
    """
    results = {
        "total": len(policies),
        "successful": 0,
        "failed": 0,
        "errors": []
    }

    if dry_run:
        logger.info("DRY RUN: Would delete the following policies:")
        for policy in policies:
            logger.info(f"  - {policy.meta.name} (UUID: {policy.uuid})")
        results["successful"] = len(policies)
        return results

    logger.info(f"Starting deletion of {len(policies)} policies...")

    for i, policy in enumerate(policies, 1):
        try:
            logger.info(f"Deleting policy {i}/{len(policies)}: {policy.meta.name}")

            # Determine the correct namespace for deletion
            policy_namespace = policy.tenant_meta.namespace if policy.tenant_meta else tenant_namespace

            success = delete_policy(client, policy_namespace, policy.uuid)

            if success:
                results["successful"] += 1
                logger.info(f"Successfully deleted policy: {policy.meta.name}")
            else:
                results["failed"] += 1
                error_msg = f"Failed to delete policy: {policy.meta.name} (UUID: {policy.uuid})"
                results["errors"].append(error_msg)
                logger.error(error_msg)

        except Exception as e:
            results["failed"] += 1
            error_msg = f"Error deleting policy {policy.meta.name}: {e}"
            results["errors"].append(error_msg)
            logger.error(error_msg, exc_info=True)

    return results


def display_deletion_results(results: Dict[str, Any]) -> None:
    """
    Display the results of the deletion operation.

    Args:
        results: Dictionary with deletion results
    """
    print("=" * 80)
    print("DELETION RESULTS")
    print("=" * 80)
    print(f"Total policies processed: {results['total']}")
    print(f"Successfully deleted: {results['successful']}")
    print(f"Failed to delete: {results['failed']}")

    if results["errors"]:
        print("\nErrors encountered:")
        for error in results["errors"]:
            print(f"  • {error}")

    print("=" * 80)


def confirm_deletion(policies: List[Policy]) -> bool:
    """
    Ask user for confirmation before deletion.

    Args:
        policies: List of policies that will be deleted

    Returns:
        True if user confirms, False otherwise
    """
    if not policies:
        return False

    print(f"\n⚠️  WARNING: You are about to delete {len(policies)} policies!")
    print("This action cannot be undone.")
    print("\nPolicies to be deleted:")

    for i, policy in enumerate(policies[:5], 1):  # Show first 5
        print(f"  {i}. {policy.meta.name} (UUID: {policy.uuid})")

    if len(policies) > 5:
        print(f"  ... and {len(policies) - 5} more policies")

    print()
    response = input("Are you sure you want to proceed? Type 'DELETE' to confirm: ")
    return response.strip() == "DELETE"


def main():
    """Main function to handle command line arguments and execute cleanup."""
    parser = argparse.ArgumentParser(
        description="Clean up test policies with 'test' and 'dummy' tags",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:

# Dry run to see what would be deleted
uv run python maneuvers/cleanup_test_policies.py \\
  --tenant-namespace "endor-solutions-tgowan.cockpit" \\
  --dry-run

# Delete with confirmation prompt
uv run python maneuvers/cleanup_test_policies.py \\
  --tenant-namespace "endor-solutions-tgowan.cockpit"

# Delete without confirmation (use with caution)
uv run python maneuvers/cleanup_test_policies.py \\
  --tenant-namespace "endor-solutions-tgowan.cockpit" \\
  --confirm-delete

# Include child namespaces in search
uv run python maneuvers/cleanup_test_policies.py \\
  --tenant-namespace "endor-solutions-tgowan.cockpit" \\
  --include-child-namespaces \\
  --dry-run
        """
    )

    # Required arguments
    parser.add_argument(
        "--tenant-namespace",
        required=True,
        help="Tenant namespace (canonical name) to clean up"
    )

    # Optional arguments
    parser.add_argument(
        "--include-child-namespaces",
        action="store_true",
        help="Include child namespaces in the search (default: True)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be deleted without actually deleting"
    )
    parser.add_argument(
        "--confirm-delete",
        action="store_true",
        help="Skip confirmation prompt and proceed with deletion (use with caution)"
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

    try:
        # Initialize API client
        logger.info("Initializing API client...")
        client = APIClient()

        # Find test policies
        logger.info("Searching for test policies...")
        test_policies = find_test_policies(
            client,
            args.tenant_namespace,
            args.include_child_namespaces
        )

        if not test_policies:
            print("No test policies found with both 'test' and 'dummy' tags.")
            return

        # Display summary
        display_policy_summary(test_policies)

        if args.dry_run:
            print("\n🔍 DRY RUN: No policies were actually deleted.")
            return

        # Confirmation
        if not args.confirm_delete:
            if not confirm_deletion(test_policies):
                print("Operation cancelled by user.")
                return

        # Delete policies
        logger.info("Proceeding with deletion...")
        results = delete_policies_batch(
            client,
            args.tenant_namespace,
            test_policies,
            dry_run=False
        )

        # Display results
        display_deletion_results(results)

        if results["failed"] > 0:
            print(f"\n⚠️  {results['failed']} policies failed to delete. Check the errors above.")
            sys.exit(1)
        else:
            print(f"\n✅ Successfully deleted {results['successful']} test policies.")

    except KeyboardInterrupt:
        logger.info("Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
