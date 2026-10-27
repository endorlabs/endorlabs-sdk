"""Unit tests for FindingLog resilient group_by_time escalate."""

from __future__ import annotations

from unittest.mock import MagicMock

from endorlabs.core.exceptions import NetworkError, ServerError
from endorlabs.workflows.findings.finding_log_trends import (
    query_operation_group_counts_resilient,
)


def test_resilient_returns_empty_for_empty_parent_uuids() -> None:
    client = MagicMock()
    counts = query_operation_group_counts_resilient(
        client,
        namespace="example-tenant",
        base_filter="meta.create_time>=date(2026-01-01T00:00:00Z)",
        operation="CREATE",
        level="CRITICAL",
        interval="week",
        parent_uuids=[],
    )
    assert counts == {}
    client.FindingLog.list_groups.assert_not_called()


def test_resilient_single_project_does_not_discover_on_timeout() -> None:
    client = MagicMock()

    def list_groups(**_kwargs: object) -> list[object]:
        raise ServerError("timeout", status_code=504)

    client.FindingLog.list_groups = list_groups

    try:
        query_operation_group_counts_resilient(
            client,
            namespace="example-tenant.child",
            base_filter="meta.create_time>=date(2026-01-01T00:00:00Z)",
            operation="CREATE",
            level="HIGH",
            interval="week",
            parent_uuids=["proj-1"],
        )
    except ServerError:
        pass
    else:
        raise AssertionError("expected ServerError to propagate for single project")
    client.Query.Project.discover.assert_not_called()


def test_resilient_leaf_timeout_propagates() -> None:
    client = MagicMock()

    def list_groups(**_kwargs: object) -> list[object]:
        raise ServerError("timeout", status_code=504)

    client.FindingLog.list_groups = list_groups

    try:
        query_operation_group_counts_resilient(
            client,
            namespace="example-tenant.child",
            base_filter="meta.create_time>=date(2026-01-01T00:00:00Z)",
            operation="CREATE",
            level="CRITICAL",
            interval="week",
            parent_uuids=None,
            max_workers=2,
        )
    except ServerError:
        pass
    else:
        raise AssertionError("expected ServerError to propagate for a leaf aggregate")
    client.Query.Project.discover.assert_not_called()


def test_resilient_shard_timeout_returns_empty_counts() -> None:
    """A timed-out aggregate is not rewritten as a zero count."""
    client = MagicMock()

    def list_groups(**_kwargs: object) -> list[object]:
        raise NetworkError(
            "Network error after 2 attempt(s): The read operation timed out"
        )

    client.FindingLog.list_groups = list_groups

    try:
        query_operation_group_counts_resilient(
            client,
            namespace="example-tenant.child",
            base_filter="meta.create_time>=date(2026-01-01T00:00:00Z)",
            operation="CREATE",
            level="CRITICAL",
            interval="week",
            parent_uuids=None,
            max_workers=2,
        )
    except NetworkError:
        pass
    else:
        raise AssertionError("expected NetworkError to propagate")
    client.Query.Project.discover.assert_not_called()


def test_resilient_multi_is_in_uses_traverse() -> None:
    """Multi-UUID parent_uuid is_in must traverse child namespaces."""
    client = MagicMock()
    seen: dict[str, object] = {}

    def list_groups(**kwargs: object) -> list[object]:
        seen["traverse"] = kwargs.get("traverse")
        lp = kwargs.get("list_params")
        filt = ""
        if lp is not None:
            filt = str(getattr(lp, "filter", "") or "")
        if not filt:
            filt = str(kwargs.get("filter") or "")
        seen["filter"] = filt
        return []

    client.FindingLog.list_groups = list_groups

    counts = query_operation_group_counts_resilient(
        client,
        namespace="example-tenant",
        base_filter="meta.create_time>=date(2026-01-01T00:00:00Z)",
        operation="CREATE",
        level="HIGH",
        interval="week",
        parent_uuids=["proj-1", "proj-2"],
    )
    assert counts == {}
    assert seen.get("traverse") is True
    assert "meta.parent_uuid in [" in str(seen.get("filter") or "")


def test_resilient_single_parent_uuid_uses_traverse() -> None:
    """Single parent_uuid is equality at the given namespace, without traverse."""
    client = MagicMock()
    seen: dict[str, object] = {}

    def list_groups(**kwargs: object) -> list[object]:
        seen["traverse"] = kwargs.get("traverse")
        return []

    client.FindingLog.list_groups = list_groups

    counts = query_operation_group_counts_resilient(
        client,
        namespace="example-tenant",
        base_filter="meta.create_time>=date(2026-01-01T00:00:00Z)",
        operation="CREATE",
        level="HIGH",
        interval="week",
        parent_uuids=["proj-1"],
    )
    assert counts == {}
    assert seen.get("traverse") is False
