"""Unit tests for create payload promotion helpers."""

from __future__ import annotations

import pytest

from endorlabs.utils.create_payload import (
    promote_create_kwargs,
    validate_flat_create_kwargs,
    validate_pass_through_create,
)


def test_promote_spec_fields_and_default_meta() -> None:
    payload = promote_create_kwargs(
        {
            "vector_store_uuid": "u1",
            "query": "logging",
            "metadata_filter": {"repo": "https://example.git"},
        },
        spec_fields=("vector_store_uuid", "query", "metadata_filter"),
        meta_name_default="vector-store-query",
        resource_label="VectorStoreQuery",
    )
    assert payload["meta"]["name"] == "vector-store-query"
    assert payload["spec"]["vector_store_uuid"] == "u1"
    assert payload["spec"]["metadata_filter"]["repo"] == "https://example.git"


def test_promote_explicit_spec_passthrough() -> None:
    payload = promote_create_kwargs(
        {"spec": {"vector_store_uuid": "u", "query": "q"}},
        spec_fields=("vector_store_uuid", "query"),
        resource_label="VectorStoreQuery",
    )
    assert payload["spec"]["query"] == "q"


def test_promote_unknown_kwarg_raises() -> None:
    with pytest.raises(TypeError, match="typo"):
        promote_create_kwargs(
            {"vector_store_uuid": "u", "query": "q", "typo": 1},
            spec_fields=("vector_store_uuid", "query"),
            resource_label="VectorStoreQuery",
        )


def test_pass_through_allows_spec_and_top_level_flat_keys() -> None:
    validate_pass_through_create(
        {
            "meta": {},
            "propagate": False,
            "policy_type": "POLICY_TYPE_EXCEPTION",
        },
        payload_top_level_fields=("meta", "propagate", "tenant_meta"),
        meta_fields=(),
        spec_fields=("policy_type", "rule"),
        resource_label="Policy",
    )


def test_validate_flat_create_kwargs() -> None:
    validate_flat_create_kwargs(
        {"meta": {}, "spec": {}},
        allowed=("meta", "spec", "propagate"),
        resource_label="Policy",
    )
    with pytest.raises(TypeError):
        validate_flat_create_kwargs(
            {"meta": {}, "unknown": 1},
            allowed=("meta", "spec"),
            resource_label="Policy",
        )
