"""
Explore call paths in findings to understand call graph data.

Findings can contain reachable_paths which show the call graph paths
from your code to vulnerable methods in dependencies. This demonstrates
how call graphs are used in vulnerability analysis.
"""

import json
import os
import sys
from typing import Optional

from endor_cockpit.api_client import APIClient
from endor_cockpit.resources import finding
from endor_cockpit.types import ListParameters


def format_reachable_path(path: dict) -> dict:
    """Format a reachable path for display."""
    nodes = path.get("nodes", [])
    functions = []
    for node in nodes:
        func_ref = node.get("function_ref", {})
        namespace = func_ref.get("namespace", "")
        classname = func_ref.get("classname", "")
        func_name = func_ref.get("function_or_attribute_name", "")

        if classname and func_name:
            display_name = f"{classname}.{func_name}"
        elif func_name:
            display_name = func_name
        else:
            display_name = namespace.split(".")[-1] if namespace else "Unknown"

        functions.append(
            {
                "name": display_name,
                "package": node.get("package_version", "N/A").replace(
                    "pypi://", ""
                ).replace("npm://", ""),
                "namespace": namespace,
                "signature": func_ref.get("signature", "N/A"),
                "internal": node.get("internal", False),
            }
        )

    return {
        "path_length": len(nodes),
        "functions": functions,
        "vulnerable_function": (
            functions[-1]["name"] if functions else "N/A"
        ),
    }


def find_findings_with_call_paths(
    client: APIClient, namespace: str, limit: int = 10
) -> list:
    """Find findings that have reachable_paths (call graph data)."""
    # Filter for findings with reachable paths
    list_params = ListParameters(
        filter="spec.reachable_paths exists",
        page_size=limit,
    )
    return finding.list_findings(client, namespace, list_params)


def analyze_finding_call_paths(finding_obj) -> dict:
    """Analyze call paths in a finding."""
    result = {
        "finding_uuid": finding_obj.uuid,
        "finding_name": finding_obj.meta.name if finding_obj.meta else "N/A",
        "severity": finding_obj.spec.level.value if finding_obj.spec.level else "N/A",
        "call_graph_analysis_type": (
            finding_obj.spec.call_graph_analysis_type.value
            if finding_obj.spec.call_graph_analysis_type
            else "N/A"
        ),
        "has_reachable_paths": finding_obj.spec.reachable_paths is not None,
        "num_paths": (
            len(finding_obj.spec.reachable_paths)
            if finding_obj.spec.reachable_paths
            else 0
        ),
        "target_dependency": (
            finding_obj.spec.target_dependency_package_name
            if finding_obj.spec.target_dependency_package_name
            else "N/A"
        ),
        "paths": [],
    }

    if finding_obj.spec.reachable_paths:
        result["paths"] = [
            format_reachable_path(path)
            for path in finding_obj.spec.reachable_paths[:3]  # Show first 3 paths
        ]

    return result


def main():
    """Main function to explore call paths in findings."""
    # Get namespace from environment or command line
    namespace = os.getenv("ENDOR_NAMESPACE")
    if len(sys.argv) > 1:
        namespace = sys.argv[1]

    if not namespace:
        print(
            "Usage: python explore_finding_call_paths.py <namespace>\n"
            "Or set ENDOR_NAMESPACE environment variable.\n"
            "Example: python explore_finding_call_paths.py tenant.namespace"
        )
        sys.exit(1)

    print(f"Exploring call paths in findings from namespace: {namespace}\n")

    try:
        # Initialize client
        client = APIClient()

        # Find findings with call paths
        print("Searching for findings with call graph paths...")
        findings = find_findings_with_call_paths(client, namespace, limit=10)

        if not findings:
            print(f"No findings with call paths found in namespace '{namespace}'.")
            print(
                "\nCall paths are generated when:\n"
                "1. A full scan is run with call graph generation enabled\n"
                "2. Vulnerabilities are found in dependencies\n"
                "3. The vulnerable code is reachable from your application code\n"
                "\nTo generate call paths:\n"
                "1. Run: endorctl scan (full scan, not quick scan)\n"
                "2. Ensure your project uses a supported language\n"
                "3. Have vulnerabilities in dependencies that are actually used"
            )
            return

        print(f"Found {len(findings)} finding(s) with call paths:\n")

        # Analyze each finding
        for i, finding_obj in enumerate(findings, 1):
            analysis = analyze_finding_call_paths(finding_obj)
            print(f"{'=' * 70}")
            print(f"Finding {i}: {analysis['finding_name']}")
            print(f"{'=' * 70}")
            print(f"UUID: {analysis['finding_uuid']}")
            print(f"Severity: {analysis['severity']}")
            print(f"Call Graph Analysis Type: {analysis['call_graph_analysis_type']}")
            print(f"Target Dependency: {analysis['target_dependency']}")
            print(f"Number of Call Paths: {analysis['num_paths']}")
            print()

            # Show call paths
            if analysis["paths"]:
                print("Call Paths (showing first 3):")
                print("-" * 70)
                for j, path in enumerate(analysis["paths"], 1):
                    print(f"\n  Path {j}:")
                    print(f"    Length: {path['path_length']} functions")
                    print(f"    Vulnerable Function: {path['vulnerable_function']}")
                    print("    Function Chain:")
                    for k, func in enumerate(path["functions"], 1):
                        arrow = "  └─► " if k < len(path["functions"]) else "  └─► [VULNERABLE]"
                        node_type = "INTERNAL" if func.get("internal") else "EXTERNAL"
                        print(f"{arrow}{func['name']}")
                        print(f"      Package: {func['package']}")
                        print(f"      Type: {node_type}")
                        if func.get("signature") and func["signature"] != "N/A":
                            print(f"      Signature: {func['signature']}")
                        if func.get("namespace"):
                            print(f"      Namespace: {func['namespace']}")
                    print()
            print()

        # Show detailed JSON for first finding
        if findings:
            print("=" * 70)
            print("Detailed JSON structure for first finding:")
            print("=" * 70)
            first_analysis = analyze_finding_call_paths(findings[0])
            print(json.dumps(first_analysis, indent=2))

    except Exception as e:
        print(f"Error exploring call paths: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

