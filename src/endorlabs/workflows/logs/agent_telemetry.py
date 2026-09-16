"""Collect AgentTelemetry call rows filtered by on_behalf_of principal."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, cast

from endorlabs.workflows.common import WorkflowResult

if TYPE_CHECKING:
    from endorlabs.client_surface import Client


def _empty_rows() -> list[dict[str, Any]]:
    return []


def _empty_str_list() -> list[str]:
    return []


@dataclass
class PrincipalCallCollectResult(WorkflowResult):
    """Agent Kit calls matched to a principal substring."""

    namespace: str = ""
    on_behalf_of_contains: str = ""
    window_days: int | None = None
    agents_scanned: list[str] = field(default_factory=_empty_str_list)
    calls_scanned: int = 0
    rows: list[dict[str, Any]] = field(default_factory=_empty_rows)


def _call_to_dict(call: Any, *, agent_id: str) -> dict[str, Any]:
    if hasattr(call, "model_dump") and callable(call.model_dump):
        data = cast("Any", call.model_dump(mode="json", exclude_none=False))
        if isinstance(data, dict):
            out = cast("dict[str, Any]", data)
            return {**out, "agent_id": agent_id}
    if isinstance(call, dict):
        out = cast("dict[str, Any]", call)
        return {**out, "agent_id": agent_id}
    raise TypeError(f"Unsupported AgentCall row type: {type(call)!r}")


def _client_default_namespace(client: Client) -> str | None:
    raw = getattr(client, "_default_namespace", None)
    return str(raw) if raw else None


def _agent_ids_from_activity(activity: Any) -> list[str]:
    targets: list[str] = []
    agents_raw: Any = getattr(activity, "agents", None)
    agents: list[Any] = list(agents_raw) if agents_raw else []
    for agent in agents:
        agent_id = getattr(agent, "agent_id", None)
        if isinstance(agent_id, str) and agent_id.strip():
            targets.append(agent_id)
    return targets


def _match_calls(
    client: Client,
    *,
    namespace: str,
    targets: Sequence[str],
    match_needle: str,
    case_insensitive: bool,
    page_size: int,
    max_pages_per_agent: int | None,
) -> tuple[list[dict[str, Any]], int, list[str]]:
    matched: list[dict[str, Any]] = []
    scanned = 0
    errors: list[str] = []
    for agent_id in targets:
        try:
            for call in client.AgentTelemetry.iter_calls(
                agent_id,
                namespace=namespace,
                page_size=page_size,
                max_pages=max_pages_per_agent,
            ):
                scanned += 1
                row = _call_to_dict(call, agent_id=agent_id)
                obo = str(row.get("on_behalf_of") or "")
                hay = obo.lower() if case_insensitive else obo
                if match_needle in hay:
                    matched.append(row)
        except Exception as exc:
            errors.append(f"{agent_id}: {type(exc).__name__}: {exc}")
    matched.sort(key=lambda r: str(r.get("timestamp") or ""), reverse=True)
    return matched, scanned, errors


def collect_calls_for_principal(
    client: Client,
    *,
    on_behalf_of_contains: str,
    namespace: str | None = None,
    window_days: int = 90,
    agent_ids: Sequence[str] | None = None,
    page_size: int = 100,
    max_pages_per_agent: int | None = None,
    case_insensitive: bool = True,
) -> PrincipalCallCollectResult:
    """Pull AgentTelemetry activity + call history filtered by principal.

    ``on_behalf_of_contains`` is a caller-supplied substring (e.g.
    ``user@example.com``). No estate identifiers are hardcoded.

    Agents Hub call history is intentionally capped by the platform; activity
    totals may exceed retained call rows.
    """
    needle = (on_behalf_of_contains or "").strip()
    if not needle:
        return PrincipalCallCollectResult(
            status="error",
            message="on_behalf_of_contains is required",
            errors=["on_behalf_of_contains is required"],
        )

    ns = namespace or _client_default_namespace(client)
    if not ns:
        return PrincipalCallCollectResult(
            status="error",
            message="namespace is required (pass namespace= or Client(tenant=…))",
            errors=["namespace is required"],
        )

    try:
        activity = client.AgentTelemetry.activity(namespace=ns, window_days=window_days)
    except Exception as exc:
        return PrincipalCallCollectResult(
            status="error",
            message=f"activity failed: {exc}",
            errors=[f"{type(exc).__name__}: {exc}"],
            namespace=ns,
            on_behalf_of_contains=needle,
            window_days=window_days,
        )

    if agent_ids is not None:
        targets = [str(a) for a in agent_ids if str(a).strip()]
    else:
        targets = _agent_ids_from_activity(activity)

    match_needle = needle.lower() if case_insensitive else needle
    matched, scanned, errors = _match_calls(
        client,
        namespace=ns,
        targets=targets,
        match_needle=match_needle,
        case_insensitive=case_insensitive,
        page_size=page_size,
        max_pages_per_agent=max_pages_per_agent,
    )

    status = "success"
    if errors and matched:
        status = "partial"
    elif errors and not matched:
        status = "error"
    return PrincipalCallCollectResult(
        status=status,
        message=(
            f"Matched {len(matched)} call(s) of {scanned} scanned "
            f"across {len(targets)} agent(s)"
        ),
        errors=errors,
        namespace=ns,
        on_behalf_of_contains=needle,
        window_days=window_days,
        agents_scanned=list(targets),
        calls_scanned=scanned,
        rows=matched,
    )


__all__ = [
    "PrincipalCallCollectResult",
    "collect_calls_for_principal",
]
