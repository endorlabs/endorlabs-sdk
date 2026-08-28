"""Unit tests for log density probe and source count adapters."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from unittest.mock import MagicMock

from endorlabs.workflows.logs.density import probe_log_density
from endorlabs.workflows.logs.sources import (
    count_agent_hook_events,
    count_log_events,
)


def test_count_agent_hook_events_parses_count_response() -> None:
    client = MagicMock()
    api = MagicMock()
    client._client = api
    res = MagicMock()
    res.json.return_value = {"count_response": {"count": 42}}
    api.get.return_value = res
    assert (
        count_agent_hook_events(
            client,
            namespace="example-tenant",
            filter_expr="meta.create_time >= date(x)",
        )
        == 42
    )
    params: dict[str, Any] = api.get.call_args.kwargs["params"]
    assert params["list_parameters.count"] == "true"
    assert "list_parameters.filter" in params


def test_probe_log_density_threshold_and_soft_fail() -> None:
    client = MagicMock()

    def _count_by_namespace(*, namespace: str, **_kwargs: Any) -> int:
        if namespace == "example-tenant.a":
            return 0
        if namespace == "example-tenant.b":
            return 5
        if namespace == "example-tenant.c":
            raise RuntimeError("boom")
        raise AssertionError(f"unexpected namespace: {namespace}")

    client.PackageFirewallLog.count.side_effect = _count_by_namespace

    result = probe_log_density(
        client,
        source="package-firewall-logs",
        root_namespace="example-tenant",
        since=datetime(2026, 8, 1, tzinfo=UTC),
        until=datetime(2026, 8, 2, tzinfo=UTC),
        min_events=1,
        namespaces=[
            "example-tenant.a",
            "example-tenant.b",
            "example-tenant.c",
        ],
        max_workers=2,
    )
    assert result.status == "partial"
    assert result.pull_namespaces == ["example-tenant.b"]
    assert result.total_events == 5
    by_ns = {row.namespace: row for row in result.rows}
    assert by_ns["example-tenant.a"].needs_pull is False
    assert by_ns["example-tenant.b"].needs_pull is True
    assert by_ns["example-tenant.c"].error is not None


def test_count_log_events_package_firewall() -> None:
    client = MagicMock()
    client.PackageFirewallLog.count.return_value = 7
    assert (
        count_log_events(
            client,
            "package-firewall-logs",
            namespace="example-tenant.package-firewall",
            filter_expr=None,
        )
        == 7
    )
