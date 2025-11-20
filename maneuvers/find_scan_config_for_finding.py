#!/usr/bin/env python3
"""
Find Scan Config for Finding Maneuver

Given a Finding UUID, this script finds the ScanResult resources that could have
created the finding by:
1. Getting the Finding by UUID to retrieve its creation date and project UUID
2. Searching through all ScanResult resources for the same project
3. Filtering ScanResults where scan_start < finding.created < scan_end
4. Returning spec.environment.config.ScanConfig from matching ScanResults

This solves the problem of not knowing which scan created a finding.

Example:

uv run python maneuvers/find_scan_config_for_finding.py \
  --namespace "endor-solutions-tgowan.cockpit" \
  --finding-uuid "0123456789abcdef01234567" \
  --output-format json \
  --traverse

Note: This maneuver now uses the ScanResult SDK resource module.
"""

import argparse
import json
import logging
import os
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional

# Add the src directory to the path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from endor_cockpit.api_client import APIClient
from endor_cockpit.resources import finding, scan_result
from endor_cockpit.types import ListParameters

# Configure logging to reduce verbosity
logging.getLogger('urllib3.connectionpool').setLevel(logging.WARNING)
logging.getLogger('endor_cockpit').setLevel(logging.INFO)

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def parse_datetime(dt_str: str) -> datetime:
    """Parse datetime string to datetime object."""
    try:
        # Try ISO format with timezone
        if dt_str.endswith('Z'):
            dt_str = dt_str[:-1] + '+00:00'
        return datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
    except ValueError:
        # Try other common formats
        for fmt in ['%Y-%m-%dT%H:%M:%S.%f', '%Y-%m-%dT%H:%M:%S']:
            try:
                return datetime.strptime(dt_str, fmt)
            except ValueError:
                continue
        raise ValueError(f"Unable to parse datetime: {dt_str}")


def get_parent_namespace(namespace: str) -> str:
    """
    Extract parent namespace from a child namespace.
    
    Args:
        namespace: Full namespace (e.g., "tenant.namespace.child")
        
    Returns:
        Parent namespace (e.g., "tenant" for child namespaces)
    """
    parts = namespace.split('.')
    if len(parts) > 1:
        return parts[0]  # Return the root/top-level namespace
    return namespace


def get_finding_details(
    client: APIClient,
    namespace: str,
    finding_uuid: str,
    traverse: bool = False
) -> Optional[Dict[str, Any]]:
    """
    Get Finding by UUID and extract creation date and project UUID.

    Args:
        client: Authenticated APIClient instance
        namespace: Target namespace
        finding_uuid: UUID of the finding to retrieve
        traverse: If True, search child namespaces as well (uses parent namespace)

    Returns:
        Dict with 'create_time' and 'project_uuid', or None if not found
    """
    try:
        # First try to get finding from the provided namespace
        # If traverse is enabled, also search parent namespace
        finding_obj = finding.get_finding(client, namespace, finding_uuid)
        
        if not finding_obj and traverse:
            # If not found and traverse enabled, search parent namespace
            search_namespace = get_parent_namespace(namespace)
            list_params = ListParameters(
                filter=f'uuid=="{finding_uuid}"',
                include_child_namespaces=True,
                mask=None,
                page_size=None,
                page_token=None,
                sort_field=None,
                sort_order=None,
                count=None,
                from_date=None,
                to_date=None
            )
            findings_list = finding.list_findings(client, search_namespace, list_params)
            finding_obj = findings_list[0] if findings_list else None
        if not finding_obj:
            logger.error(f"Finding {finding_uuid} not found")
            return None

        create_time = finding_obj.meta.create_time
        project_uuid = finding_obj.spec.project_uuid

        if not create_time:
            logger.error("Finding has no create_time")
            return None
        if not project_uuid:
            logger.error("Finding has no project_uuid")
            return None

        logger.info(
            f"Found finding: {finding_obj.meta.name} "
            f"(created: {create_time}, project: {project_uuid})"
        )

        return {
            'create_time': create_time,
            'project_uuid': project_uuid,
            'finding_name': finding_obj.meta.name,
        }
    except Exception as e:
        logger.error(f"Error getting finding: {e}")
        return None


