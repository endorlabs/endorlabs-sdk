#!/usr/bin/env python3
"""
Analyze OpenAPI specification to identify actual operation patterns for resources.
This script provides absolute truths about what operations are available.
"""

import json
import re
from collections import defaultdict
from pathlib import Path


def analyze_openapi_spec(spec_file):
    """Analyze OpenAPI spec to find operation patterns."""

    with open(spec_file, 'r', encoding='utf-8') as f:
        spec = json.load(f)

    # Track operations by resource type
    resource_operations = defaultdict(set)
    operation_patterns = defaultdict(int)

    # Analyze paths
    for path, path_item in spec.get('paths', {}).items():
        # Extract resource name from path
        # Pattern: /v1/namespaces/{tenant_meta.namespace}/{resource}
        # Pattern: /v1/namespaces/{tenant_meta.namespace}/{resource}/{uuid}

        if '/v1/namespaces/{tenant_meta.namespace}/' in path or '/v1/namespaces/{object.tenant_meta.namespace}/' in path:
            # Extract resource name from either pattern
            resource_match = re.search(r'/v1/namespaces/\{tenant_meta\.namespace\}/([^/]+)', path)
            if not resource_match:
                resource_match = re.search(r'/v1/namespaces/\{object\.tenant_meta\.namespace\}/([^/]+)', path)
            if resource_match:
                resource = resource_match.group(1)

                # Check if it's a UUID endpoint
                is_uuid_endpoint = '/{uuid}' in path

                # Analyze operations
                for method in ['get', 'post', 'patch', 'delete', 'put']:
                    if method in path_item:
                        operation = path_item[method]
                        summary = operation.get('summary', '')

                        # Categorize operations
                        if is_uuid_endpoint:
                            if method == 'get':
                                resource_operations[resource].add('GET_BY_UUID')
                            elif method == 'patch':
                                resource_operations[resource].add('PATCH')
                            elif method == 'delete':
                                resource_operations[resource].add('DELETE')
                            elif method == 'put':
                                resource_operations[resource].add('PUT')
                        else:
                            if method == 'get':
                                resource_operations[resource].add('GET_LIST')
                            elif method == 'post':
                                resource_operations[resource].add('POST')

                        operation_patterns[f"{method.upper()}_{'UUID' if is_uuid_endpoint else 'LIST'}"] += 1

    return resource_operations, operation_patterns

def generate_operation_analysis():
    """Generate comprehensive operation analysis."""

    spec_file = Path('.workspace/downloads/openapi-swagger.json')
    if not spec_file.exists():
        print("❌ OpenAPI spec file not found. Run 'python -m holocron sync' first.")
        return

    print("🔍 Analyzing OpenAPI specification for operation patterns...")

    resource_operations, operation_patterns = analyze_openapi_spec(spec_file)

    print("\n📊 OPERATION PATTERN ANALYSIS")
    print("=" * 50)

    # Overall operation patterns
    print("\n🎯 Overall Operation Patterns:")
    for pattern, count in sorted(operation_patterns.items()):
        print(f"  {pattern}: {count} resources")

    # Find absolute truths
    print("\n✅ ABSOLUTE TRUTHS:")
    print("=" * 30)

    # Count resources with each operation type
    operation_counts = defaultdict(int)
    for resource, operations in resource_operations.items():
        for op in operations:
            operation_counts[op] += 1

    total_resources = len(resource_operations)

    print(f"\n📈 Operation Availability (out of {total_resources} resources):")

    for op_type in ['GET_LIST', 'GET_BY_UUID', 'POST', 'PATCH', 'DELETE']:
        count = operation_counts[op_type]
        percentage = (count / total_resources) * 100 if total_resources > 0 else 0
        status = "✅ UNIVERSAL" if percentage >= 95 else "⚠️  PARTIAL" if percentage >= 50 else "❌ LIMITED"
        print(f"  {op_type}: {count}/{total_resources} ({percentage:.1f}%) {status}")

    # Find resources with complete CRUD
    print("\n🔍 Resources with Complete CRUD Operations:")
    print("-" * 50)

    crud_resources = []
    for resource, operations in resource_operations.items():
        has_crud = all(op in operations for op in ['GET_LIST', 'GET_BY_UUID', 'POST', 'PATCH', 'DELETE'])
        if has_crud:
            crud_resources.append(resource)
            print(f"  ✅ {resource}")

    print(f"\n📊 Summary: {len(crud_resources)}/{total_resources} resources have complete CRUD")

    # Find resources missing operations
    print("\n⚠️  Resources Missing Operations:")
    print("-" * 50)

    for resource, operations in resource_operations.items():
        missing = []
        for op in ['GET_LIST', 'GET_BY_UUID', 'POST', 'PATCH', 'DELETE']:
            if op not in operations:
                missing.append(op)

        if missing:
            print(f"  {resource}: Missing {', '.join(missing)}")

    # Generate protocol recommendations
    print("\n📋 PROTOCOL RECOMMENDATIONS:")
    print("=" * 40)

    if operation_counts['GET_LIST'] >= total_resources * 0.95:
        print("✅ GET_LIST: Universal - Include in all resource protocols")
    else:
        print("⚠️  GET_LIST: Not universal - Check per resource")

    if operation_counts['GET_BY_UUID'] >= total_resources * 0.95:
        print("✅ GET_BY_UUID: Universal - Include in all resource protocols")
    else:
        print("⚠️  GET_BY_UUID: Not universal - Check per resource")

    if operation_counts['POST'] >= total_resources * 0.95:
        print("✅ POST: Universal - Include in all resource protocols")
    else:
        print("⚠️  POST: Not universal - Check per resource")

    if operation_counts['PATCH'] >= total_resources * 0.95:
        print("✅ PATCH: Universal - Include in all resource protocols")
    else:
        print("⚠️  PATCH: Not universal - Check per resource")

    if operation_counts['DELETE'] >= total_resources * 0.95:
        print("✅ DELETE: Universal - Include in all resource protocols")
    else:
        print("⚠️  DELETE: Not universal - Check per resource")

    # Save detailed results
    results_file = Path('.workspace/api_operation_analysis.json')
    with open(results_file, 'w') as f:
        json.dump({
            'resource_operations': {k: list(v) for k, v in resource_operations.items()},
            'operation_patterns': dict(operation_patterns),
            'operation_counts': dict(operation_counts),
            'crud_resources': crud_resources,
            'total_resources': total_resources
        }, f, indent=2)

    print(f"\n💾 Detailed results saved to: {results_file}")

    return resource_operations, operation_patterns

if __name__ == "__main__":
    generate_operation_analysis()
