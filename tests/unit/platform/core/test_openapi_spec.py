"""OpenAPI spec parity tests.

Ensures every registry resource has a corresponding OpenAPI path and list method.
See docs/reference/resources.md and src/endorlabs/registry.py.
"""

import json
from pathlib import Path

import pytest

from endorlabs.registry import RESOURCE_REGISTRY

_REPO_ROOT = Path(__file__).resolve().parents[4]
_SPEC_PATH = _REPO_ROOT / ".endorlabs-context" / "openapiv2.swagger.json"


def test_openapi_spec_paths_exist() -> None:
    """Every registry resource path exists in OpenAPI spec and has list (get)."""
    if not _SPEC_PATH.exists():
        pytest.skip(f"OpenAPI spec not present ({_SPEC_PATH})")
    with open(_SPEC_PATH, encoding="utf-8") as f:
        spec = json.load(f)
    paths = spec.get("paths", {})
    prefix = "/v1/namespaces/{tenant_meta.namespace}/"
    for entry in RESOURCE_REGISTRY:
        path_key = prefix + entry.resource_name
        assert path_key in paths, f"Spec path missing for {entry.attr_name}: {path_key}"
        if "list" in entry.supported_ops:
            assert "get" in paths[path_key], (
                f"Spec path {path_key} has no get for {entry.attr_name}"
            )
