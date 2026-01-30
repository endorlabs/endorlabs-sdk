"""Test cases for model validation utilities.

Tests merge_partial_update, get_immutable_fields, validate_update_mask,
safe_serialize, and related helpers used by models/base.
"""

from datetime import datetime
from enum import Enum

import pytest
from pydantic import BaseModel

from endorlabs.utils.model_validation import (
    create_minimal_payload,
    ensure_required_fields,
    get_immutable_fields,
    merge_partial_update,
    safe_serialize,
    validate_update_mask,
)


class TestSafeSerialize:
    """Tests for safe_serialize."""

    def test_datetime(self) -> None:
        dt = datetime(2025, 1, 15, 12, 0, 0)
        assert safe_serialize(dt) == "2025-01-15T12:00:00"

    def test_enum(self) -> None:
        class E(Enum):
            A = "a"
            B = "b"

        assert safe_serialize(E.A) == "a"

    def test_dict_recursive(self) -> None:
        assert safe_serialize({"x": 1, "y": [2, 3]}) == {"x": 1, "y": [2, 3]}

    def test_list_recursive(self) -> None:
        assert safe_serialize([1, "a", None]) == [1, "a", None]

    def test_passthrough_scalar(self) -> None:
        assert safe_serialize(42) == 42
        assert safe_serialize("hello") == "hello"
        assert safe_serialize(None) is None


class TestMergePartialUpdate:
    """Tests for merge_partial_update."""

    def test_no_mask_updates_non_none(self) -> None:
        existing = {"a": 1, "b": 2}
        update = {"a": 10, "b": None}
        result = merge_partial_update(existing, update)
        assert result["a"] == 10
        assert result["b"] == 2

    def test_with_mask_only_specified_fields(self) -> None:
        existing = {"spec": {"level": "low", "name": "x"}}
        update = {"spec": {"level": "high", "name": "y"}}
        result = merge_partial_update(existing, update, update_mask=["spec.level"])
        assert result["spec"]["level"] == "high"
        assert result["spec"]["name"] == "x"

    def test_with_mask_nested_creates_path(self) -> None:
        existing: dict = {}
        update = {"meta": {"tags": ["a"]}}
        result = merge_partial_update(existing, update, update_mask=["meta.tags"])
        assert result.get("meta", {}).get("tags") == ["a"]


class TestGetImmutableFields:
    """Tests for get_immutable_fields."""

    def test_finding_returns_list(self) -> None:
        fields = get_immutable_fields("finding")
        assert isinstance(fields, list)
        assert "uuid" in fields
        assert "meta.create_time" in fields
        assert "spec.project_uuid" in fields

    def test_policy_returns_list(self) -> None:
        fields = get_immutable_fields("policy")
        assert "spec.policy_type" in fields

    def test_unknown_resource_returns_empty(self) -> None:
        assert get_immutable_fields("unknown_type") == []


class TestValidateUpdateMask:
    """Tests for validate_update_mask."""

    def test_empty_mask_returns_true(self) -> None:
        assert validate_update_mask("", ["meta.tags"]) is True

    def test_valid_single_field(self) -> None:
        assert validate_update_mask("meta.tags", ["meta.tags", "spec.level"]) is True

    def test_valid_multiple_fields(self) -> None:
        assert (
            validate_update_mask(
                "meta.tags, spec.level",
                ["meta.tags", "spec.level"],
            )
            is True
        )

    def test_invalid_field_returns_false(self) -> None:
        assert validate_update_mask("meta.bad", ["meta.tags"], "finding") is False


class TestEnsureRequiredFields:
    """Tests for ensure_required_fields."""

    def test_present_returns_data(self) -> None:
        data = {"meta": {"name": "x"}}
        assert ensure_required_fields(data, ["meta.name"]) == data

    def test_missing_raises(self) -> None:
        data = {"meta": {}}
        with pytest.raises(ValueError, match="Missing required fields"):
            ensure_required_fields(data, ["meta.name"], context="create")


class TestCreateMinimalPayload:
    """Tests for create_minimal_payload."""

    def test_creates_instance(self) -> None:
        class M(BaseModel):
            a: int
            b: str = "default"

        inst = create_minimal_payload(M, a=1)
        assert inst.a == 1
        assert inst.b == "default"

    def test_filters_none(self) -> None:
        class M(BaseModel):
            a: int
            b: str | None = None

        inst = create_minimal_payload(M, a=1, b=None)
        assert inst.a == 1
        assert inst.b is None
