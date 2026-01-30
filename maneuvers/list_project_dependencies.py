#!/usr/bin/env python3
"""
List all DependencyMetadata for this project.

Retrieves all dependencies in the dependency tree for packages in this project
using the efficient traverse pattern to query across all namespaces.

Example:
    uv run python maneuvers/list_project_dependencies.py
    uv run python maneuvers/list_project_dependencies.py --output deps.json
"""

import argparse
import json
import logging
import os
import sys
from collections import defaultdict
from typing import Any, Dict, List

# Add the src directory to the path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from endorlabs.api_client import APIClient
from endorlabs.resources import dependency_metadata
from endorlabs.types import ListParameters

# Configure logging
logging.getLogger("urllib3.connectionpool").setLevel(logging.WARNING)
logging.getLogger("endorlabs").setLevel(logging.INFO)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def format_dependency(dep) -> Dict[str, Any]:
    """Format a dependency metadata object for display."""
    dep_data = dep.spec.dependency_data if dep.spec else None
    importer_data = dep.spec.importer_data if dep.spec else None

    formatted = {
        "uuid": dep.uuid,
        "namespace": (
            dep.tenant_meta.namespace
            if dep.tenant_meta and dep.tenant_meta.namespace
            else "unknown"
        ),
    }

    if dep_data:
        formatted["dependency"] = {
            "package_name": dep_data.package_name,
            "resolved_version": dep_data.resolved_version,
            "unresolved_version": dep_data.unresolved_version,
            "ecosystem": dep_data.ecosystem.value if dep_data.ecosystem else None,
            "scope": dep_data.scope.value if dep_data.scope else None,
            "reachability": (
                dep_data.reachability.value if dep_data.reachability else None
            ),
            "utilization": dep_data.utilization,
            "imported_type": (
                dep_data.imported_type.value if dep_data.imported_type else None
            ),
            "discovery_type": (
                dep_data.discovery_type.value if dep_data.discovery_type else None
            ),
        }
        # Check for public field (may not be in model but exists in API)
        dep_dict = dep_data.model_dump() if hasattr(dep_data, "model_dump") else {}
        if "public" in dep_dict:
            formatted["dependency"]["public"] = dep_dict["public"]

    if importer_data:
        formatted["importer"] = {
            "package_name": importer_data.package_name,
            "package_version_name": importer_data.package_version_name,
            "package_version_ref": importer_data.package_version_ref,
            "package_version_sha": importer_data.package_version_sha,
        }

    return formatted


def list_all_dependencies(
    client: APIClient, tenant_namespace: str
) -> Dict[str, Any]:
    """
    List all dependency metadata across all namespaces.

    Args:
        client: Authenticated APIClient
        tenant_namespace: Root tenant namespace

    Returns:
        Dictionary with dependencies and statistics
    """
    logger.info(
        f"Querying DependencyMetadata with traverse from: {tenant_namespace}"
    )

    # Use canonical traverse pattern for tenant-wide query
    list_params = ListParameters(traverse=True)

    try:
        # Query all DependencyMetadata with traverse
        all_deps = dependency_metadata.list_dependency_metadata(
            client, tenant_namespace, list_params
        )

        logger.info(f"Found {len(all_deps)} DependencyMetadata objects")

        # Format and analyze results
        formatted_deps = [format_dependency(dep) for dep in all_deps]

        # Calculate statistics
        stats = {
            "total": len(all_deps),
            "by_namespace": defaultdict(int),
            "by_ecosystem": defaultdict(int),
            "by_scope": defaultdict(int),
            "by_reachability": defaultdict(int),
            "unique_packages": set(),
            "unique_importers": set(),
        }

        for dep in all_deps:
            # Namespace stats
            namespace = (
                dep.tenant_meta.namespace
                if dep.tenant_meta and dep.tenant_meta.namespace
                else "unknown"
            )
            stats["by_namespace"][namespace] += 1

            # Dependency data stats
            if dep.spec and dep.spec.dependency_data:
                dep_data = dep.spec.dependency_data
                stats["unique_packages"].add(dep_data.package_name)

                if dep_data.ecosystem:
                    stats["by_ecosystem"][dep_data.ecosystem.value] += 1
                if dep_data.scope:
                    stats["by_scope"][dep_data.scope.value] += 1
                if dep_data.reachability:
                    stats["by_reachability"][dep_data.reachability.value] += 1

            # Importer stats
            if dep.spec and dep.spec.importer_data:
                importer_data = dep.spec.importer_data
                stats["unique_importers"].add(importer_data.package_name)

        # Convert sets to counts for JSON serialization
        stats["unique_packages_count"] = len(stats["unique_packages"])
        stats["unique_importers_count"] = len(stats["unique_importers"])
        stats["unique_packages"] = list(stats["unique_packages"])[:20]  # Sample
        stats["unique_importers"] = list(stats["unique_importers"])[:20]  # Sample

        return {
            "status": "success",
            "dependencies": formatted_deps,
            "statistics": stats,
        }

    except Exception as e:
        logger.error(f"Error querying DependencyMetadata: {e}", exc_info=True)
        return {
            "status": "error",
            "error": str(e),
            "dependencies": [],
            "statistics": {},
        }


