#!/usr/bin/env python3
"""
Dependency Visibility Check - Efficient Approach

Uses DependencyMetadata directly with traverse to efficiently check
all dependencies across all namespaces for public/private visibility.

This is much faster than iterating through PackageVersions because:
1. DependencyMetadata is already normalized and indexed
2. --traverse automatically handles all namespaces
3. Direct query on the relationship resource

Example:
    uv run python maneuvers/check_dependency_visibility.py
"""

import argparse
import json
import logging
import os
import sys
from collections import defaultdict
from typing import Any, Dict, List, Optional

# Add the src directory to the path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from endor_cockpit.api_client import APIClient
from endor_cockpit.resources import dependency_metadata
from endor_cockpit.types import ListParameters
from endor_cockpit.utils.traversal import create_traverse_params

# Configure logging
logging.getLogger("urllib3.connectionpool").setLevel(logging.WARNING)
logging.getLogger("endor_cockpit").setLevel(logging.INFO)

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def check_dependency_visibility(
    client: APIClient,
    tenant_namespace: str,
    filter_public: Optional[bool] = None,
) -> Dict[str, Any]:
    """
    Efficiently check dependency visibility using DependencyMetadata with traverse.

    Args:
        client: Authenticated APIClient
        tenant_namespace: Root tenant namespace
        filter_public: If True, only return public deps. If False, only private. If None, all.

    Returns:
        Dictionary with statistics and findings
    """
    logger.info(
        f"Querying DependencyMetadata with traverse from: {tenant_namespace}"
    )

    # Use canonical traverse pattern for tenant-wide query
    # This automatically queries all namespaces in a single efficient API call
    # Note: No page_size override - uses API default (typically 100)
    #       max_pages controls the upper bound instead
    filter_expr = None
    if filter_public is not None:
        filter_expr = (
            f"spec.dependency_data.public=={str(filter_public).lower()}"
        )
    
    list_params = create_traverse_params(filter_expr=filter_expr)

    try:
        # Query all DependencyMetadata with traverse
        all_deps = dependency_metadata.list_dependency_metadata(
            client, tenant_namespace, list_params
        )

        logger.info(f"Found {len(all_deps)} DependencyMetadata objects")

        # Analyze results
        stats = {
            "total": len(all_deps),
            "with_public_field": 0,
            "public_deps": 0,
            "private_deps": 0,
            "unknown_visibility": 0,
            "by_namespace": defaultdict(int),
            "by_ecosystem": defaultdict(int),
            "sample_public": [],
            "sample_private": [],
        }

        for dep in all_deps:
            # Get namespace
            namespace = (
                dep.tenant_meta.namespace
                if dep.tenant_meta and dep.tenant_meta.namespace
                else "unknown"
            )
            stats["by_namespace"][namespace] += 1

            # Check dependency_data
            if dep.spec and dep.spec.dependency_data:
                dep_data = dep.spec.dependency_data
                dep_dict = dep_data.model_dump() if hasattr(dep_data, "model_dump") else {}

                # Check for public field
                public_value = dep_dict.get("public")
                if public_value is not None:
                    stats["with_public_field"] += 1
                    if public_value is True:
                        stats["public_deps"] += 1
                        if len(stats["sample_public"]) < 5:
                            stats["sample_public"].append({
                                "importer": (
                                    dep.spec.importer_data.package_name
                                    if dep.spec.importer_data
                                    else "unknown"
                                ),
                                "dependency": dep_data.package_name,
                                "namespace": namespace,
                                "ecosystem": (
                                    dep_data.ecosystem.value
                                    if dep_data.ecosystem
                                    else "unknown"
                                ),
                            })
                    elif public_value is False:
                        stats["private_deps"] += 1
                        if len(stats["sample_private"]) < 5:
                            stats["sample_private"].append({
                                "importer": (
                                    dep.spec.importer_data.package_name
                                    if dep.spec.importer_data
                                    else "unknown"
                                ),
                                "dependency": dep_data.package_name,
                                "namespace": namespace,
                                "ecosystem": (
                                    dep_data.ecosystem.value
                                    if dep_data.ecosystem
                                    else "unknown"
                                ),
                            })
                else:
                    stats["unknown_visibility"] += 1

                # Track ecosystem
                if dep_data.ecosystem:
                    ecosystem = dep_data.ecosystem.value
                    stats["by_ecosystem"][ecosystem] += 1

        return {
            "status": "success",
            "stats": stats,
        }

    except Exception as e:
        logger.error(f"Error querying DependencyMetadata: {e}")
        return {
            "status": "error",
            "error": str(e),
            "stats": {},
        }


