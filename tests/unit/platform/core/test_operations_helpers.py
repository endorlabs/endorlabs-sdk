"""Focused tests for operations helper branches."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from endorlabs.core.exceptions import ValidationError
from endorlabs.operations import (
    _load_generated_mutability_by_resource_name,
    validate_namespace,
)


@pytest.mark.parametrize(
    "namespace",
    ["tenant", "tenant.child", "tenant_child-1", "TENANT.Prod_1"],
)
def test_validate_namespace_accepts_canonical_values(namespace: str) -> None:
    assert validate_namespace(namespace) == namespace


@pytest.mark.parametrize("namespace", ["", "tenant/child", "../tenant", "tenant child"])
def test_validate_namespace_rejects_unsafe_values(namespace: str) -> None:
    with pytest.raises(ValidationError, match="Invalid namespace format"):
        validate_namespace(namespace)


def test_load_generated_mutability_filters_non_string_entries() -> None:
    _load_generated_mutability_by_resource_name.cache_clear()
    contract = {
        "resources": [
            {
                "resource_name": "Project",
                "immutable_fields": ["meta.create_time", 123],
                "mutable_fields": ["meta.name", None, "spec.tags"],
            },
            {
                "resource_name": "SkipMe",
                "immutable_fields": "bad-shape",
                "mutable_fields": [],
            },
        ]
    }
    with patch(
        "endorlabs.generated.registry_contract.RUNTIME_REGISTRY_CONTRACT", contract
    ):
        actual = _load_generated_mutability_by_resource_name()
    _load_generated_mutability_by_resource_name.cache_clear()

    assert actual == {
        "Project": {
            "immutable_fields": ["meta.create_time"],
            "mutable_fields": ["meta.name", "spec.tags"],
        }
    }
