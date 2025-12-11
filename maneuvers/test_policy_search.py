#!/usr/bin/env python3
"""
Test script to troubleshoot policy search query issues.

This script:
1. Retrieves the test policy to understand its structure
2. Tests API filter equivalents for the three URL query strings
3. Investigates why dash in URL 1 causes search to fail
4. Tests custom tag searching capabilities
"""

import json
import logging
import os
import sys
from typing import List, Optional

from endor_cockpit.api_client import APIClient
from endor_cockpit.resources import policy
from endor_cockpit.resources.policy import Policy
from endor_cockpit.types import ListParameters

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def retrieve_test_policy(
    client: APIClient,
    namespace: str,
    policy_uuid: str
) -> Optional[Policy]:
    """Retrieve the test policy and document its structure."""
    logger.info(f"Retrieving policy {policy_uuid} from namespace {namespace}")
    try:
        policy_obj = policy.get_policy(client, namespace, policy_uuid)
        if policy_obj:
            logger.info(f"Found policy: {policy_obj.meta.name}")
            logger.info(f"  UUID: {policy_obj.uuid}")
            logger.info(f"  Tags: {policy_obj.meta.tags}")
            logger.info(f"  Description: {policy_obj.meta.description}")
            
            # Search for ticket ID in various fields
            ticket_id = "REL-1230239"
            fields_containing_ticket = []
            
            if ticket_id in policy_obj.meta.name:
                fields_containing_ticket.append("meta.name")
            if policy_obj.meta.description and ticket_id in policy_obj.meta.description:
                fields_containing_ticket.append("meta.description")
            if policy_obj.meta.tags:
                for tag in policy_obj.meta.tags:
                    if ticket_id in tag:
                        fields_containing_ticket.append(f"meta.tags: {tag}")
            
            logger.info(f"  Fields containing '{ticket_id}': {fields_containing_ticket}")
            
            # Print full policy structure for analysis
            logger.info("\nFull policy structure:")
            policy_dict = policy_obj.model_dump()
            print(json.dumps(policy_dict, indent=2, default=str))
            
            return policy_obj
        else:
            logger.error(f"Policy {policy_uuid} not found")
            return None
    except Exception as e:
        logger.error(f"Error retrieving policy: {e}", exc_info=True)
        return None


def test_filter_equivalents(
    client: APIClient,
    namespace: str,
    ticket_id: str = "REL-1230239"
) -> None:
    """Test API filter equivalents for the three URL query strings."""
    logger.info("\n" + "="*80)
    logger.info("Testing API Filter Equivalents")
    logger.info("="*80)
    
    # URL 1: filter.search=REL-1230239 (dash, doesn't work)
    logger.info("\n--- URL 1 Tests: REL-1230239 (with dash) ---")
    url1_filters = [
        f'meta.name matches "{ticket_id}"',
        f'meta.description matches "{ticket_id}"',
        f'meta.tags contains ["{ticket_id}"]',
        f'meta.name matches "REL.*1230239"',  # Regex for dash handling
        f'meta.name matches "REL-?1230239"',  # Optional dash
    ]
    
    for filter_expr in url1_filters:
        logger.info(f"\nTesting: {filter_expr}")
        try:
            list_params = ListParameters(filter=filter_expr)
            policies = policy.list_policies(
                client, namespace, list_params=list_params
            )
            logger.info(f"  Results: {len(policies)} policies found")
            if policies:
                for p in policies:
                    logger.info(f"    - {p.meta.name} (UUID: {p.uuid})")
        except Exception as e:
            logger.error(f"  Error: {e}")
    
    # URL 2: filter.search=REL%201230239 (space encoded, works)
    logger.info("\n--- URL 2 Tests: REL 1230239 (space instead of dash) ---")
    ticket_space = "REL 1230239"
    url2_filters = [
        f'meta.name matches "{ticket_space}"',
        f'meta.description matches "{ticket_space}"',
        f'meta.tags contains ["{ticket_space}"]',
    ]
    
    for filter_expr in url2_filters:
        logger.info(f"\nTesting: {filter_expr}")
        try:
            list_params = ListParameters(filter=filter_expr)
            policies = policy.list_policies(
                client, namespace, list_params=list_params
            )
            logger.info(f"  Results: {len(policies)} policies found")
            if policies:
                for p in policies:
                    logger.info(f"    - {p.meta.name} (UUID: {p.uuid})")
        except Exception as e:
            logger.error(f"  Error: {e}")
    
    # URL 3: filter.search=%5Bvuln%20ticket%20%3D%20REL-1230239%5D
    # Decodes to: [vuln ticket = REL-1230239]
    logger.info("\n--- URL 3 Tests: [vuln ticket = REL-1230239] (bracket notation) ---")
    url3_filters = [
        'meta.tags contains ["vuln ticket"]',
        'meta.tags contains ["REL-1230239"]',
        'meta.tags in ["vuln ticket", "REL-1230239"]',
        'meta.name matches "vuln ticket"',
        'meta.description matches "vuln ticket"',
    ]
    
    for filter_expr in url3_filters:
        logger.info(f"\nTesting: {filter_expr}")
        try:
            list_params = ListParameters(filter=filter_expr)
            policies = policy.list_policies(
                client, namespace, list_params=list_params
            )
            logger.info(f"  Results: {len(policies)} policies found")
            if policies:
                for p in policies:
                    logger.info(f"    - {p.meta.name} (UUID: {p.uuid})")
        except Exception as e:
            logger.error(f"  Error: {e}")