def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(
        description="Efficiently check dependency visibility using DependencyMetadata"
    )
    parser.add_argument(
        "--tenant-namespace",
        type=str,
        default=os.getenv("ENDOR_NAMESPACE"),
        help="Root tenant namespace (default: ENDOR_NAMESPACE env var)",
    )
    parser.add_argument(
        "--filter-public",
        type=str,
        choices=["true", "false", "all"],
        default="all",
        help="Filter by visibility: true (public only), false (private only), all (default)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Output file for JSON results (default: stdout)",
    )

    args = parser.parse_args()

    if not args.tenant_namespace:
        logger.error(
            "Tenant namespace is required. Provide --tenant-namespace or set "
            "ENDOR_NAMESPACE environment variable."
        )
        sys.exit(1)

    # Initialize client
    try:
        client = APIClient()
    except ValueError as e:
        logger.error(f"Failed to initialize API client: {e}")
        sys.exit(1)

    # Parse filter
    filter_public = None
    if args.filter_public == "true":
        filter_public = True
    elif args.filter_public == "false":
        filter_public = False

    # Run check
    result = check_dependency_visibility(
        client, args.tenant_namespace, filter_public
    )

    # Report results
    logger.info("\n" + "=" * 80)
    logger.info("DEPENDENCY VISIBILITY CHECK RESULTS")
    logger.info("=" * 80)

    if result["status"] == "success":
        stats = result["stats"]
        logger.info(f"\n📊 SUMMARY:")
        logger.info(f"   Total DependencyMetadata objects: {stats['total']}")
        logger.info(
            f"   With public field: {stats['with_public_field']} "
            f"({stats['with_public_field']/stats['total']*100:.1f}%)"
        )
        logger.info(f"   Public dependencies: {stats['public_deps']}")
        logger.info(f"   Private dependencies: {stats['private_deps']}")
        logger.info(f"   Unknown visibility: {stats['unknown_visibility']}")

        if stats["by_namespace"]:
            logger.info(f"\n📁 BY NAMESPACE:")
            for ns, count in sorted(stats["by_namespace"].items()):
                logger.info(f"   {ns}: {count} dependencies")

        if stats["by_ecosystem"]:
            logger.info(f"\n📦 BY ECOSYSTEM:")
            for eco, count in sorted(stats["by_ecosystem"].items()):
                logger.info(f"   {eco}: {count} dependencies")

        if stats["sample_public"]:
            logger.info(f"\n✅ SAMPLE PUBLIC DEPENDENCIES:")
            for sample in stats["sample_public"]:
                logger.info(
                    f"   {sample['importer']} → {sample['dependency']} "
                    f"({sample['ecosystem']}, {sample['namespace']})"
                )

        if stats["sample_private"]:
            logger.info(f"\n🔒 SAMPLE PRIVATE DEPENDENCIES:")
            for sample in stats["sample_private"]:
                logger.info(
                    f"   {sample['importer']} → {sample['dependency']} "
                    f"({sample['ecosystem']}, {sample['namespace']})"
                )

        logger.info(
            f"\n💡 KEY FINDING: Visibility is tracked at the dependency "
            f"relationship level, not at the PackageVersion level."
        )
        logger.info(
            f"   Use DependencyMetadata.spec.dependency_data.public to check "
            f"if a dependency is public or private."
        )

    else:
        logger.error(f"\n❌ Error: {result.get('error', 'Unknown error')}")

    # Output JSON if requested
    if args.output:
        with open(args.output, "w") as f:
            json.dump(result, f, indent=2, default=str)
        logger.info(f"\n💾 Results written to: {args.output}")


if __name__ == "__main__":
    main()

