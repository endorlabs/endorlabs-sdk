#!/usr/bin/env python3
"""
Namespace Creation Maneuver

A repeatable script for creating namespaces using the Endor Labs API client.
This script provides parameterized inputs for creating child namespaces with proper
hierarchy and configuration.

Based on the OpenAPI schema and namespace resource structure.

Example:

uv run python maneuvers/create_namespace.py \
  --parent-namespace "tenant.namespace" \
  --name "kessel" \
  --description "Kessel namespace for testing" \
  --dry-run

## Note: Namespaces provide hierarchical organization and access control boundaries.
"""

import argparse
import json
import logging
import os
import sys
from typing import Any, Dict, Optional

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


class NamespaceMeta(BaseModel):
    """Metadata for namespace creation."""

    name: str = Field(..., description="Namespace name - unique identifier within parent namespace")
    description: str = Field(..., description="Namespace description - explains the purpose and scope")
    kind: str = Field(default="Namespace", description="Resource kind - always 'Namespace' for namespaces")
    version: str = Field(default="v1", description="Resource version")
    tags: Optional[list] = Field(default=None, description="Optional tags for categorization")


class CreateNamespacePayload(BaseModel):
    """Payload for creating a namespace."""

    meta: NamespaceMeta = Field(..., description="Namespace metadata")
    propagate: bool = Field(default=True, description="Whether to propagate to child namespaces")


def create_namespace(
    client: APIClient,
    parent_namespace: str,
    payload: CreateNamespacePayload
) -> Optional[Dict[str, Any]]:
    """
    Create a namespace in the specified parent namespace.

    Args:
        client: API client instance
        parent_namespace: Parent namespace (e.g., "tenant.namespace")
        payload: Namespace creation payload

    Returns:
        Created namespace data or None if creation failed
    """
    try:
        logger.info(f"Creating namespace in parent: {parent_namespace}")

        # Create sanitized payload for debug logging
        debug_payload = payload.model_dump()
        logger.debug(f"Request data: {json.dumps(debug_payload, indent=2)}")

        res = client.post(
            f"v1/namespaces/{parent_namespace}/namespaces",
            json=payload.model_dump(),
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
        )

        if res.status_code == 200:
            data = res.json()
            logger.info(f"Successfully created namespace: {data.get('uuid', 'unknown')}")
            return data
        else:
            logger.error(f"Failed to create namespace: {res.status_code} - {res.text}")
            return None

    except Exception as e:
        logger.error(f"Error creating namespace: {e}", exc_info=True)
        return None


def get_namespace(
    client: APIClient,
    tenant_namespace: str,
    namespace_uuid: str
) -> Optional[Dict[str, Any]]:
    """
    Retrieve a namespace by UUID.

    Args:
        client: API client instance
        tenant_namespace: Tenant namespace
        namespace_uuid: Namespace UUID

    Returns:
        Namespace data or None if retrieval failed
    """
    try:
        logger.info(f"Retrieving namespace: {namespace_uuid}")

        res = client.get(
            f"v1/namespaces/{tenant_namespace}/namespaces/{namespace_uuid}"
        )

        if res.status_code == 200:
            data = res.json()
            logger.info(f"Successfully retrieved namespace: {namespace_uuid}")
            return data
        else:
            logger.error(f"Failed to retrieve namespace: {res.status_code} - {res.text}")
            return None

    except Exception as e:
        logger.error(f"Error retrieving namespace: {e}", exc_info=True)
        return None