def list_scan_results(
    client: APIClient,
    namespace: str,
    project_uuid: str,
    traverse: bool = False
) -> List[scan_result.ScanResult]:
    """
    List all ScanResult resources for a given project.

    Args:
        client: Authenticated APIClient instance
        namespace: Target namespace
        project_uuid: Project UUID to filter by
        traverse: If True, search child namespaces as well (uses parent namespace)

    Returns:
        List of ScanResult objects
    """
    try:
        # If traverse is enabled, use parent namespace to access child resources
        search_namespace = get_parent_namespace(namespace) if traverse else namespace
        
        if traverse:
            logger.info(
                f"Listing ScanResults for project {project_uuid} with traverse "
                f"(using parent namespace: {search_namespace})..."
            )
        else:
            logger.info(f"Listing ScanResults for project {project_uuid}...")
        
        # Build list parameters
        list_params = ListParameters(
            filter=f'meta.parent_uuid=="{project_uuid}"',
            include_child_namespaces=traverse if traverse else None,
            mask=None,
            page_size=None,
            page_token=None,
            sort_field=None,
            sort_order=None,
            count=None,
            from_date=None,
            to_date=None
        )
        
        # Use SDK to list scan results
        scan_results_list = scan_result.list_scan_results(
            client, search_namespace, list_params
        )
        
        logger.info(f"Found {len(scan_results_list)} ScanResults for project")
        return scan_results_list
    except Exception as e:
        logger.error(f"Error listing ScanResults: {e}")
        return []


def find_matching_scan_results(
    scan_results: List[scan_result.ScanResult],
    finding_create_time: datetime
) -> List[scan_result.ScanResult]:
    """
    Filter ScanResults where scan_start < finding.created < scan_end.

    Args:
        scan_results: List of ScanResult objects
        finding_create_time: Finding creation datetime

    Returns:
        List of matching ScanResult objects
    """
    matching_scans = []

    for scan_result_obj in scan_results:
        if not scan_result_obj.spec.start_time or not scan_result_obj.spec.end_time:
            logger.debug(
                f"Skipping scan {scan_result_obj.uuid} - missing "
                "start_time or end_time"
            )
            continue

        try:
            start_time = parse_datetime(scan_result_obj.spec.start_time)
            end_time = parse_datetime(scan_result_obj.spec.end_time)

            # Check if finding was created during this scan
            if start_time <= finding_create_time <= end_time:
                logger.info(
                    f"Found matching scan: {scan_result_obj.uuid} "
                    f"(start: {start_time}, end: {end_time})"
                )
                matching_scans.append(scan_result_obj)
        except ValueError as e:
            logger.warning(
                f"Error parsing datetime for scan {scan_result_obj.uuid}: {e}"
            )
            continue

    return matching_scans


def extract_scan_configs(
    scan_results: List[scan_result.ScanResult]
) -> List[Dict[str, Any]]:
    """
    Extract spec.environment.config from ScanResults.

    Args:
        scan_results: List of matching ScanResult objects

    Returns:
        List of scan config dictionaries
    """
    scan_configs = []

    for scan_result_obj in scan_results:
        config = {}
        if scan_result_obj.spec.environment and scan_result_obj.spec.environment.config:
            config = scan_result_obj.spec.environment.config

        scan_configs.append({
            'scan_uuid': scan_result_obj.uuid,
            'scan_name': scan_result_obj.meta.name if scan_result_obj.meta else None,
            'scan_start': scan_result_obj.spec.start_time,
            'scan_end': scan_result_obj.spec.end_time,
            'scan_config': config,
        })

    return scan_configs


