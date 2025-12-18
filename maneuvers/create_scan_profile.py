#!/usr/bin/env python3
"""
Create Scan Profile Script

A script to test API access and create a new Scan Profile using the Endor Labs API.
This script uses credentials from environment variables.
"""

import json
import os
import sys
from datetime import datetime
from typing import Any, Dict, Optional

# Add the src directory to the path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from endor_cockpit.api_client import APIClient

# Set up logging
import logging

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def test_api_access(client: APIClient, namespace: str) -> bool:
    """Test API access by listing namespaces."""
    try:
        logger.info(f"Testing API access for namespace: {namespace}")
        # Try to list namespaces as a simple access test
        res = client.get(f"v1/namespaces/{namespace}/namespaces")
        if res.status_code == 200:
            logger.info("✅ API access successful!")
            return True
        else:
            logger.error(f"❌ API access failed: {res.status_code} - {res.text}")
            return False
    except Exception as e:
        logger.error(f"❌ API access test failed: {e}", exc_info=True)
        return False


def create_scan_profile(
    client: APIClient,
    namespace: str,
    name: str,
    description: Optional[str] = None,
    is_default: bool = False,
) -> Optional[Dict[str, Any]]:
    """
    Create a new Scan Profile.

    Args:
        client: Authenticated APIClient instance
        namespace: Target tenant namespace (canonical name)
        name: Scan profile name
        description: Optional description
        is_default: Whether this should be the default scan profile

    Returns:
        Created scan profile data or None if creation failed
    """
    try:
        # Create a minimal scan profile payload
        # Based on OpenAPI spec: v1ScanProfileSpec
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        profile_name = f"{name}-{timestamp}" if name else f"scan-profile-{timestamp}"

        payload = {
            "meta": {
                "name": profile_name,
                "kind": "ScanProfile",
                "description": description
                or f"Scan profile created via API at {datetime.now().isoformat()}",
            },
            "spec": {
                "is_default": is_default,
                # Minimal spec - toolchain_profile and automated_scan_parameters are optional
                # We'll create a basic profile that can be configured later
            },
            "propagate": False,
        }

        logger.info(f"Creating scan profile: {profile_name}")
        logger.debug(f"Request payload: {json.dumps(payload, indent=2)}")

        res = client.post(
            f"v1/namespaces/{namespace}/scan-profiles",
            json=payload,
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
        )

        if res.status_code == 200:
            data = res.json()
            logger.info(
                f"✅ Successfully created scan profile: {data.get('uuid', 'unknown')}"
            )
            logger.info(f"   Name: {data.get('meta', {}).get('name', 'N/A')}")
            return data
        else:
            logger.error(
                f"❌ Failed to create scan profile: {res.status_code} - {res.text}"
            )
            return None

    except Exception as e:
        logger.error(f"❌ Error creating scan profile: {e}", exc_info=True)
        return None


def list_scan_profiles(
    client: APIClient, namespace: str
) -> Optional[list[Dict[str, Any]]]:
    """List all scan profiles in the namespace."""
    try:
        logger.info(f"Listing scan profiles in namespace: {namespace}")
        res = client.get(f"v1/namespaces/{namespace}/scan-profiles")

        if res.status_code == 200:
            data = res.json()
            profiles = data.get("list", {}).get("objects", [])
            logger.info(f"Found {len(profiles)} scan profile(s)")
            return profiles
        else:
            logger.error(
                f"❌ Failed to list scan profiles: {res.status_code} - {res.text}"
            )
            return None

    except Exception as e:
        logger.error(f"❌ Error listing scan profiles: {e}", exc_info=True)
        return None


def main():
    """Main function to test access and create scan profile."""
    # Get environment variables
    namespace = os.getenv("ENDOR_NAMESPACE", "")
    if not namespace:
        logger.error("❌ ENDOR_NAMESPACE environment variable must be set")
        sys.exit(1)

    logger.info("=" * 80)
    logger.info("Scan Profile Creation Script")
    logger.info("=" * 80)
    logger.info(f"Namespace: {namespace}")
    logger.info(f"API Endpoint: {os.getenv('ENDOR_API', 'Not set')}")
    logger.info("")

    # Initialize API client
    try:
        logger.info("Initializing API client...")
        client = APIClient()
        logger.info("✅ API client initialized")
    except Exception as e:
        logger.error(f"❌ Failed to initialize API client: {e}")
        sys.exit(1)

    # Test API access
    logger.info("")
    logger.info("Step 1: Testing API Access")
    logger.info("-" * 80)
    if not test_api_access(client, namespace):
        logger.error("❌ API access test failed. Cannot proceed.")
        sys.exit(1)

    # List existing scan profiles
    logger.info("")
    logger.info("Step 2: Listing Existing Scan Profiles")
    logger.info("-" * 80)
    existing_profiles = list_scan_profiles(client, namespace)
    if existing_profiles:
        logger.info("Existing scan profiles:")
        for profile in existing_profiles[:5]:  # Show first 5
            profile_name = profile.get("meta", {}).get("name", "N/A")
            profile_uuid = profile.get("uuid", "N/A")
            is_default = profile.get("spec", {}).get("is_default", False)
            default_str = " (DEFAULT)" if is_default else ""
            logger.info(f"  - {profile_name} ({profile_uuid}){default_str}")

    # Create new scan profile
    logger.info("")
    logger.info("Step 3: Creating New Scan Profile")
    logger.info("-" * 80)
    created_profile = create_scan_profile(
        client,
        namespace,
        name="test-scan-profile",
        description="Test scan profile created via API script",
        is_default=False,
    )

    if created_profile:
        logger.info("")
        logger.info("=" * 80)
        logger.info("✅ SUCCESS: Scan Profile Created")
        logger.info("=" * 80)
        logger.info(f"UUID: {created_profile.get('uuid', 'N/A')}")
        logger.info(f"Name: {created_profile.get('meta', {}).get('name', 'N/A')}")
        logger.info(
            f"Description: {created_profile.get('meta', {}).get('description', 'N/A')}"
        )
        logger.info(
            f"Created: {created_profile.get('meta', {}).get('create_time', 'N/A')}"
        )
        logger.info("")
        logger.info("Full response:")
        print(json.dumps(created_profile, indent=2))
        return 0
    else:
        logger.error("")
        logger.error("=" * 80)
        logger.error("❌ FAILED: Could not create scan profile")
        logger.error("=" * 80)
        return 1


if __name__ == "__main__":
    sys.exit(main())

