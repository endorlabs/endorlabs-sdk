#!/usr/bin/env python3
"""
Analyze OpenAPI specification to identify actual operation patterns for resources.
This script provides absolute truths about what operations are available.
"""

import json
import re
from collections import defaultdict
from pathlib import Path


def _extract_resource_from_path(path: str) -> str:
    """Extract resource name from API path."""
    # Try first pattern
    resource_match = re.search(
        r"/v1/namespaces/\{tenant_meta\.namespace\}/([^/]+)", path
    )
    if not resource_match:
        # Try second pattern
        resource_match = re.search(
            r"/v1/namespaces/\{object\.tenant_meta\.namespace\}/([^/]+)", path
        )

    return resource_match.group(1) if resource_match else None


def _categorize_operation(method: str, is_uuid_endpoint: bool) -> str:
    """Categorize operation based on method and endpoint type."""
    if is_uuid_endpoint:
        if method == "get":
            return "GET_BY_UUID"
        elif method == "patch":
            return "PATCH"
        elif method == "delete":
            return "DELETE"
        elif method == "put":
            return "PUT"
    else:
        if method == "get":
            return "GET_LIST"
        elif method == "post":
            return "POST"

    return None


def _analyze_path_operations(
    path: str, path_item: dict, resource_operations: dict, operation_patterns: dict
):
    """Analyze operations for a single path."""
    # Check if this is a namespaced resource path
    if not (
        "/v1/namespaces/{tenant_meta.namespace}/" in path
        or "/v1/namespaces/{object.tenant_meta.namespace}/" in path
    ):
        return

    # Extract resource name
    resource = _extract_resource_from_path(path)
    if not resource:
        return

    # Check if it's a UUID endpoint
    is_uuid_endpoint = "/{uuid}" in path

    # Analyze operations
    for method in ["get", "post", "patch", "delete", "put"]:
        if method in path_item:
            operation_type = _categorize_operation(method, is_uuid_endpoint)
            if operation_type:
                resource_operations[resource].add(operation_type)
                operation_patterns[
                    f"{method.upper()}_{'UUID' if is_uuid_endpoint else 'LIST'}"
                ] += 1


def analyze_openapi_spec(spec_file):
    """Analyze OpenAPI spec to find operation patterns."""
    with open(spec_file, "r", encoding="utf-8") as f:
        spec = json.load(f)

    # Track operations by resource type
    resource_operations = defaultdict(set)
    operation_patterns = defaultdict(int)

    # Analyze paths
    for path, path_item in spec.get("paths", {}).items():
        _analyze_path_operations(
            path, path_item, resource_operations, operation_patterns
        )

    return resource_operations, operation_patterns


def _print_operation_patterns(operation_patterns: dict):
    """Print overall operation patterns."""
    print("\n🎯 Overall Operation Patterns:")
    for pattern, count in sorted(operation_patterns.items()):
        print(f"  {pattern}: {count} resources")


def _calculate_operation_counts(resource_operations: dict) -> tuple:
    """Calculate operation counts and total resources."""
    operation_counts = defaultdict(int)
    for _resource, operations in resource_operations.items():
        for op in operations:
            operation_counts[op] += 1

    total_resources = len(resource_operations)
    return operation_counts, total_resources


def _print_operation_availability(operation_counts: dict, total_resources: int):
    """Print operation availability statistics."""
    print(f"\n📈 Operation Availability (out of {total_resources} resources):")

    for op_type in ["GET_LIST", "GET_BY_UUID", "POST", "PATCH", "DELETE"]:
        count = operation_counts[op_type]
        percentage = (count / total_resources) * 100 if total_resources > 0 else 0
        status = (
            "✅ UNIVERSAL"
            if percentage >= 95
            else "⚠️  PARTIAL"
            if percentage >= 50
            else "❌ LIMITED"
        )
        print(f"  {op_type}: {count}/{total_resources} ({percentage:.1f}%) {status}")


def _find_crud_resources(resource_operations: dict) -> list:
    """Find resources with complete CRUD operations."""
    crud_resources = []
    print("\n🔍 Resources with Complete CRUD Operations:")
    print("-" * 50)

    for resource, operations in resource_operations.items():
        has_crud = all(
            op in operations
            for op in ["GET_LIST", "GET_BY_UUID", "POST", "PATCH", "DELETE"]
        )
        if has_crud:
            crud_resources.append(resource)
            print(f"  ✅ {resource}")

    return crud_resources


def _print_missing_operations(resource_operations: dict):
    """Print resources missing operations."""
    print("\n⚠️  Resources Missing Operations:")
    print("-" * 50)

    for resource, operations in resource_operations.items():
        missing = []
        for op in ["GET_LIST", "GET_BY_UUID", "POST", "PATCH", "DELETE"]:
            if op not in operations:
                missing.append(op)

        if missing:
            print(f"  {resource}: Missing {', '.join(missing)}")


def _print_protocol_recommendations(operation_counts: dict, total_resources: int):
    """Print protocol recommendations based on operation availability."""
    print("\n📋 PROTOCOL RECOMMENDATIONS:")
    print("=" * 40)

    for op_type in ["GET_LIST", "GET_BY_UUID", "POST", "PATCH", "DELETE"]:
        count = operation_counts[op_type]
        is_universal = count >= total_resources * 0.95

        if is_universal:
            print(f"✅ {op_type}: Universal - Include in all resource protocols")
        else:
            print(f"⚠️  {op_type}: Not universal - Check per resource")


def _save_analysis_results(
    resource_operations: dict,
    operation_patterns: dict,
    operation_counts: dict,
    crud_resources: list,
    total_resources: int,
):
    """Save detailed analysis results to file."""
    results_file = Path(".workspace/api_operation_analysis.json")
    with open(results_file, "w") as f:
        json.dump(
            {
                "resource_operations": {
                    k: list(v) for k, v in resource_operations.items()
                },
                "operation_patterns": dict(operation_patterns),
                "operation_counts": dict(operation_counts),
                "crud_resources": crud_resources,
                "total_resources": total_resources,
            },
            f,
            indent=2,
        )

    print(f"\n💾 Detailed results saved to: {results_file}")


def generate_operation_analysis():
    """Generate comprehensive operation analysis."""
    spec_file = Path(".workspace/downloads/openapi-swagger.json")
    if not spec_file.exists():
        print(
            "❌ OpenAPI spec file not found. Run 'uv run python -m holocron sync' "
            "first."
        )
        return

    print("🔍 Analyzing OpenAPI specification for operation patterns...")

    resource_operations, operation_patterns = analyze_openapi_spec(spec_file)

    print("\n📊 OPERATION PATTERN ANALYSIS")
    print("=" * 50)

    # Print analysis sections
    _print_operation_patterns(operation_patterns)

    print("\n✅ ABSOLUTE TRUTHS:")
    print("=" * 30)

    operation_counts, total_resources = _calculate_operation_counts(resource_operations)
    _print_operation_availability(operation_counts, total_resources)

    crud_resources = _find_crud_resources(resource_operations)
    print(
        f"\n📊 Summary: {len(crud_resources)}/{total_resources} resources have "
        "complete CRUD"
    )

    _print_missing_operations(resource_operations)
    _print_protocol_recommendations(operation_counts, total_resources)
    _save_analysis_results(
        resource_operations,
        operation_patterns,
        operation_counts,
        crud_resources,
        total_resources,
    )

    return resource_operations, operation_patterns


if __name__ == "__main__":
    generate_operation_analysis()
