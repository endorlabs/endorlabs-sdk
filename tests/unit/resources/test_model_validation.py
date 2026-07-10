"""Test cases for model validation utilities.

Tests get_tags_update_paths (from model class),
validate_update_mask, safe_serialize, and related helpers used by resources/base.
"""

from datetime import datetime
from enum import Enum

import pytest
from pydantic import BaseModel

from endorlabs.resources.finding import Finding
from endorlabs.resources.policy import Policy
from endorlabs.resources.project import Project
from endorlabs.utils.model_validation import (
    build_filter_from_identity_kwargs,
    create_minimal_payload,
    ensure_required_fields,
    get_list_filter_map,
    get_tags_update_paths,
    parse_update_mask,
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


class TestGetImmutableFieldsCls:
    """Tests for model get_immutable_fields_cls() (canonical source)."""

    def test_finding_returns_list(self) -> None:
        fields = Finding.get_immutable_fields_cls()
        assert isinstance(fields, list)
        assert "uuid" in fields
        assert "meta.create_time" in fields
        assert "spec.project_uuid" in fields

    def test_policy_returns_list(self) -> None:
        fields = Policy.get_immutable_fields_cls()
        assert "spec.policy_type" in fields


class TestParseUpdateMask:
    """Tests for parse_update_mask."""

    def test_single_field(self) -> None:
        assert parse_update_mask("meta.tags") == ["meta.tags"]

    def test_multiple_fields_and_whitespace(self) -> None:
        assert parse_update_mask("meta.description, meta.tags") == [
            "meta.description",
            "meta.tags",
        ]
        assert parse_update_mask("a,, b ") == ["a", "b"]
        assert parse_update_mask("") == []


class TestGetTagsUpdatePaths:
    """Tests for get_tags_update_paths(model_class) (tag capability from model)."""

    def test_project_returns_meta_tags(self) -> None:
        assert get_tags_update_paths(Project) == ["meta.tags"]

    def test_finding_returns_meta_tags_and_spec_finding_tags(self) -> None:
        paths = get_tags_update_paths(Finding)
        assert set(paths) == {"meta.tags", "spec.finding_tags"}

    def test_class_without_get_mutable_fields_cls_returns_empty(self) -> None:
        """Class without get_mutable_fields_cls returns []."""

        class NoMutableFields:
            pass

        assert get_tags_update_paths(NoMutableFields) == []


class TestGetListFilterMap:
    """Tests for get_list_filter_map (list identity kwargs)."""

    def test_project_returns_name_map(self) -> None:
        assert get_list_filter_map("project") == {"name": "meta.name"}

    def test_repository_returns_name_and_vcs_url(self) -> None:
        m = get_list_filter_map("repository")
        assert m.get("name") == "meta.name"
        assert m.get("vcs_url") == "spec.vcs_url"
        assert m.get("git_url") == "spec.vcs_url"

    def test_authorization_policy_has_name_in_map(self) -> None:
        """authorization_policy supports list(name=...) / lookup(name=...)."""
        m = get_list_filter_map("authorization_policy")
        assert "name" in m
        assert m["name"] == "meta.name"

    def test_list_filter_map_keys_match_resource_name_to_type_values(self) -> None:
        """Every LIST_FILTER_KWARG_MAP key has a RESOURCE_NAME_TO_TYPE entry."""
        from endorlabs.resources.base import RESOURCE_NAME_TO_TYPE
        from endorlabs.utils import model_validation

        type_values = set(RESOURCE_NAME_TO_TYPE.values())
        map_keys = set(model_validation.LIST_FILTER_KWARG_MAP)
        for key in map_keys:
            assert key in type_values, (
                f"LIST_FILTER_KWARG_MAP key {key!r} not in RESOURCE_NAME_TO_TYPE values"
            )

    def test_unknown_returns_empty(self) -> None:
        assert get_list_filter_map("") == {}
        assert get_list_filter_map("unknown") == {}


class TestBuildFilterFromIdentityKwargs:
    """Tests for build_filter_from_identity_kwargs."""

    def test_name_backend_produces_meta_name_clause(self) -> None:
        filter_map = {"name": "meta.name"}
        kwargs = {"name": "backend", "max_pages": 1}
        merged, remaining = build_filter_from_identity_kwargs(filter_map, kwargs)
        assert "meta.name" in merged
        assert "backend" in merged
        assert "name" not in remaining
        assert remaining.get("max_pages") == 1

    def test_merge_with_explicit_filter(self) -> None:
        filter_map = {"name": "meta.name"}
        kwargs = {"filter": "spec.level == 'CRITICAL'", "name": "backend"}
        merged, remaining = build_filter_from_identity_kwargs(filter_map, kwargs)
        assert "meta.name" in merged
        assert "spec.level" in merged
        assert "name" not in remaining
        assert "filter" not in remaining


class TestValidateUpdateMask:
    """Tests for validate_update_mask."""

    def test_empty_mask_returns_true(self) -> None:
        assert validate_update_mask("", ["meta.tags"]) is True

    def test_valid_fields(self) -> None:
        assert validate_update_mask("meta.tags", ["meta.tags", "spec.level"]) is True
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
