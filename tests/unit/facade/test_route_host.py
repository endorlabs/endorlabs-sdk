"""Tests for RouteHostMixin private route API."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import Mock, patch

from endorlabs.facade.runtime import ResourceRuntimeFacade
from endorlabs.operations.route_contract import load_golden_contract


def _entry(
    *, attr_name: str = "Finding", parent_kind: str | None = None
) -> SimpleNamespace:
    return SimpleNamespace(
        attr_name=attr_name,
        resource_name="findings",
        parent_kind=parent_kind,
        supported_ops=frozenset({"list", "get"}),
        filter_kwarg_map={},
        model_class=SimpleNamespace,
        workflow_flags=frozenset(),
        scope=None,
        create_mode="unsupported",
        update_requires_mask=False,
        build_create_payload_fn=None,
    )


def test_execute_route_project_findings() -> None:
    contract = load_golden_contract()
    facade = ResourceRuntimeFacade(
        Mock(),
        "tenant",
        _entry(attr_name="Finding"),
    )
    facade._route_contract = contract
    project = SimpleNamespace(
        uuid="p-1",
        tenant_meta=SimpleNamespace(namespace="tenant.child"),
    )
    with patch.object(facade, "_get_route_executor") as get_exec:
        executor = Mock()
        get_exec.return_value = executor
        executor.execute.return_value = Mock(edge_used="project.findings", values=[])
        facade._execute_route(
            "project.findings", source=project, filter='meta.name=="x"'
        )
        executor.execute.assert_called_once()
        call = executor.execute.call_args
        assert call.kwargs["source"] is project


def test_route_table_for_finding() -> None:
    contract = load_golden_contract()
    facade = ResourceRuntimeFacade(Mock(), "tenant", _entry(attr_name="Finding"))
    facade._route_contract = contract
    table = facade._route_table_for_kind("Finding")
    assert any(edge.id == "scan.findings" for edge in table)
