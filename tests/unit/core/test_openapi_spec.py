"""OpenAPI spec parity tests.

Ensures every RESOURCE_REGISTRY resource has a corresponding path in the spec.
See docs/reference/resources.md and src/endorlabs/registry.py.
"""

import json
from pathlib import Path

import pytest

# attr_name -> OpenAPI path segment (must match registry and spec)
REGISTRY_ATTR_TO_PATH: dict[str, str] = {
    "namespaces": "namespaces",
    "projects": "projects",
    "findings": "findings",
    "repositories": "repositories",
    "repository_versions": "repository-versions",
    "policies": "policies",
    "authorization_policies": "authorization-policies",
    "package_versions": "package-versions",
    "package_licenses": "package-licenses",
    "dependency_metadata": "dependency-metadata",
    "installations": "installations",
    "scan_profiles": "scan-profiles",
    "scan_results": "scan-results",
    "linter_results": "linter-results",
    "metrics": "metrics",
    "semgrep_rules": "semgrep-rules",
    "api_keys": "api-keys",
    "audit_logs": "audit-logs",
    "finding_logs": "finding-logs",
}


def test_openapi_spec_paths_exist() -> None:
    """Every registry resource path exists in OpenAPI spec and has get (list)."""
    spec_path = (
        Path(__file__).resolve().parent.parent / ".endorlabs-context" / "openapi.json"
    )
    if not spec_path.exists():
        pytest.skip("OpenAPI spec not present (.endorlabs-context/openapi.json)")
    with open(spec_path, encoding="utf-8") as f:
        spec = json.load(f)
    paths = spec.get("paths", {})
    prefix = "/v1/namespaces/{tenant_meta.namespace}/"
    for attr_name, path_segment in REGISTRY_ATTR_TO_PATH.items():
        path_key = prefix + path_segment
        assert path_key in paths, f"Spec path missing for {attr_name}: {path_key}"
        assert "get" in paths[path_key], (
            f"Spec path {path_key} has no get for {attr_name}"
        )
