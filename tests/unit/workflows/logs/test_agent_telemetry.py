"""Unit tests for AgentTelemetry custom facade and principal collect helper."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import Mock

import pytest

from endorlabs.facade import AgentTelemetryFacade
from endorlabs.generated.models.agent_telemetry_service import (
    Agent,
    Call,
    V1ListAgentActivityResponse,
)
from endorlabs.resources import agent_telemetry as wire
from endorlabs.workflows.logs.agent_telemetry import collect_calls_for_principal


class _JsonResponse:
    def __init__(self, payload: dict[str, Any]) -> None:
        super().__init__()
        self._payload = payload

    def json(self) -> dict[str, Any]:
        return self._payload


def test_list_agent_activity_parses_response() -> None:
    client = Mock()
    client.get.return_value = _JsonResponse(
        {
            "schema_version": "v1",
            "window_days": 7,
            "agents": [{"agent_id": "findings-browser", "calls": "3", "active": True}],
        }
    )
    result = wire.list_agent_activity(client, namespace="example-tenant", window_days=7)
    assert isinstance(result, V1ListAgentActivityResponse)
    assert result.window_days == 7
    assert result.agents is not None
    assert result.agents[0].agent_id == "findings-browser"
    client.get.assert_called_once()
    args, kwargs = client.get.call_args
    assert args[0] == "v1/namespaces/example-tenant/agent-telemetry/activity"
    assert kwargs["params"] == {"window_days": 7}


def test_list_agent_calls_page_requires_agent_id() -> None:
    with pytest.raises(ValueError, match="agent_id"):
        wire.list_agent_calls_page(Mock(), "", namespace="example-tenant")


def test_agent_telemetry_facade_iter_calls_paginates() -> None:
    api = Mock()
    pages = [
        _JsonResponse(
            {
                "agent_id": "findings-browser",
                "calls": [
                    {
                        "timestamp": "2026-09-16T10:00:00Z",
                        "operation": "LIST",
                        "resource_kind": "Finding",
                        "decision": "allowed",
                        "status_code": "OK",
                        "on_behalf_of": "user@example.com@abc",
                    }
                ],
                "next_page_token": "token-2",
            }
        ),
        _JsonResponse(
            {
                "agent_id": "findings-browser",
                "calls": [
                    {
                        "timestamp": "2026-09-16T09:00:00Z",
                        "operation": "LIST",
                        "resource_kind": "Project",
                        "decision": "allowed",
                        "status_code": "InvalidArgument",
                        "on_behalf_of": "other@example.com@xyz",
                    }
                ],
                "next_page_token": "",
            }
        ),
    ]
    api.get.side_effect = pages
    facade = AgentTelemetryFacade(api, "example-tenant")
    rows = list(facade.iter_calls("findings-browser", page_size=1))
    assert len(rows) == 2
    assert rows[0].resource_kind == "Finding"
    assert rows[1].status_code == "InvalidArgument"
    assert api.get.call_count == 2


def test_collect_calls_for_principal_filters_placeholder_email() -> None:
    client = SimpleNamespace(_default_namespace="example-tenant")
    telemetry = Mock()
    telemetry.activity.return_value = V1ListAgentActivityResponse(
        agents=[Agent(agent_id="findings-browser", active=True, calls="2")]
    )
    telemetry.iter_calls.return_value = [
        Call(
            timestamp=None,
            operation="LIST",
            resource_kind="Finding",
            decision="allowed",
            status_code="OK",
            on_behalf_of="user@example.com@abc123",
        ),
        Call(
            timestamp=None,
            operation="LIST",
            resource_kind="Project",
            decision="allowed",
            status_code="OK",
            on_behalf_of="other@example.com@def456",
        ),
    ]
    client.AgentTelemetry = telemetry

    result = collect_calls_for_principal(
        cast("Any", client),
        on_behalf_of_contains="user@example.com",
        namespace="example-tenant",
        window_days=30,
    )
    assert result.status == "success"
    assert result.calls_scanned == 2
    assert len(result.rows) == 1
    assert result.rows[0]["agent_id"] == "findings-browser"
    assert "user@example.com" in str(result.rows[0]["on_behalf_of"])


def test_collect_calls_for_principal_requires_needle() -> None:
    result = collect_calls_for_principal(
        cast("Any", SimpleNamespace(_default_namespace="example-tenant")),
        on_behalf_of_contains="  ",
    )
    assert result.status == "error"
    assert not result.ok
