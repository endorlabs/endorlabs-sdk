#!/usr/bin/env python3
"""
Debug script to test DependencyMetadata query performance.

This script isolates the query to identify performance bottlenecks,
including retry/backoff behavior, pagination, and API response times.
"""

import argparse
import logging
import os
import sys
import time
from typing import Any, Dict

# Add the src directory to the path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from endor_cockpit.api_client import APIClient
from endor_cockpit.resources import dependency_metadata
from endor_cockpit.types import ListParameters
from endor_cockpit.utils.traversal import create_traverse_params

# Configure detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Enable requests logging to see HTTP details
logging.getLogger("urllib3").setLevel(logging.DEBUG)
logging.getLogger("requests").setLevel(logging.DEBUG)


def test_dependency_metadata_query(
    client: APIClient,
    tenant_namespace: str,
    use_traverse: bool = True,
    page_size: Optional[int] = None,
    max_pages: int = None,
) -> Dict[str, Any]:
    """
    Test DependencyMetadata query with detailed timing and metrics.
    
    Returns:
        Dictionary with performance metrics and results
    """
    logger.info("=" * 80)
    logger.info("DEPENDENCY METADATA PERFORMANCE TEST")
    logger.info("=" * 80)
    
    # Check API client configuration
    logger.info("\n📊 API CLIENT CONFIGURATION:")
    logger.info(f"   Base URL: {client.base_url}")
    adapter = client.session.adapters.get('https://')
    if adapter:
        retry = adapter.max_retries
        logger.info(f"   Max retries: {retry.total}")
        logger.info(f"   Backoff factor: {retry.backoff_factor}")
        logger.info(f"   Status forcelist: {retry.status_forcelist}")
        logger.info(f"   Backoff calculation: delay = backoff_factor * (2 ^ retry_count)")
        logger.info(f"      Retry 1: {retry.backoff_factor * (2 ** 0):.1f}s")
        logger.info(f"      Retry 2: {retry.backoff_factor * (2 ** 1):.1f}s")
        logger.info(f"      Retry 3: {retry.backoff_factor * (2 ** 2):.1f}s")
        logger.info(f"      Retry 4: {retry.backoff_factor * (2 ** 3):.1f}s")
    logger.info(f"   Rate limit delay: {client.rate_limit_delay}")
    
    # Prepare query parameters
    # Use API default page size (don't override) - max_pages is the control mechanism
    if use_traverse:
        list_params = create_traverse_params(page_size=page_size)
        logger.info(f"\n🔍 QUERY CONFIGURATION:")
        logger.info(f"   Traverse: True (tenant-wide query)")
        logger.info(f"   Page size: {page_size or 'API default (typically 100)'}")
        logger.info(f"   Max pages: {max_pages or 'unlimited'}")
    else:
        list_params = ListParameters(page_size=page_size, traverse=False)
        logger.info(f"\n🔍 QUERY CONFIGURATION:")
        logger.info(f"   Traverse: False (namespace-scoped)")
        logger.info(f"   Page size: {page_size or 'API default (typically 100)'}")
        logger.info(f"   Max pages: {max_pages or 'unlimited'}")
    
    # Track metrics
    start_time = time.time()
    page_times = []
    total_items = 0
    page_count = 0
    
    try:
        logger.info(f"\n🚀 Starting query at {time.strftime('%H:%M:%S')}")
        logger.info(f"   Namespace: {tenant_namespace}")
        
        # Make the query
        query_start = time.time()
        results = dependency_metadata.list_dependency_metadata(
            client, tenant_namespace, list_params
        )
        query_end = time.time()
        
        total_items = len(results)
        query_duration = query_end - query_start
        
        logger.info(f"\n✅ QUERY COMPLETED")
        logger.info(f"   Total items: {total_items}")
        logger.info(f"   Total duration: {query_duration:.2f} seconds")
        logger.info(f"   Items per second: {total_items / query_duration:.2f}" if query_duration > 0 else "   N/A")
        
        # Sample first few items
        if results:
            logger.info(f"\n📦 SAMPLE RESULTS (first 3):")
            for i, dep in enumerate(results[:3], 1):
                dep_data = dep.spec.dependency_data if dep.spec else None
                importer_data = dep.spec.importer_data if dep.spec else None
                logger.info(f"   {i}. Dependency: {dep_data.package_name if dep_data else 'N/A'}")
                logger.info(f"      Importer: {importer_data.package_name if importer_data else 'N/A'}")
                logger.info(f"      UUID: {dep.uuid[:16]}...")
        
        return {
            "status": "success",
            "total_items": total_items,
            "duration_seconds": query_duration,
            "items_per_second": total_items / query_duration if query_duration > 0 else 0,
            "page_count": page_count,
            "sample_count": min(3, total_items),
        }
        
    except Exception as e:
        error_duration = time.time() - start_time
        logger.error(f"\n❌ QUERY FAILED after {error_duration:.2f} seconds")
        logger.error(f"   Error: {type(e).__name__}: {e}")
        import traceback
        logger.error(f"   Traceback:\n{traceback.format_exc()}")
        
        return {
            "status": "error",
            "error": str(e),
            "error_type": type(e).__name__,
            "duration_seconds": error_duration,
        }