def test_custom_tag_search(
    client: APIClient,
    namespace: str,
    tag: str = "engineer_generated"
) -> None:
    """Test searching by custom policy tag."""
    logger.info("\n" + "="*80)
    logger.info(f"Testing Custom Tag Search: {tag}")
    logger.info("="*80)
    
    tag_filters = [
        f'meta.tags contains ["{tag}"]',
        f'meta.tags in ["{tag}"]',
        f'meta.tags contains ["{tag}"] and spec.policy_type==POLICY_TYPE_EXCEPTION',
    ]
    
    for filter_expr in tag_filters:
        logger.info(f"\nTesting: {filter_expr}")
        try:
            list_params = ListParameters(filter=filter_expr)
            policies = policy.list_policies(
                client, namespace, list_params=list_params
            )
            logger.info(f"  Results: {len(policies)} policies found")
            if policies:
                for p in policies[:5]:  # Show first 5
                    logger.info(f"    - {p.meta.name} (Tags: {p.meta.tags})")
        except Exception as e:
            logger.error(f"  Error: {e}")


def test_dash_handling(
    client: APIClient,
    namespace: str,
    ticket_id: str = "REL-1230239"
) -> None:
    """Investigate why dash in URL causes search to fail."""
    logger.info("\n" + "="*80)
    logger.info("Investigating Dash Handling")
    logger.info("="*80)
    
    # Test various dash encoding and regex patterns
    dash_tests = [
        # Exact match with dash
        f'meta.name == "{ticket_id}"',
        # Regex patterns
        f'meta.name matches "REL-1230239"',
        f'meta.name matches "REL.*1230239"',
        f'meta.name matches "REL-?1230239"',
        f'meta.name matches "REL[\\- ]1230239"',  # Dash or space
        # Contains
        f'meta.name contains "{ticket_id}"',
        # Try with escaped dash
        f'meta.name matches "REL\\-1230239"',
    ]
    
    for filter_expr in dash_tests:
        logger.info(f"\nTesting: {filter_expr}")
        try:
            list_params = ListParameters(filter=filter_expr)
            policies = policy.list_policies(
                client, namespace, list_params=list_params
            )
            logger.info(f"  Results: {len(policies)} policies found")
            if policies:
                for p in policies:
                    logger.info(f"    - {p.meta.name} (UUID: {p.uuid})")
        except Exception as e:
            logger.error(f"  Error: {e}")


def main():
    """Main execution function."""
    # Get configuration from environment
    namespace = os.getenv("ENDOR_NAMESPACE", "endor-solutions-tgowan.cockpit")
    policy_uuid = "692f5c0beb124423f4683ffc"
    
    if len(sys.argv) > 1:
        namespace = sys.argv[1]
    if len(sys.argv) > 2:
        policy_uuid = sys.argv[2]
    
    logger.info(f"Testing policy search in namespace: {namespace}")
    logger.info(f"Test policy UUID: {policy_uuid}")
    
    # Initialize client
    try:
        client = APIClient()
    except Exception as e:
        logger.error(f"Failed to initialize API client: {e}")
        sys.exit(1)
    
    # Step 1: Retrieve and analyze test policy
    test_policy = retrieve_test_policy(client, namespace, policy_uuid)
    if not test_policy:
        logger.error("Could not retrieve test policy. Exiting.")
        sys.exit(1)
    
    # Step 2: Test filter equivalents
    test_filter_equivalents(client, namespace)
    
    # Step 3: Test dash handling
    test_dash_handling(client, namespace)
    
    # Step 4: Test custom tag search
    test_custom_tag_search(client, namespace)
    
    logger.info("\n" + "="*80)
    logger.info("Testing Complete")
    logger.info("="*80)


if __name__ == "__main__":
    main()



