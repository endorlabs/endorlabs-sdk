#!/usr/bin/env python3
"""
Authorization Policy Maneuver

A repeatable script for creating authorization policies using the Endor Labs API client.
This script provides parameterized inputs for all necessary fields to create comprehensive
authorization policies with proper permissions and targeting.

Based on the OpenAPI schema and example authorization policy structure.

Example:

uv run python .workspace/create_auth_policy_maneuver.py \
  --tenant-namespace "endor-solutions-tgowan.cockpit" \
  --name "Read Only Policy for auditors" \
  --description "Authorization policy for sso.tools OIDC users" \
  --clause "*@endor.ai,68fae83022a47bdae812bb42" \
  --target-namespaces "endor-solutions-tgowan.cockpit" \
  --roles "SYSTEM_ROLE_READ_ONLY" \
  --resource-permissions "finding:METHOD_READ,METHOD_CREATE,METHOD_UPDATE,METHOD_DELETE;namespace:METHOD_READ,METHOD_CREATE,METHOD_UPDATE,METHOD_DELETE;package_version:METHOD_READ,METHOD_CREATE,METHOD_UPDATE,METHOD_DELETE;policy:METHOD_READ,METHOD_CREATE,METHOD_UPDATE,METHOD_DELETE;project:METHOD_READ,METHOD_CREATE,METHOD_UPDATE,METHOD_DELETE;repository:METHOD_READ,METHOD_CREATE,METHOD_UPDATE,METHOD_DELETE" \
  --dry-run

## Note: The clause is a mapping between the user and the identity provider. In this case, the identity provider's uuid is 68fae83022a47bdae812bb42
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

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AuthorizationPolicyMeta(BaseModel):
    """Metadata for authorization policy creation."""

    name: str = Field(..., description="Policy name - descriptive identifier for the authorization policy")
    description: str = Field(..., description="Policy description - explains the purpose and scope of the authorization policy")
    kind: str = Field(default="AuthorizationPolicy", description="Resource kind - always 'AuthorizationPolicy' for authorization policies")
    version: str = Field(default="v1", description="Version identifier - API version for the policy metadata")
    tags: Optional[List[str]] = Field(None, description="Policy tags - optional labels for categorization and filtering")


class AuthorizationPolicyPermissions(BaseModel):
    """Permissions configuration for authorization policy."""

    roles: Optional[List[str]] = Field(None, description="System roles - predefined role-based permissions (e.g., SYSTEM_ROLE_READ_ONLY, SYSTEM_ROLE_ADMIN)")
    rules: Optional[Dict[str, Dict[str, List[str]]]] = Field(None, description="Resource-specific permissions - maps resource types to allowed methods (e.g., {'repository': {'methods': ['METHOD_READ', 'METHOD_CREATE']}})")
    except_resources: Optional[List[str]] = Field(None, description="Excluded resources - list of resources to exclude from wildcard permissions")


class AuthorizationPolicySpec(BaseModel):
    """Specification for authorization policy creation."""

    clause: List[str] = Field(..., description="""Authorization clauses - list of claims that must match (AND operation).

CLAUSE FORMATS:
• User Email: 'user@endor.ai', 'tgowan@endor.ai'
• Domain Wildcard: '*@endor.ai' (all users from domain)
• Identity Provider UUID: '68fae83022a47bdae812bb42' (all users from this IDP)
• API Key: 'endr+abCdefGhIJKL0PQrs' with 'api-key'
• Group Claims: 'group=developers', 'group=admins'
• Mixed: 'tgowan@endor.ai,68fae83022a47bdae812bb42' (user + IDP)

