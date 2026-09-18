"""Agent telemetry wire helpers (Agents Hub / Agent Kit API call metering).

OpenAPI serves activity and recent-call history under
``/v1/namespaces/{namespace}/agent-telemetry/...``. These are not CRUD
resources on ``registry_contract``; ``AgentTelemetryFacade`` on ``Client``
delegates here.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from endorlabs.generated.models.agent_telemetry_service import (
    V1ListAgentActivityResponse,
    V1ListAgentCallsResponse,
)
from endorlabs.workflows.wire_access import as_dict

if TYPE_CHECKING:
    from endorlabs.api_client import APIClient

_ACTIVITY_PATH = "v1/namespaces/{namespace}/agent-telemetry/activity"
_CALLS_PATH = "v1/namespaces/{namespace}/agent-telemetry/agents/{agent_id}/calls"


def _resolve_namespace(
    namespace: str | None,
    default_namespace: str | None,
) -> str:
    resolved = namespace or default_namespace
    if not resolved:
        raise ValueError("namespace is required (pass namespace= or Client(tenant=…))")
    return resolved


def _response_json(res: Any) -> dict[str, Any]:
    if hasattr(res, "json") and callable(res.json):
        return as_dict(res.json())
    return as_dict(res)


def list_agent_activity(
    client: APIClient,
    *,
    namespace: str | None = None,
    default_namespace: str | None = None,
    window_days: int | None = None,
) -> V1ListAgentActivityResponse:
    """GET agent-telemetry activity summary for a namespace."""
    ns = _resolve_namespace(namespace, default_namespace)
    params: dict[str, Any] = {}
    if window_days is not None:
        params["window_days"] = int(window_days)
    url = _ACTIVITY_PATH.format(namespace=ns)
    data = _response_json(client.get(url, params=params or None))
    return V1ListAgentActivityResponse.model_validate(data)


def list_agent_calls_page(
    client: APIClient,
    agent_id: str,
    *,
    namespace: str | None = None,
    default_namespace: str | None = None,
    page_size: int | None = None,
    page_token: str | None = None,
    decision: str | None = None,
    operation: str | None = None,
) -> V1ListAgentCallsResponse:
    """GET one page of recent Agent Kit calls for ``agent_id``."""
    if not agent_id or not str(agent_id).strip():
        raise ValueError("agent_id is required")
    ns = _resolve_namespace(namespace, default_namespace)
    params: dict[str, Any] = {}
    if page_size is not None:
        params["page_size"] = int(page_size)
    if page_token:
        params["page_token"] = page_token
    if decision:
        params["decision"] = decision
    if operation:
        params["operation"] = operation
    url = _CALLS_PATH.format(namespace=ns, agent_id=agent_id)
    data = _response_json(client.get(url, params=params or None))
    return V1ListAgentCallsResponse.model_validate(data)


__all__ = [
    "list_agent_activity",
    "list_agent_calls_page",
]