def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(
        description="List all DependencyMetadata for this project"
    )
    parser.add_argument(
        "--tenant-namespace",
        type=str,
        default=os.getenv("ENDOR_NAMESPACE"),
        help="Root tenant namespace (default: ENDOR_NAMESPACE env var)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Output file for JSON results (default: stdout)",
    )
    parser.add_argument(
        "--summary-only",
        action="store_true",
        help="Only show summary statistics, not full dependency list",
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

    # List dependencies
    result = list_all_dependencies(client, args.tenant_namespace)

    # Report results
    logger.info("\n" + "=" * 80)
    logger.info("DEPENDENCY METADATA RESULTS")
    logger.info("=" * 80)

    if result["status"] == "success":
        stats = result["statistics"]
        deps = result["dependencies"]

        logger.info(f"\n📊 SUMMARY:")
        logger.info(f"   Total DependencyMetadata objects: {stats['total']}")
        logger.info(
            f"   Unique packages: {stats['unique_packages_count']}"
        )
        logger.info(
            f"   Unique importers: {stats['unique_importers_count']}"
        )

        if stats["by_namespace"]:
            logger.info(f"\n📁 BY NAMESPACE:")
            for ns, count in sorted(stats["by_namespace"].items()):
                logger.info(f"   {ns}: {count} dependencies")

        if stats["by_ecosystem"]:
            logger.info(f"\n📦 BY ECOSYSTEM:")
            for eco, count in sorted(stats["by_ecosystem"].items()):
                logger.info(f"   {eco}: {count} dependencies")

        if stats["by_scope"]:
            logger.info(f"\n🔍 BY SCOPE:")
            for scope, count in sorted(stats["by_scope"].items()):
                logger.info(f"   {scope}: {count} dependencies")

        if stats["by_reachability"]:
            logger.info(f"\n🔗 BY REACHABILITY:")
            for reach, count in sorted(stats["by_reachability"].items()):
                logger.info(f"   {reach}: {count} dependencies")

        if not args.summary_only:
            logger.info(f"\n📋 DEPENDENCIES (showing first 20):")
            for dep in deps[:20]:
                importer = dep.get("importer", {}).get("package_name", "unknown")
                dep_name = (
                    dep.get("dependency", {}).get("package_name", "unknown")
                )
                version = (
                    dep.get("dependency", {}).get("resolved_version", "unknown")
                )
                ecosystem = (
                    dep.get("dependency", {}).get("ecosystem", "unknown")
                )
                logger.info(
                    f"   {importer} → {dep_name}@{version} ({ecosystem})"
                )
            if len(deps) > 20:
                logger.info(f"   ... and {len(deps) - 20} more dependencies")

    else:
        logger.error(f"\n❌ Error: {result.get('error', 'Unknown error')}")

    # Output JSON if requested
    if args.output:
        with open(args.output, "w") as f:
            json.dump(result, f, indent=2, default=str)
        logger.info(f"\n💾 Results written to: {args.output}")


if __name__ == "__main__":
    main()


