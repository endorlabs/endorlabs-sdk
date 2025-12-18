#!/usr/bin/env python3
"""
Inspect Scan Result Script

A script to fetch and inspect a scan result to check toolchain source and
auto-detection information.
"""

import json
import os
import sys
from typing import Any, Dict, Optional

# Add the src directory to the path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from endor_cockpit.api_client import APIClient
from endor_cockpit.resources import scan_result

# Set up logging
import logging

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def inspect_scan_result(
    client: APIClient, namespace: str, scan_result_uuid: str
) -> Optional[Dict[str, Any]]:
    """
    Fetch and inspect a scan result to check toolchain source.

    Args:
        client: Authenticated APIClient instance
        namespace: Target tenant namespace (canonical name)
        scan_result_uuid: UUID of the scan result to inspect

    Returns:
        Dictionary with inspection results or None if fetch failed
    """
    try:
        logger.info(f"Fetching scan result: {scan_result_uuid}")
        result = scan_result.get_scan_result(client, namespace, scan_result_uuid)

        if not result:
            logger.error("❌ Failed to fetch scan result")
            return None

        logger.info("✅ Successfully fetched scan result")
        logger.info("")

        # Extract provisioning result information
        inspection = {
            "scan_result_uuid": result.uuid,
            "scan_result_name": result.meta.name if result.meta else "N/A",
            "status": result.spec.status if result.spec else "N/A",
            "provisioning_result": None,
            "toolchain_info": {},
        }

        if result.spec and result.spec.provisioning_result:
            prov_result = result.spec.provisioning_result
            inspection["provisioning_result"] = {
                "uuid": prov_result.provisioning_result_uuid,
                "exit_code": prov_result.exit_code,
                "error": prov_result.error,
            }

            # Check toolchain source
            tool_chains_source = prov_result.tool_chains_source
            auto_detect_result = prov_result.auto_detect_result
            tool_chains = prov_result.tool_chains
            scan_profile = prov_result.scan_profile

            inspection["toolchain_info"] = {
                "tool_chains_source": tool_chains_source,
                "auto_detect_result": auto_detect_result,
                "tool_chains": tool_chains,
                "scan_profile": {
                    "uuid": scan_profile.get("uuid") if scan_profile else None,
                    "name": (
                        scan_profile.get("meta", {}).get("name")
                        if scan_profile
                        else None
                    ),
                    "toolchain_profile": (
                        scan_profile.get("spec", {}).get("toolchain_profile")
                        if scan_profile
                        else None
                    ),
                }
                if scan_profile
                else None,
            }

        return inspection

    except Exception as e:
        logger.error(f"❌ Error inspecting scan result: {e}", exc_info=True)
        return None


def print_inspection_results(inspection: Dict[str, Any]) -> None:
    """Print formatted inspection results."""
    logger.info("=" * 80)
    logger.info("SCAN RESULT INSPECTION RESULTS")
    logger.info("=" * 80)
    logger.info(f"Scan Result UUID: {inspection.get('scan_result_uuid')}")
    logger.info(f"Scan Result Name: {inspection.get('scan_result_name')}")
    logger.info(f"Status: {inspection.get('status')}")
    logger.info("")

    prov_result = inspection.get("provisioning_result")
    if prov_result:
        logger.info("PROVISIONING RESULT:")
        logger.info(f"  UUID: {prov_result.get('uuid')}")
        logger.info(f"  Exit Code: {prov_result.get('exit_code')}")
        if prov_result.get("error"):
            logger.warning(f"  Error: {prov_result.get('error')}")
        logger.info("")

    toolchain_info = inspection.get("toolchain_info", {})
    tool_chains_source = toolchain_info.get("tool_chains_source")
    auto_detect_result = toolchain_info.get("auto_detect_result")

    logger.info("TOOLCHAIN SOURCE INFORMATION:")
    if tool_chains_source:
        logger.info(f"  tool_chains_source: {tool_chains_source}")
        if isinstance(tool_chains_source, str):
            if tool_chains_source == "TOOL_CHAINS_SOURCE_AUTO_DETECTION":
                logger.info("  ✅ AUTO-DETECTION WAS USED")
            elif tool_chains_source == "TOOL_CHAINS_SOURCE_API":
                logger.info("  📋 Toolchains from API/Scan Profile")
            elif tool_chains_source == "TOOL_CHAINS_SOURCE_FILE":
                logger.info("  📄 Toolchains from scanprofile.yaml file")
            elif tool_chains_source == "TOOL_CHAINS_SOURCE_DEFAULTS":
                logger.info("  🔧 System default toolchains")
            elif tool_chains_source == "TOOL_CHAINS_SOURCE_NAMESPACE_DEFAULT":
                logger.info("  🏢 Namespace default toolchains")
        else:
            logger.info(f"  (Raw value: {json.dumps(tool_chains_source, indent=2)})")
    else:
        logger.warning("  ⚠️  tool_chains_source not available")

    logger.info("")

    if auto_detect_result:
        logger.info("AUTO-DETECT RESULTS:")
        logger.info(json.dumps(auto_detect_result, indent=2))
        logger.info("")
    else:
        logger.info("AUTO-DETECT RESULTS: None (auto-detection may not have been used)")
        logger.info("")

    scan_profile_info = toolchain_info.get("scan_profile")
    if scan_profile_info:
        logger.info("SCAN PROFILE USED:")
        logger.info(f"  UUID: {scan_profile_info.get('uuid')}")
        logger.info(f"  Name: {scan_profile_info.get('name')}")
        toolchain_profile = scan_profile_info.get("toolchain_profile")
        if toolchain_profile is None:
            logger.info("  ✅ toolchain_profile: null (auto-detection enabled)")
        elif toolchain_profile == {}:
            logger.info("  ✅ toolchain_profile: {} (empty, auto-detection enabled)")
        else:
            logger.info(
                f"  📋 toolchain_profile: configured "
                f"({len(str(toolchain_profile))} chars)"
            )
        logger.info("")

    tool_chains = toolchain_info.get("tool_chains")
    if tool_chains:
        logger.info("TOOLCHAINS INSTALLED:")
        logger.info(json.dumps(tool_chains, indent=2))
    else:
        logger.info("TOOLCHAINS INSTALLED: None")

    logger.info("")
    logger.info("=" * 80)


def main():
    """Main function to inspect a scan result."""
    # Get environment variables
    namespace = os.getenv("ENDOR_NAMESPACE", "")
    if not namespace:
        logger.error("❌ ENDOR_NAMESPACE environment variable must be set")
        sys.exit(1)

    # Get scan result UUID from command line or use default
    if len(sys.argv) > 1:
        scan_result_uuid = sys.argv[1]
    else:
        # Default from the URL provided
        scan_result_uuid = "69447625d899e9af5f2f7fb2"
        logger.info(
            f"No UUID provided, using default from URL: {scan_result_uuid}"
        )

    logger.info("=" * 80)
    logger.info("Scan Result Inspection Script")
    logger.info("=" * 80)
    logger.info(f"Namespace: {namespace}")
    logger.info(f"Scan Result UUID: {scan_result_uuid}")
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

    # Inspect scan result
    logger.info("")
    logger.info("Inspecting Scan Result")
    logger.info("-" * 80)
    inspection = inspect_scan_result(client, namespace, scan_result_uuid)

    if inspection:
        print_inspection_results(inspection)
        return 0
    else:
        logger.error("")
        logger.error("=" * 80)
        logger.error("❌ FAILED: Could not inspect scan result")
        logger.error("=" * 80)
        return 1


if __name__ == "__main__":
    sys.exit(main())

