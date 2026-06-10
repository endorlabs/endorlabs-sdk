"""Tests for branchy helper behavior in facade internals."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from endorlabs import F
from endorlabs.core.exceptions import ValidationError
from endorlabs.facade import _ListableFacade


def _entry(*, filter_map: dict[str, str] | None = None) -> SimpleNamespace:
    return SimpleNamespace(
        resource_name="projects",
        parent_kind=None,
        supported_ops={"list"},
        filter_kwarg_map=filter_map or {},
        model_class=SimpleNamespace,
        workflow_flags=frozenset(),
    )


def test_ns_requires_explicit_or_default_namespace() -> None:
    facade = _ListableFacade(Mock(), None, _entry())
    with pytest.raises(ValidationError, match="Namespace required"):
        facade._ns(None)


def test_build_list_kwargs_merges_parent_clause_with_existing_filter() -> None:
    parent = SimpleNamespace(uuid="parent-123")
    facade = _ListableFacade(Mock(), "tenant.ns", _entry())
    kwargs = facade._build_list_kwargs(
        parent=parent,
        filter='meta.name=="acme"',
        mask=None,
        page_size=None,
        page_token=None,
        page_id=None,
        sort_by=None,
        desc=None,
        count=None,
        from_date=None,
        to_date=None,
        archive=None,
        pr_uuid=None,
        ci_run_uuid=None,
    )

    assert "filter" in kwargs
    assert 'meta.name=="acme"' in kwargs["filter"]
    assert str(F("meta.parent_uuid") == "parent-123") in kwargs["filter"]


def test_build_list_kwargs_normalizes_filter_expression_and_identity_kwargs() -> None:
    facade = _ListableFacade(
        Mock(),
        "tenant.ns",
        _entry(filter_map={"name": "meta.name"}),
    )
    kwargs = facade._build_list_kwargs(
        parent=None,
        filter=(F("spec.status") == "STATUS_SUCCESS"),
        mask=None,
        page_size=50,
        page_token=None,
        page_id=None,
        sort_by=None,
        desc=None,
        count=None,
        from_date=None,
        to_date=None,
        archive=None,
        pr_uuid=None,
        ci_run_uuid=None,
        name="project-a",
    )

    assert "spec.status" in str(kwargs["filter"])
    assert "meta.name" in str(kwargs["filter"])
    assert kwargs["page_size"] == 50