def main():
    """Main function to find scan config for a finding."""
    parser = argparse.ArgumentParser(
        description='Find ScanConfig for a given Finding UUID'
    )
    parser.add_argument(
        '--namespace',
        required=True,
        help='Target namespace (e.g., "endor-solutions-tgowan.cockpit")'
    )
    parser.add_argument(
        '--finding-uuid',
        required=True,
        help='UUID of the finding to investigate'
    )
    parser.add_argument(
        '--output-format',
        choices=['json', 'yaml', 'pretty'],
        default='pretty',
        help='Output format (default: pretty)'
    )
    parser.add_argument(
        '--traverse',
        action='store_true',
        help='Search child namespaces as well (equivalent to --traverse flag)'
    )

    args = parser.parse_args()

    # Initialize API client
    try:
        client = APIClient()
    except ValueError as e:
        logger.error(f"Failed to initialize API client: {e}")
        logger.error(
            "Make sure ENDOR_API_CREDENTIALS_KEY and "
            "ENDOR_API_CREDENTIALS_SECRET are set"
        )
        sys.exit(1)

    # Step 1: Get Finding details
    logger.info(
        f"Getting Finding {args.finding_uuid} "
        f"{'with traverse' if args.traverse else ''}..."
    )
    finding_details = get_finding_details(
        client, args.namespace, args.finding_uuid, args.traverse
    )
    if not finding_details:
        logger.error("Failed to get finding details")
        sys.exit(1)

    # create_time is a string from the API, parse it
    finding_create_time_str = finding_details['create_time']
    if isinstance(finding_create_time_str, datetime):
        finding_create_time_str = finding_create_time_str.isoformat()
    finding_create_time = parse_datetime(finding_create_time_str)
    project_uuid = finding_details['project_uuid']

    # Step 2: List ScanResults for the project
    logger.info(
        f"Listing ScanResults for project {project_uuid} "
        f"{'with traverse' if args.traverse else ''}..."
    )
    scan_results = list_scan_results(
        client, args.namespace, project_uuid, args.traverse
    )

    if not scan_results:
        logger.warning("No ScanResults found for this project")
        sys.exit(0)

    # Step 3: Find matching ScanResults
    logger.info(
        f"Filtering ScanResults where scan overlaps "
        f"finding creation time ({finding_create_time})..."
    )
    matching_scans = find_matching_scan_results(
        scan_results, finding_create_time
    )

    if not matching_scans:
        logger.warning(
            "No ScanResults found that overlap with finding creation time"
        )
        sys.exit(0)

    # Step 4: Extract scan configs
    logger.info("Extracting ScanConfig from matching ScanResults...")
    scan_configs = extract_scan_configs(matching_scans)

    # Output results
    if args.output_format == 'json':
        output = json.dumps(scan_configs, indent=2, default=str)
        print(output)
    elif args.output_format == 'yaml':
        try:
            import yaml
            output = yaml.dump(scan_configs, default_flow_style=False)
            print(output)
        except ImportError:
            logger.error("PyYAML not installed. Install with: uv add pyyaml")
            sys.exit(1)
    else:  # pretty
        print("\n" + "=" * 80)
        print(f"Finding: {finding_details['finding_name']}")
        print(f"Finding UUID: {args.finding_uuid}")
        print(f"Finding Created: {finding_create_time}")
        print(f"Project UUID: {project_uuid}")
        print("=" * 80)
        print(f"\nFound {len(scan_configs)} matching ScanResult(s):\n")

        for i, config in enumerate(scan_configs, 1):
            print(f"Scan Result {i}:")
            print(f"  UUID: {config['scan_uuid']}")
            print(f"  Name: {config['scan_name']}")
            print(f"  Start: {config['scan_start']}")
            print(f"  End: {config['scan_end']}")
            print(f"  Scan Config:")
            print(json.dumps(config['scan_config'], indent=4, default=str))
            print()

    logger.info(f"Successfully found {len(scan_configs)} matching scan config(s)")


if __name__ == '__main__':
    main()

