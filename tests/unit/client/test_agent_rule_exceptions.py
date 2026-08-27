"""Typed EndorRuleError exceptions carry MANIFEST rule_id corrections."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, Mock

import pytest

from endorlabs import AGENT_RULE_EXCEPTION_TYPES, agent_knowledge_manifest
from endorlabs.context.paths import default_runs_dir, require_openapi_spec
from endorlabs.core.exceptions import (
    ListQueryPerformanceError,
    LocalContextError,
    NamespaceScopingError,
    OutputShapeRoutingError,
    PortableExamplesError,
    WorkflowCompositionError,
    WorkspaceLayoutError,
)
from endorlabs.core.portable import raise_if_nonportable_tenant_literal
from endorlabs.facade import ListableFacade
from endorlabs.query.routing import OutputShape
from endorlabs.registry import RESOURCE_REGISTRY
from endorlabs.workflows.estate.analyze.workspace import analyze_workspace
from endorlabs.workflows.estate.collect.runner import collect_workspace


def _facade(attr_name: str, *, tenant: str = "example-tenant") -> ListableFacade:
    entry = next(e for e in RESOURCE_REGISTRY if e.attr_name == attr_name)
    return ListableFacade(Mock(), tenant, entry)


def test_agent_rule_exception_ids_match_manifest() -> None:
    manifest_ids = {row["id"] for row in agent_knowledge_manifest()["rules"]}
    exception_ids = {cls.rule_id for cls in AGENT_RULE_EXCEPTION_TYPES}
    assert exception_ids <= manifest_ids
    assert exception_ids == {
        "endor-namespace-scoping",
        "endor-list-query-performance",
        "endor-output-shape-routing",
        "endor-workflow-composition",
        "endor-local-context",
        "endor-workspace-layout",
        "endor-portable-examples",
    }


def test_namespace_scoping_error_before_network() -> None:
    facade = _facade("Finding")
    facade._ops = Mock()
    with pytest.raises(NamespaceScopingError, match="list_by_project") as exc_info:
        facade.list(max_pages=1)
    assert exc_info.value.rule_id == "endor-namespace-scoping"
    facade._ops.list.assert_not_called()


def test_list_query_performance_page_size_without_filter() -> None:
    facade = _facade("Finding", tenant="example-tenant.child")
    facade._ops = Mock()
    with pytest.raises(ListQueryPerformanceError, match="page_size=1") as exc_info:
        facade.list(page_size=1, traverse=False)
    assert exc_info.value.rule_id == "endor-list-query-performance"
    facade._ops.list.assert_not_called()


def test_list_query_performance_max_pages_unscoped_at_tenant_root() -> None:
    """max_pages on project-scoped list at tenant root is blocked (after namespace)."""
    facade = _facade("Finding", tenant="example-tenant")
    facade._ops = Mock()
    # Namespace rule takes precedence when both apply.
    with pytest.raises(NamespaceScopingError):
        facade.list(max_pages=50)
    facade._ops.list.assert_not_called()


def test_output_shape_routing_error_on_collect() -> None:
    with pytest.raises(OutputShapeRoutingError, match="OutputShape") as exc_info:
        collect_workspace(MagicMock(), namespace="example-tenant")
    assert exc_info.value.rule_id == "endor-output-shape-routing"


def test_workflow_composition_error_on_analyze_without_pull(tmp_path: Path) -> None:
    with pytest.raises(WorkflowCompositionError, match="pull") as exc_info:
        analyze_workspace(tmp_path, namespace="example-tenant")
    assert exc_info.value.rule_id == "endor-workflow-composition"


def test_local_context_error_missing_openapi(tmp_path: Path) -> None:
    with pytest.raises(LocalContextError, match="OpenAPI") as exc_info:
        require_openapi_spec(tmp_path)
    assert exc_info.value.rule_id == "endor-local-context"


def test_workspace_layout_error_timestamp_bucket(tmp_path: Path) -> None:
    with pytest.raises(WorkspaceLayoutError, match="timestamp") as exc_info:
        default_runs_dir("20260827T120000Z", context_dir=tmp_path)
    assert exc_info.value.rule_id == "endor-workspace-layout"
    path = default_runs_dir("troubleshooting-scans", context_dir=tmp_path)
    assert path.name == "troubleshooting-scans"


def test_portable_examples_error_nonportable_tenant() -> None:
    # Build at runtime so the source file does not embed a dotted estate literal
    # (pre-commit portable-examples scans added lines).
    bad = "nonexample-root" + ".child-ns.prod"
    with pytest.raises(PortableExamplesError, match="nonexample-root") as exc_info:
        raise_if_nonportable_tenant_literal(f'tenant="{bad}"', field="fixture")
    assert exc_info.value.rule_id == "endor-portable-examples"
    raise_if_nonportable_tenant_literal("example-tenant.child", field="fixture")


def test_collect_shape_gate_allows_classified_pull(tmp_path: Path) -> None:
    client = MagicMock()
    try:
        collect_workspace(
            client,
            namespace="example-tenant",
            output_shape=OutputShape.FINDING_ROWS,
            workspace=tmp_path,
            max_pages=1,
        )
    except OutputShapeRoutingError:
        pytest.fail("output_shape gate should not fire when shape is provided")
    except Exception:
        # Downstream collect failure is expected with a MagicMock client.
        pass
