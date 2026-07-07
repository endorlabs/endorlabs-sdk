"""Unit tests for endorlabs.workflows.wire_access."""

from __future__ import annotations

from endorlabs.workflows.wire_access import (
    as_dict,
    dict_str,
    model_to_dict,
    nested_dict,
    nested_str,
)


def test_as_dict() -> None:
    assert as_dict({"a": 1}) == {"a": 1}
    assert as_dict([]) == {}
    assert as_dict(None) == {}


def test_dict_str() -> None:
    assert dict_str({"name": "foo"}, "name") == "foo"
    assert dict_str({"name": None}, "name", "x") == "x"
    assert dict_str({}, "missing", "d") == "d"


def test_nested_dict_and_str() -> None:
    payload = {"meta": {"name": "proj"}, "tenant_meta": {"namespace": "t.n"}}
    assert nested_dict(payload, "meta") == {"name": "proj"}
    assert nested_str(payload, "meta", "name") == "proj"
    assert nested_str(payload, "meta", "missing") == ""
    assert nested_dict(payload, "meta", "child") == {}


def test_model_to_dict_passthrough() -> None:
    assert model_to_dict({"uuid": "u"}) == {"uuid": "u"}

    class _Model:
        def model_dump(self, *, mode: str) -> dict[str, str]:
            assert mode == "json"
            return {"uuid": "u"}

    assert model_to_dict(_Model()) == {"uuid": "u"}


def test_model_to_dict_mock_attributes() -> None:
    from unittest.mock import Mock

    finding = Mock()
    finding.uuid = "f1"
    finding.meta.description = "desc"
    finding.spec.level = "FINDING_LEVEL_HIGH"
    finding.spec.finding_categories = ["FINDING_CATEGORY_VULNERABILITY"]

    wire = model_to_dict(finding)
    assert wire["uuid"] == "f1"
    assert wire["meta"]["description"] == "desc"
    assert wire["spec"]["level"] == "FINDING_LEVEL_HIGH"