def test_direct_api_call(
    client: APIClient,
    tenant_namespace: str,
    use_traverse: bool = True,
    page_size: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Test direct API call to see raw response and timing.
    """
    logger.info("\n" + "=" * 80)
    logger.info("DIRECT API CALL TEST (Single Page)")
    logger.info("=" * 80)
    
    url = f"v1/namespaces/{tenant_namespace}/dependency-metadata"
    params = {
        "list_parameters.traverse": str(use_traverse).lower(),
    }
    # Only add page_size if explicitly provided (let API use default)
    if page_size is not None:
        params["list_parameters.page_size"] = str(page_size)
    
    logger.info(f"\n📡 API REQUEST:")
    logger.info(f"   Full URL: {client.base_url}/{url}")
    logger.info(f"   Params: {params}")
    logger.info(f"   Expected endpoint: /v1/namespaces/{tenant_namespace}/dependency-metadata")
    
    start_time = time.time()
    logger.info(f"   Request started at: {time.strftime('%H:%M:%S')}")
    try:
        response = client.get(url, params=params)
        duration = time.time() - start_time
        
        logger.info(f"\n📥 API RESPONSE:")
        logger.info(f"   Status: {response.status_code}")
        logger.info(f"   Duration: {duration:.2f} seconds")
        logger.info(f"   Headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            data = response.json()
            objects = data.get("list", {}).get("objects", [])
            logger.info(f"   Objects in response: {len(objects)}")
            logger.info(f"   Has next_page_token: {'next_page_token' in str(data)}")
            
            return {
                "status": "success",
                "status_code": response.status_code,
                "duration_seconds": duration,
                "object_count": len(objects),
            }
        else:
            logger.error(f"   Response text: {response.text[:500]}")
            return {
                "status": "error",
                "status_code": response.status_code,
                "duration_seconds": duration,
            }
            
    except Exception as e:
        duration = time.time() - start_time
        logger.error(f"\n❌ API CALL FAILED after {duration:.2f} seconds")
        logger.error(f"   Error: {type(e).__name__}: {e}")
        return {
            "status": "error",
            "error": str(e),
            "duration_seconds": duration,
        }


def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(
        description="Debug DependencyMetadata query performance"
    )
    parser.add_argument(
        "--tenant-namespace",
        type=str,
        default=os.getenv("ENDOR_NAMESPACE"),
        help="Root tenant namespace (default: ENDOR_NAMESPACE env var)",
    )
    parser.add_argument(
        "--no-traverse",
        action="store_true",
        help="Disable traverse (namespace-scoped query only)",
    )
    parser.add_argument(
        "--page-size",
        type=int,
        default=None,
        help="Page size for pagination (default: None = use API default, typically 100)",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=None,
        help="Maximum pages to fetch (default: unlimited)",
    )
    parser.add_argument(
        "--direct-api",
        action="store_true",
        help="Test direct API call first (single page)",
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

    # Test direct API call first if requested
    if args.direct_api:
        logger.info("\n" + "=" * 80)
        logger.info("STEP 1: DIRECT API CALL TEST")
        logger.info("=" * 80)
        direct_result = test_direct_api_call(
            client,
            args.tenant_namespace,
            use_traverse=not args.no_traverse,
            page_size=args.page_size,
        )
        logger.info(f"\n📊 Direct API Result: {direct_result}")

    # Test full query
    logger.info("\n" + "=" * 80)
    logger.info("STEP 2: FULL QUERY TEST")
    logger.info("=" * 80)
    result = test_dependency_metadata_query(
        client,
        args.tenant_namespace,
        use_traverse=not args.no_traverse,
        page_size=args.page_size,
        max_pages=args.max_pages,
    )

    # Summary
    logger.info("\n" + "=" * 80)
    logger.info("PERFORMANCE SUMMARY")
    logger.info("=" * 80)
    logger.info(f"Status: {result.get('status', 'unknown')}")
    if result.get("status") == "success":
        logger.info(f"Total items: {result.get('total_items', 0)}")
        logger.info(f"Duration: {result.get('duration_seconds', 0):.2f} seconds")
        logger.info(f"Items/second: {result.get('items_per_second', 0):.2f}")
    else:
        logger.error(f"Error: {result.get('error', 'Unknown error')}")


if __name__ == "__main__":
    main()

