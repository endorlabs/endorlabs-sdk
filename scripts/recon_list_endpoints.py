#!/usr/bin/env python3
"""
Reconnaissance script to test all list endpoints from OpenAPI spec.

This script:
1. Parses the OpenAPI spec to find all list endpoints
2. Tests each endpoint with traverse enabled
3. Captures response structure and attributes
4. Outputs a comprehensive report of objects and attributes
"""

import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
from collections import defaultdict

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from endor_cockpit.api_client import APIClient


class EndpointRecon:
    """Reconnaissance tool for testing list endpoints."""

    def __init__(self, openapi_path: str, namespace: str):
        """Initialize with OpenAPI spec path and namespace."""
        self.openapi_path = Path(openapi_path)
        self.namespace = namespace
        self.client = APIClient()
        self.results: List[Dict[str, Any]] = []
        self.spec: Dict[str, Any] = {}

    def load_openapi_spec(self) -> bool:
        """Load OpenAPI specification."""
        try:
            with open(self.openapi_path, "r", encoding="utf-8") as f:
                self.spec = json.load(f)
            print(f"✅ Loaded OpenAPI spec: {len(self.spec.get('paths', {}))} paths")
            return True
        except Exception as e:
            print(f"❌ Failed to load OpenAPI spec: {e}")
            return False

    def find_list_endpoints(self) -> List[Dict[str, Any]]:
        """Find all list endpoints from OpenAPI spec.
        
        Selection criteria:
        1. GET method
        2. Path contains "/namespaces/" (namespaced resources)
        3. OperationId contains "List" (case-insensitive)
        4. Path pattern: /v1/namespaces/{...}/resource_name (no UUID in path)
        5. Not in blacklist (e.g., "archived")
        """
        # Blacklist of resource names to skip
        blacklist = {"archived"}
        # Also blacklist any resource ending in "-logs" except scan-related logs
        log_whitelist = {"scan-logs"}  # Allow scan logs
        
        endpoints = []
        paths = self.spec.get("paths", {})

        for path, methods in paths.items():
            # Look for GET methods
            if "get" not in methods:
                continue
                
            get_method = methods["get"]
            operation_id = get_method.get("operationId", "").lower()
            summary = get_method.get("summary", "").lower()

            # Check if it's a list operation
            # Must have "list" in operationId or summary, and be namespaced
            is_list_operation = (
                "list" in operation_id or "list" in summary
            ) and "/namespaces/" in path

            if is_list_operation:
                # Extract resource name from path
                # Pattern: /v1/namespaces/{tenant_meta.namespace}/resource_name
                # Skip paths with UUIDs (those are GET by UUID, not list)
                path_parts = path.split("/")
                
                # Only check the LAST part for parameters (skip GET by UUID endpoints)
                # Don't check path_parts[-2:] because {tenant_meta.namespace} is always in the path
                if len(path_parts) >= 4:
                    resource_name = path_parts[-1]
                    
                    # Skip if resource_name is a parameter placeholder (e.g., {uuid})
                    if resource_name.startswith("{") and resource_name.endswith("}"):
                        continue
                    
                    # Skip if resource_name is in blacklist
                    if resource_name.lower() in blacklist:
                        continue
                    
                    # Skip if resource_name ends with "-logs" (except whitelisted)
                    if resource_name.lower().endswith("-logs"):
                        if resource_name.lower() not in log_whitelist:
                            continue

                    endpoints.append(
                        {
                            "path": path,
                            "method": "GET",
                            "operation_id": get_method.get("operationId"),
                            "summary": get_method.get("summary", ""),
                            "resource_name": resource_name,
                            "tags": get_method.get("tags", []),
                        }
                    )

        # Sort by resource name
        endpoints.sort(key=lambda x: x["resource_name"])
        print(f"📋 Found {len(endpoints)} list endpoints")
        return endpoints

    def extract_attributes(self, obj: Dict[str, Any], prefix: str = "") -> Set[str]:
        """Recursively extract all attribute paths from an object."""
        attributes = set()

        if not isinstance(obj, dict):
            return attributes

        for key, value in obj.items():
            attr_path = f"{prefix}.{key}" if prefix else key
            attributes.add(attr_path)

            if isinstance(value, dict):
                attributes.update(self.extract_attributes(value, attr_path))
            elif isinstance(value, list) and value and isinstance(value[0], dict):
                # Sample first item in array
                attributes.update(self.extract_attributes(value[0], attr_path))

        return attributes

    def test_endpoint(
        self, endpoint: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Test a single list endpoint with traverse enabled."""
        path = endpoint["path"]
        resource_name = endpoint["resource_name"]

        # Replace path parameter with actual namespace
        # Pattern: /v1/namespaces/{tenant_meta.namespace}/resource_name
        test_path = path.replace("{tenant_meta.namespace}", self.namespace)

        print(f"\n🔍 Testing: {resource_name}")
        print(f"   Path: {test_path}")

        result = {
            "resource_name": resource_name,
            "path": path,
            "operation_id": endpoint["operation_id"],
            "summary": endpoint["summary"],
            "tags": endpoint["tags"],
            "status": "unknown",
            "status_code": None,
            "error": None,
            "count": 0,
            "attributes": set(),
            "sample_object": None,
        }

        try:
            # Test with traverse enabled
            params = {
                "list_parameters.traverse": "true",
            }

            response = self.client.get(test_path, params=params)
            result["status_code"] = response.status_code

            if response.status_code == 200:
                data = response.json()

                # Extract objects from response
                objects = []
                if "list" in data and "objects" in data["list"]:
                    objects = data["list"]["objects"]
                elif "objects" in data:
                    objects = data["objects"]

                result["count"] = len(objects)
                result["status"] = "success"

                if objects:
                    # Extract attributes from first object
                    sample = objects[0]
                    result["sample_object"] = sample
                    result["attributes"] = self.extract_attributes(sample)

                    print(f"   ✅ Success: {len(objects)} object(s) returned")
                    print(f"   📊 Attributes: {len(result['attributes'])} found")
                else:
                    print(f"   ⚠️  Success but no objects returned")
                    result["status"] = "empty"

            elif response.status_code == 403:
                result["status"] = "forbidden"
                result["error"] = "403 Forbidden - Insufficient permissions"
                print(f"   🔒 Forbidden (403) - Insufficient permissions")

            elif response.status_code == 404:
                result["status"] = "not_found"
                result["error"] = "404 Not Found"
                print(f"   ❌ Not Found (404)")

            else:
                result["status"] = "error"
                try:
                    error_data = response.json()
                    result["error"] = str(error_data)
                except:
                    result["error"] = response.text[:200]
                print(f"   ❌ Error ({response.status_code}): {result['error'][:100]}")

        except Exception as e:
            result["status"] = "exception"
            result["error"] = str(e)
            print(f"   💥 Exception: {type(e).__name__}: {e}")
            # Continue gracefully - don't raise, just log the error

        return result

    def run_recon(self) -> Dict[str, Any]:
        """Run full reconnaissance on all list endpoints."""
        if not self.load_openapi_spec():
            return {"error": "Failed to load OpenAPI spec"}

        endpoints = self.find_list_endpoints()

        print(f"\n🚀 Starting reconnaissance on {len(endpoints)} endpoints...")
        print(f"   Namespace: {self.namespace}")
        print(f"   Traverse: enabled\n")

        for i, endpoint in enumerate(endpoints, 1):
            try:
                print(f"[{i}/{len(endpoints)}] ", end="")
                result = self.test_endpoint(endpoint)
                if result:
                    self.results.append(result)
            except Exception as e:
                # Fail gracefully - log error but continue with other endpoints
                print(f"\n   ⚠️  Unexpected error processing endpoint: {e}")
                error_result = {
                    "resource_name": endpoint.get("resource_name", "unknown"),
                    "path": endpoint.get("path", "unknown"),
                    "operation_id": endpoint.get("operation_id", "unknown"),
                    "status": "exception",
                    "error": f"Unexpected error: {str(e)}",
                    "count": 0,
                    "attributes": set(),
                }
                self.results.append(error_result)

        return self.generate_report()

    def generate_report(self) -> Dict[str, Any]:
        """Generate comprehensive report from results."""
        report = {
            "summary": {
                "total_endpoints": len(self.results),
                "successful": len([r for r in self.results if r["status"] == "success"]),
                "empty": len([r for r in self.results if r["status"] == "empty"]),
                "forbidden": len([r for r in self.results if r["status"] == "forbidden"]),
                "not_found": len([r for r in self.results if r["status"] == "not_found"]),
                "errors": len([r for r in self.results if r["status"] in ["error", "exception"]]),
            },
            "endpoints": [],
            "attributes_by_resource": {},
            "all_attributes": set(),
        }

        # Process each result
        for result in self.results:
            endpoint_info = {
                "resource_name": result["resource_name"],
                "path": result["path"],
                "operation_id": result["operation_id"],
                "summary": result["summary"],
                "status": result["status"],
                "count": result["count"],
                "attribute_count": len(result["attributes"]),
                "attributes": sorted(result["attributes"]),
            }

            if result["error"]:
                endpoint_info["error"] = result["error"]

            report["endpoints"].append(endpoint_info)

            # Collect attributes
            if result["attributes"]:
                report["attributes_by_resource"][result["resource_name"]] = sorted(
                    result["attributes"]
                )
                report["all_attributes"].update(result["attributes"])

        report["all_attributes"] = sorted(report["all_attributes"])

        return report

    def print_report(self, report: Dict[str, Any]):
        """Print formatted report."""
        print("\n" + "=" * 80)
        print("RECONNAISSANCE REPORT")
        print("=" * 80)

        summary = report["summary"]
        print(f"\n📊 SUMMARY:")
        print(f"   Total Endpoints Tested: {summary['total_endpoints']}")
        print(f"   ✅ Successful: {summary['successful']}")
        print(f"   ⚠️  Empty: {summary['empty']}")
        print(f"   🔒 Forbidden: {summary['forbidden']}")
        print(f"   ❌ Not Found: {summary['not_found']}")
        print(f"   💥 Errors: {summary['errors']}")

        print(f"\n📋 ENDPOINTS BY STATUS:")
        print("\n✅ SUCCESSFUL ENDPOINTS:")
        for endpoint in report["endpoints"]:
            if endpoint["status"] == "success":
                print(
                    f"   {endpoint['resource_name']:30} | "
                    f"Count: {endpoint['count']:3} | "
                    f"Attributes: {endpoint['attribute_count']:3}"
                )

        if summary["empty"] > 0:
            print("\n⚠️  EMPTY ENDPOINTS (successful but no data):")
            for endpoint in report["endpoints"]:
                if endpoint["status"] == "empty":
                    print(f"   {endpoint['resource_name']:30} | {endpoint['path']}")

        if summary["forbidden"] > 0:
            print("\n🔒 FORBIDDEN ENDPOINTS:")
            for endpoint in report["endpoints"]:
                if endpoint["status"] == "forbidden":
                    print(f"   {endpoint['resource_name']:30} | {endpoint['path']}")

        if summary["not_found"] > 0:
            print("\n❌ NOT FOUND ENDPOINTS:")
            for endpoint in report["endpoints"]:
                if endpoint["status"] == "not_found":
                    print(f"   {endpoint['resource_name']:30} | {endpoint['path']}")

        if summary["errors"] > 0:
            print("\n💥 ERROR ENDPOINTS:")
            for endpoint in report["endpoints"]:
                if endpoint["status"] in ["error", "exception"]:
                    error_msg = endpoint.get("error", "Unknown error")[:100]
                    print(
                        f"   {endpoint['resource_name']:30} | "
                        f"{endpoint['status']:10} | {error_msg}"
                    )

        print(f"\n📦 ATTRIBUTES BY RESOURCE:")
        for resource, attributes in sorted(report["attributes_by_resource"].items()):
            print(f"\n   {resource} ({len(attributes)} attributes):")
            for attr in attributes[:20]:  # Show first 20
                print(f"      - {attr}")
            if len(attributes) > 20:
                print(f"      ... and {len(attributes) - 20} more")

        print(f"\n🔍 ALL UNIQUE ATTRIBUTES ({len(report['all_attributes'])} total):")
        for attr in sorted(report["all_attributes"])[:50]:  # Show first 50
            print(f"   - {attr}")
        if len(report["all_attributes"]) > 50:
            print(f"   ... and {len(report['all_attributes']) - 50} more")

        print("\n" + "=" * 80)

    def save_report(self, report: Dict[str, Any], output_path: str):
        """Save report to JSON file."""
        # Convert sets to lists for JSON serialization
        json_report = json.loads(
            json.dumps(report, default=lambda x: list(x) if isinstance(x, set) else x)
        )

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(json_report, f, indent=2)

        print(f"\n💾 Report saved to: {output_path}")


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Reconnaissance script for testing all list endpoints"
    )
    parser.add_argument(
        "--openapi",
        default="external_docs/openapi-swagger.json",
        help="Path to OpenAPI spec file",
    )
    parser.add_argument(
        "--namespace",
        default=os.getenv("ENDOR_NAMESPACE", "endor-solutions-tgowan"),
        help="Namespace to test (default: from ENDOR_NAMESPACE env var)",
    )
    parser.add_argument(
        "--output",
        default="recon_report.json",
        help="Output JSON file path",
    )

    args = parser.parse_args()

    recon = EndpointRecon(args.openapi, args.namespace)
    report = recon.run_recon()

    if "error" in report:
        print(f"❌ Error: {report['error']}")
        return 1

    recon.print_report(report)
    recon.save_report(report, args.output)

    return 0


if __name__ == "__main__":
    sys.exit(main())