SECURITY: All clauses must match (AND logic) for policy to apply.""")
    target_namespaces: List[str] = Field(..., description="Target namespaces - list of namespaces where this policy applies (must be current namespace or its children)")
    propagate: bool = Field(default=False, description="Propagation flag - whether policy should apply to child namespaces of target namespaces")
    permissions: AuthorizationPolicyPermissions = Field(..., description="Permissions configuration - defines what actions are allowed")
    expiration_time: Optional[str] = Field(None, description="Expiration time - ISO 8601 datetime when policy expires (optional, defaults to never expire)")


class CreateAuthorizationPolicyPayload(BaseModel):
    """Complete payload for creating an authorization policy."""

    meta: AuthorizationPolicyMeta = Field(..., description="Policy metadata - name, description, and other metadata")
    spec: AuthorizationPolicySpec = Field(..., description="Policy specification - authorization rules and permissions")
    propagate: bool = Field(default=False, description="Global propagation flag - whether policy propagates to child namespaces")


def create_authorization_policy(
    client: APIClient,
    tenant_namespace: str,
    payload: CreateAuthorizationPolicyPayload
) -> Optional[Dict[str, Any]]:
    """
    Create an authorization policy using the API client.

    Args:
        client: Authenticated APIClient instance
        tenant_namespace: Target tenant namespace (canonical name)
        payload: Authorization policy creation payload

    Returns:
        Created policy data or None if creation failed
    """
    try:
        # Convert payload to dict
        request_data = {
            "meta": payload.meta.model_dump(),
            "spec": payload.spec.model_dump(),
            "propagate": payload.propagate
        }

        logger.info(f"Creating authorization policy in namespace: {tenant_namespace}")
        logger.debug(f"Request data: {json.dumps(request_data, indent=2)}")

        res = client.post(
            f"v1/namespaces/{tenant_namespace}/authorization-policies",
            json=request_data,
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
        )

        if res.status_code == 200:
            data = res.json()
            logger.info(f"Successfully created authorization policy: {data.get('uuid', 'unknown')}")
            return data
        else:
            logger.error(f"Failed to create authorization policy: {res.status_code} - {res.text}")
            return None

    except Exception as e:
        logger.error(f"Error creating authorization policy: {e}", exc_info=True)
        return None


def get_authorization_policy(
    client: APIClient,
    tenant_namespace: str,
    policy_uuid: str
) -> Optional[Dict[str, Any]]:
    """
    Retrieve an authorization policy by UUID.

    Args:
        client: Authenticated APIClient instance
        tenant_namespace: Target tenant namespace (canonical name)
        policy_uuid: UUID of the authorization policy

    Returns:
        Policy data or None if retrieval failed
    """
    try:
        logger.info(f"Retrieving authorization policy: {policy_uuid}")

        res = client.get(
            f"v1/namespaces/{tenant_namespace}/authorization-policies/{policy_uuid}"
        )

        if res.status_code == 200:
            data = res.json()
            logger.info(f"Successfully retrieved authorization policy: {policy_uuid}")
            return data
        else:
            logger.error(f"Failed to retrieve authorization policy: {res.status_code} - {res.text}")
            return None

    except Exception as e:
        logger.error(f"Error retrieving authorization policy: {e}", exc_info=True)
        return None


def format_policy_for_display(policy_data: Dict[str, Any]) -> str:
    """
    Format authorization policy data for human-readable display.

    Args:
        policy_data: Authorization policy data from API

    Returns:
        Formatted string for display
    """
    if not policy_data:
        return "No policy data available"

    meta = policy_data.get('meta', {})
    spec = policy_data.get('spec', {})
    tenant_meta = policy_data.get('tenant_meta', {})
    permissions = spec.get('permissions', {})

    output = []
    output.append("=" * 80)
    output.append("AUTHORIZATION POLICY DETAILS")
    output.append("=" * 80)

    # Basic Information
    output.append(f"UUID: {policy_data.get('uuid', 'N/A')}")
    output.append(f"Name: {meta.get('name', 'N/A')}")
    output.append(f"Description: {meta.get('description', 'N/A')}")
    output.append(f"Kind: {meta.get('kind', 'N/A')}")
    output.append(f"Version: {meta.get('version', 'N/A')}")
    output.append(f"Namespace: {tenant_meta.get('namespace', 'N/A')}")
    output.append(f"Propagate: {policy_data.get('propagate', 'N/A')}")

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

    # Authorization Clauses
    output.append("")
    output.append("AUTHORIZATION CLAUSES:")
    output.append("-" * 40)
    for clause in spec.get('clause', []):
        output.append(f"  • {clause}")

    # Target Namespaces
    output.append("")
    output.append("TARGET NAMESPACES:")
    output.append("-" * 40)
    for namespace in spec.get('target_namespaces', []):
        output.append(f"  • {namespace}")

    # Permissions
    output.append("")
    output.append("PERMISSIONS:")
    output.append("-" * 40)

    # System Roles
    if permissions.get('roles'):
        output.append("System Roles:")
        for role in permissions.get('roles', []):
            output.append(f"  • {role}")
        output.append("")

    # Resource Rules
    if permissions.get('rules'):
        output.append("Resource Permissions:")
        for resource, methods_data in permissions.get('rules', {}).items():
            methods = methods_data.get('methods', [])
            output.append(f"  {resource}:")
            for method in methods:
                output.append(f"    • {method}")
        output.append("")

    # Exception Resources
    if permissions.get('except_resources'):
        output.append("Excluded Resources:")
        for resource in permissions.get('except_resources', []):
            output.append(f"  • {resource}")
        output.append("")

    # Expiration
    if spec.get('expiration_time'):
        output.append("")
        output.append("EXPIRATION:")
        output.append("-" * 40)
        output.append(f"Expires: {spec.get('expiration_time', 'N/A')}")

    # Support Policy Flag
    if spec.get('is_support_policy'):
        output.append("")
        output.append("SUPPORT POLICY:")
        output.append("-" * 40)
        output.append("This is a support policy and cannot be altered without using the SupportAccess API.")

    output.append("=" * 80)

    return "\n".join(output)


def parse_clause_list(clause_str: str) -> List[str]:
    """Parse comma-separated clause string into list."""
    return [clause.strip() for clause in clause_str.split(',') if clause.strip()]


def parse_target_namespaces(namespace_str: str) -> List[str]:
    """Parse comma-separated namespace string into list."""
    return [ns.strip() for ns in namespace_str.split(',') if ns.strip()]


def parse_roles(roles_str: str) -> List[str]:
    """Parse comma-separated roles string into list."""
    return [role.strip() for role in roles_str.split(',') if role.strip()]


def parse_resource_permissions(perms_str: str) -> Dict[str, Dict[str, List[str]]]:
    """
    Parse resource permissions from string format.
    Expected format: "resource1:method1,method2;resource2:method1"
    """
    if not perms_str:
        return {}

    rules = {}
    for resource_perms in perms_str.split(';'):
        if ':' in resource_perms:
            resource, methods = resource_perms.split(':', 1)
            resource = resource.strip()
            methods = [method.strip() for method in methods.split(',') if method.strip()]
            rules[resource] = {"methods": methods}

    return rules


def parse_except_resources(except_str: str) -> List[str]:
    """Parse comma-separated exception resources string into list."""
    return [resource.strip() for resource in except_str.split(',') if resource.strip()]


def main():
    """Main function to create authorization policy with command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Create authorization policy using Endor Labs API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Single user with specific identity provider
  python create_auth_policy_maneuver.py \\
    --tenant-namespace "endor-solutions-tgowan.cockpit" \\
    --name "Auth Policy for User: tgowan@endor.ai" \\
    --description "Authorization policy for specific user" \\
    --clause "tgowan@endor.ai,68fae83022a47bdae812bb42" \\
    --target-namespaces "endor-solutions-tgowan.cockpit" \\
    --roles "SYSTEM_ROLE_READ_ONLY"

  # Domain-wide access for all users from identity provider
  python create_auth_policy_maneuver.py \\
    --tenant-namespace "endor-solutions-tgowan.cockpit" \\
    --name "Domain Access Policy" \\
    --description "Access for all @endor.ai users" \\
    --clause "*@endor.ai,68fae83022a47bdae812bb42" \\
    --target-namespaces "endor-solutions-tgowan.cockpit" \\
    --roles "SYSTEM_ROLE_READ_ONLY" \\
    --propagate

  # API key-based access
  python create_auth_policy_maneuver.py \\
    --tenant-namespace "tenant.namespace" \\
    --name "API Key Access Policy" \\
    --description "Access for API key authentication" \\
    --clause "endr+abCdefGhIJKL0PQrs,api-key" \\
    --target-namespaces "tenant.namespace" \\
    --roles "SYSTEM_ROLE_CODE_SCANNER"

  # Group-based access with expiration
  python create_auth_policy_maneuver.py \\
    --tenant-namespace "tenant.namespace" \\
    --name "Contractor Access Policy" \\
    --description "Temporary access for contractors" \\
    --clause "group=contractors,68fae83022a47bdae812bb42" \\
    --target-namespaces "tenant.namespace.project" \\
    --roles "SYSTEM_ROLE_READ_ONLY" \\
    --expiration-time "2024-12-31T23:59:59Z"
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
        help="Policy name - descriptive identifier for the authorization policy"
    )
    parser.add_argument(
        "--description",
        required=True,
        help="Policy description - explains the purpose and scope of the authorization policy"
    )
    parser.add_argument(
        "--clause",
        required=True,
        help="""Authorization clauses - comma-separated list of claims that must match (AND operation).

CLAUSE TYPES:
• User Email: 'user@endor.ai' or 'tgowan@endor.ai'
• Domain Wildcard: '*@endor.ai' (matches all users from domain)
• Identity Provider UUID: '68fae83022a47bdae812bb42' (matches all users from this IDP)
• API Key: 'endr+abCdefGhIJKL0PQrs,api-key'
• Group Claims: 'group=developers' or 'group=admins'
• Mixed Format: 'tgowan@endor.ai,68fae83022a47bdae812bb42' (user + IDP)

EXAMPLES:
• Single user: 'tgowan@endor.ai'
• Domain + IDP: '*@endor.ai,68fae83022a47bdae812bb42'
• API key: 'endr+abCdefGhIJKL0PQrs,api-key'
• Group + IDP: 'group=developers,68fae83022a47bdae812bb42'

SECURITY NOTE: Clauses work as AND operator - ALL must match for policy to apply."""
    )
    parser.add_argument(
        "--target-namespaces",
        required=True,
        help="Target namespaces - comma-separated list of namespaces where this policy applies"
    )

    # Permissions arguments (at least one required)
    permissions_group = parser.add_argument_group(
        "Permissions",
        "Define what permissions the policy grants (at least one required)"
    )
    permissions_group.add_argument(
        "--roles",
        help="System roles - comma-separated list of system roles (e.g., 'SYSTEM_ROLE_READ_ONLY,SYSTEM_ROLE_ADMIN')"
    )
    permissions_group.add_argument(
        "--resource-permissions",
        help="Resource-specific permissions - format: 'resource1:method1,method2;resource2:method1' (e.g., 'repository:METHOD_READ,METHOD_CREATE;finding:METHOD_READ')"
    )
    permissions_group.add_argument(
        "--except-resources",
        help="Excluded resources - comma-separated list of resources to exclude from wildcard permissions"
    )

    # Optional arguments
    parser.add_argument(
        "--tags",
        help="Policy tags - comma-separated list of tags for categorization"
    )
    parser.add_argument(
        "--expiration-time",
        help="Expiration time - ISO 8601 datetime when policy expires (e.g., '2024-12-31T23:59:59Z')"
    )
    parser.add_argument(
        "--propagate",
        action="store_true",
        help="Enable propagation to child namespaces"
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

    args = parser.parse_args()

    # Set logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Validate that at least one permission type is provided
    if not args.roles and not args.resource_permissions:
        parser.error("At least one of --roles or --resource-permissions must be specified")

    try:
        # Initialize API client
        logger.info("Initializing API client...")
        client = APIClient()

        # Parse arguments
        clauses = parse_clause_list(args.clause)
        target_namespaces = parse_target_namespaces(args.target_namespaces)
        roles = parse_roles(args.roles) if args.roles else None
        resource_permissions = parse_resource_permissions(args.resource_permissions) if args.resource_permissions else None
        except_resources = parse_except_resources(args.except_resources) if args.except_resources else None
        tags = [tag.strip() for tag in args.tags.split(',')] if args.tags else None

        # Create permissions object
        permissions = AuthorizationPolicyPermissions(
            roles=roles,
            rules=resource_permissions,
            except_resources=except_resources
        )

        # Create spec object
        spec = AuthorizationPolicySpec(
            clause=clauses,
            target_namespaces=target_namespaces,
            propagate=args.propagate,
            permissions=permissions,
            expiration_time=args.expiration_time
        )

        # Create meta object
        meta = AuthorizationPolicyMeta(
            name=args.name,
            description=args.description,
            tags=tags
        )

        # Create payload
        payload = CreateAuthorizationPolicyPayload(
            meta=meta,
            spec=spec,
            propagate=args.propagate
        )

        if args.dry_run:
            print("=== DRY RUN - Authorization Policy Payload ===")
            print(json.dumps(payload.model_dump(), indent=2))
            return

        # Create the authorization policy
        result = create_authorization_policy(client, args.tenant_namespace, payload)

        if result:
            policy_uuid = result.get('uuid')
            print("=== Authorization Policy Created Successfully ===")
            print(f"UUID: {policy_uuid}")
            print(f"Name: {result.get('meta', {}).get('name', 'unknown')}")
            print(f"Namespace: {result.get('tenant_meta', {}).get('namespace', 'unknown')}")
            print(f"Created: {result.get('meta', {}).get('create_time', 'unknown')}")

            # Retrieve the policy and display in human-readable format
            if policy_uuid:
                print("\n" + "=" * 80)
                print("RETRIEVING POLICY DETAILS...")
                print("=" * 80)

                retrieved_policy = get_authorization_policy(client, args.tenant_namespace, policy_uuid)
                if retrieved_policy:
                    print("\n" + format_policy_for_display(retrieved_policy))
                else:
                    print("Failed to retrieve policy details after creation")
            else:
                print("Warning: No UUID returned from policy creation")
        else:
            print("Failed to create authorization policy")
            sys.exit(1)

    except KeyboardInterrupt:
        logger.info("Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
