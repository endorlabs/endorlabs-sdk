#!/usr/bin/env python3
"""
Script to create a ServiceRequest to enable NAT network requests for SystemConfig.

**ADMIN USERS ONLY**: This script is restricted to Endor Labs Admin users only.
It creates a ServiceRequest to update SystemConfig.cloud_deployment.nat_network_requests
which requires admin-level permissions.

This version uses browser-based authentication and can also accept a token as an argument.
"""

import json
import os
import sys
from pathlib import Path
from typing import Optional

import requests

# Add the src to the path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

try:
    from endor_cockpit.auth_server import get_token
except ImportError:
    get_token = None


def create_service_request_direct(
    base_url: str,
    token: str,
    namespace: str,
    target_namespace: str,
    system_config_uuid: str,
    approvers: list[str],
    description: Optional[str] = None,
) -> Optional[dict]:
    """
    Create a ServiceRequest to update SystemConfig using direct HTTP request.

    **ADMIN USERS ONLY**: This function requires admin-level permissions to create
    ServiceRequests that modify SystemConfig settings.

    Args:
        base_url: Base URL for the API (e.g., "https://api.endorlabs.com")
        token: Bearer token for authentication (must be from an admin user)
        namespace: The namespace where the ServiceRequest is created (e.g., "endor-admin")
        target_namespace: The target namespace for the SystemConfig update (e.g., "datavant")
        system_config_uuid: UUID of the SystemConfig to update
        approvers: List of approver email addresses
        description: Optional description for the ServiceRequest

    Returns:
        Created ServiceRequest data or None if creation failed
    """
    # Build the payload matching the working example structure
    payload = {
        "meta": {
            "name": f"SystemConfig - {target_namespace}",
            "kind": "ServiceRequest",
            "description": description
            or f"SystemConfig - {target_namespace} - enable nat_network_requests",
        },
        "spec": {
            "description": description
            or f"SystemConfig - {target_namespace} - enable nat_network_requests",
            "resource": "SystemConfig",
            "target_namespace": target_namespace,
            "approvers": approvers,
            "method": "METHOD_UPDATE",
            "data": {
                "@type": "internal.endor.ai.endor.v1.UpdateSystemConfigRequest",
                "object": {
                    "uuid": system_config_uuid,
                    "spec": {
                        "cloud_deployment": {
                            "nat_network_requests": True,
                        }
                    },
                },
                "request": {
                    "update_mask": "spec.cloudDeployment",
                },
            },
        },
    }

    # Build the endpoint URL
    endpoint = f"{base_url}/v1/namespaces/{namespace}/service-requests"

    # Set up headers
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }

    print(f"Creating ServiceRequest in namespace: {namespace}")
    print(f"Target namespace: {target_namespace}")
    print(f"SystemConfig UUID: {system_config_uuid}")
    print(f"Endpoint: {endpoint}")
    print(f"\nPayload:\n{json.dumps(payload, indent=2)}")

    try:
        response = requests.post(
            endpoint,
            json=payload,
            headers=headers,
        )

        print(f"\nResponse Status: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print(f"\n✅ Successfully created ServiceRequest: {data.get('uuid', 'unknown')}")
            print(f"\nFull Response:\n{json.dumps(data, indent=2)}")
            return data
        else:
            print(f"\n❌ Failed to create ServiceRequest: {response.status_code}")
            print(f"Response: {response.text}")
            try:
                error_data = response.json()
                print(f"Error details:\n{json.dumps(error_data, indent=2)}")
            except:
                pass
            return None

    except Exception as e:
        print(f"\n❌ Error creating ServiceRequest: {e}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        return None


def main():
    """
    Main entry point.

    **ADMIN USERS ONLY**: This script requires admin-level permissions.
    """
    import argparse

    parser = argparse.ArgumentParser(
        description="Create a ServiceRequest to update SystemConfig (ADMIN USERS ONLY)"
    )
    parser.add_argument(
        "--base-url",
        default=os.getenv("ENDOR_API", "https://api.endorlabs.com"),
        help="Base URL for the API (default: from ENDOR_API env var or https://api.endorlabs.com)",
    )
    parser.add_argument(
        "--token",
        default=os.getenv("ENDOR_TOKEN"),
        help="Bearer token for authentication (default: from ENDOR_TOKEN env var or browser auth)",
    )
    parser.add_argument(
        "--namespace",
        default=os.getenv("ENDOR_NAMESPACE", "endor-admin"),
        help="Namespace where ServiceRequest is created (default: endor-admin)",
    )
    parser.add_argument(
        "--target-namespace",
        default="datavant",
        help="Target namespace for SystemConfig update (default: datavant)",
    )
    parser.add_argument(
        "--system-config-uuid",
        default="6893987de16661801d62b96c",
        help="UUID of the SystemConfig to update",
    )
    parser.add_argument(
        "--approvers",
        default="sesbrandt@endor.ai",
        help="Comma-separated list of approver email addresses",
    )
    parser.add_argument(
        "--description",
        help="Description for the ServiceRequest",
    )
    parser.add_argument(
        "--auth-method",
        choices=["browser", "admin", "google", "github", "gitlab", "email"],
        default="admin",
        help="Browser authentication method (default: admin SSO)",
    )
    parser.add_argument(
        "--browser",
        help="Browser name for authentication (optional)",
    )
    parser.add_argument(
        "--email",
        help="Email address for email-based authentication",
    )
    parser.add_argument(
        "--environment",
        default="endorlabs.com",
        help="API environment (default: endorlabs.com)",
    )
    parser.add_argument(
        "--no-browser-auth",
        action="store_true",
        help="Skip browser authentication (requires --token)",
    )

    args = parser.parse_args()

    # Get token - try env var first, then browser auth if available
    token = args.token
    if not token and not args.no_browser_auth:
        if get_token:
            print("🔐 No token provided. Starting browser authentication...")
            auth_method = args.auth_method
            if auth_method == "browser":
                auth_method = "admin"  # Default to admin SSO

            token = get_token(
                timeout=60,
                environment=args.environment,
                browser_name=args.browser,
                method=auth_method,
                email=args.email,
            )
            if token:
                print("✅ Browser authentication successful!")
            else:
                print(
                    "❌ Browser authentication failed or was cancelled",
                    file=sys.stderr,
                )
                sys.exit(1)
        else:
            print(
                "❌ Error: Token is required. Set ENDOR_TOKEN env var, use --token, or install endor-cockpit for browser auth",
                file=sys.stderr,
            )
            sys.exit(1)

    if not token:
        print(
            "❌ Error: Token is required. Set ENDOR_TOKEN env var or use --token",
            file=sys.stderr,
        )
        sys.exit(1)

    approvers = [a.strip() for a in args.approvers.split(",") if a.strip()]

    result = create_service_request_direct(
        base_url=args.base_url,
        token=token,  # Use the token variable (may be from browser auth)
        namespace=args.namespace,
        target_namespace=args.target_namespace,
        system_config_uuid=args.system_config_uuid,
        approvers=approvers,
        description=args.description,
    )

    if result:
        print(f"\n✅ ServiceRequest created successfully!")
        print(f"UUID: {result.get('uuid')}")
        print(f"Status: {result.get('spec', {}).get('status', 'unknown')}")
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