def format_namespace_for_display(namespace_data: Dict[str, Any]) -> str:
    """
    Format namespace data for human-readable display.

    Args:
        namespace_data: Namespace data from API

    Returns:
        Formatted string for display
    """
    if not namespace_data:
        return "No namespace data available"

    meta = namespace_data.get('meta', {})
    tenant_meta = namespace_data.get('tenant_meta', {})

    output = []
    output.append("=" * 80)
    output.append("NAMESPACE DETAILS")
    output.append("=" * 80)

    # Basic Information
    output.append(f"UUID: {namespace_data.get('uuid', 'N/A')}")
    output.append(f"Name: {meta.get('name', 'N/A')}")
    output.append(f"Description: {meta.get('description', 'N/A')}")
    output.append(f"Kind: {meta.get('kind', 'N/A')}")
    output.append(f"Version: {meta.get('version', 'N/A')}")
    output.append(f"Namespace: {tenant_meta.get('namespace', 'N/A')}")
    output.append(f"Propagate: {namespace_data.get('propagate', 'N/A')}")
    output.append("")

    # Timestamps
    output.append("TIMESTAMPS:")
    output.append("-" * 40)
    output.append(f"Created: {meta.get('create_time', 'N/A')}")
    output.append(f"Created By: {meta.get('created_by', 'N/A')}")
    output.append(f"Updated: {meta.get('update_time', 'N/A')}")
    output.append(f"Updated By: {meta.get('updated_by', 'N/A')}")
    output.append("")

    # Tags
    tags = meta.get('tags', [])
    if tags:
        output.append("TAGS:")
        output.append("-" * 40)
        for tag in tags:
            output.append(f"  - {tag}")
        output.append("")

    output.append("=" * 80)

    return "\n".join(output)


def main():
    """Main function to handle command line arguments and execute namespace creation."""
    parser = argparse.ArgumentParser(
        description="Create a namespace in the Endor Labs platform",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:

# Create a child namespace
uv run python maneuvers/create_namespace.py \\
  --parent-namespace "tenant.namespace" \\
  --name "kessel" \\
  --description "Kessel namespace for testing" \\
  --dry-run

# Create with tags
uv run python maneuvers/create_namespace.py \\
  --parent-namespace "tenant.namespace" \\
  --name "production" \\
  --description "Production environment namespace" \\
  --tags "env:production,team:platform" \\
  --no-propagate
        """
    )

    # Required arguments
    parser.add_argument(
        "--parent-namespace",
        required=True,
        help="Parent namespace (e.g., 'tenant.namespace')"
    )
    parser.add_argument(
        "--name",
        required=True,
        help="Namespace name (unique within parent)"
    )
    parser.add_argument(
        "--description",
        required=True,
        help="Namespace description"
    )

    # Optional arguments
    parser.add_argument(
        "--tags",
        help="Comma-separated tags (e.g., 'env:prod,team:platform')"
    )
    parser.add_argument(
        "--no-propagate",
        action="store_true",
        help="Don't propagate to child namespaces (default: propagate=True)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show the payload that would be sent without creating the namespace"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )

    args = parser.parse_args()

    # Configure logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Initialize API client
    logger.info("Initializing API client...")
    client = APIClient()

    # Parse tags
    tags = None
    if args.tags:
        tags = [tag.strip() for tag in args.tags.split(',') if tag.strip()]

    # Create namespace metadata
    meta = NamespaceMeta(
        name=args.name,
        description=args.description,
        tags=tags
    )

    # Create payload
    payload = CreateNamespacePayload(
        meta=meta,
        propagate=not args.no_propagate
    )

    if args.dry_run:
        print("=== DRY RUN - Namespace Creation Payload ===")
        print(json.dumps(payload.model_dump(), indent=2))
        return

    # Create namespace
    result = create_namespace(client, args.parent_namespace, payload)

    if result:
        print("=== Namespace Created Successfully ===")
        print(f"UUID: {result.get('uuid', 'unknown')}")
        print(f"Name: {result.get('meta', {}).get('name', 'unknown')}")
        print(f"Namespace: {result.get('tenant_meta', {}).get('namespace', 'unknown')}")
        print(f"Created: {result.get('meta', {}).get('create_time', 'unknown')}")
        print()

        # Retrieve and display full details
        print("=" * 80)
        print("RETRIEVING NAMESPACE DETAILS...")
        print("=" * 80)
        print()

        namespace_data = get_namespace(
            client,
            result.get('tenant_meta', {}).get('namespace', args.parent_namespace),
            result.get('uuid', '')
        )

        if namespace_data:
            print(format_namespace_for_display(namespace_data))
        else:
            print("Failed to retrieve namespace details")
    else:
        print("Failed to create namespace")
        sys.exit(1)


if __name__ == "__main__":
    main()

