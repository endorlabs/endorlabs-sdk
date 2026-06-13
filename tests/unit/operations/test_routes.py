"""Tests for generic route executors (mocked ops)."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from endorlabs.core.exceptions import RouteNotApplicableError
from endorlabs.operations.route_contract import RouteEdge, load_golden_contract
from endorlabs.operations.routes import RouteExecutor, resolve_attr_path


def _project() -> SimpleNamespace:
    return SimpleNamespace(
        uuid="proj-uuid-1",
        tenant_meta=SimpleNamespace(namespace="tenant.child"),
    )


def _scan() -> SimpleNamespace:
    return SimpleNamespace(
        uuid="scan-uuid-1",
        tenant_meta=SimpleNamespace(namespace="tenant.child"),
        meta=SimpleNamespace(parent_uuid="proj-uuid-1"),
        context=SimpleNamespace(type="CONTEXT_TYPE_CI_RUN", id="pr-1"),
    )


def _finding(
    *, target_uuid: str = "dm-uuid-1", package: str = "pypi://requests@2.28"
) -> SimpleNamespace:
    return SimpleNamespace(
        uuid="finding-1",
        tenant_meta=SimpleNamespace(namespace="tenant.child"),
        spec=SimpleNamespace(
            target_uuid=target_uuid,
            target_dependency_package_name=package,
            project_uuid="proj-uuid-1",
            finding_categories=["FINDING_CATEGORY_SAST"],
            method="SYSTEM_EVALUATION_METHOD_SAST",
        ),
    )


def _executor(**kinds: Mock) -> RouteExecutor:
    return RouteExecutor(
        default_namespace="tenant",
        ops_for_kind=dict(kinds),
    )


@pytest.mark.parametrize(
    ("edge_id", "setup"),
    [
        (
            "project.findings",
            lambda: (
                _executor(Finding=Mock()),
                _project(),
                "Finding",
            ),
        ),
        (
            "scan.findings",
            lambda: (
                _executor(Finding=Mock()),
                _scan(),
                "Finding",
            ),
        ),
    ],
)
def test_list_routes_call_ops_with_expected_filter(edge_id: str, setup) -> None:
    executor, source, kind = setup()
    contract = load_golden_contract()
    edge = contract.edge_by_id(edge_id)
    assert edge is not None
    mock_ops = executor._ops_for_kind[kind]
    mock_ops.list.return_value = []
    result = executor.execute(edge, source=source)
    assert result.edge_used == edge_id
    mock_ops.list.assert_called_once()
    args, _ = mock_ops.list.call_args
    assert args[0] == "tenant.child"
    lp = args[1]
    assert lp is not None
    if edge_id == "project.findings":
        assert 'spec.project_uuid=="proj-uuid-1"' in lp.filter
    if edge_id == "scan.findings":
        assert '(context.type=="CONTEXT_TYPE_CI_RUN")' in lp.filter
        assert '(context.id=="pr-1")' in lp.filter
        assert 'spec.project_uuid=="proj-uuid-1"' in lp.filter


def test_get_by_uuid_route() -> None:
    contract = load_golden_contract()
    edge = contract.edge_by_id("finding.dependency_metadata.get")
    assert edge is not None
    mock_ops = Mock()
    mock_ops.get.return_value = SimpleNamespace(uuid="dm-uuid-1")
    executor = _executor(DependencyMetadata=mock_ops)
    finding = _finding()
    result = executor.execute(edge, source=finding)
    mock_ops.get.assert_called_once_with("tenant.child", "dm-uuid-1")
    assert result.value is not None


def test_list_by_parent_via_list_fn() -> None:
    contract = load_golden_contract()
    edge = contract.edge_by_id("project.scan_results")
    assert edge is not None
    list_fn = Mock(return_value=[SimpleNamespace(uuid="scan-1")])
    executor = RouteExecutor(
        default_namespace="tenant",
        ops_for_kind={"ScanResult": Mock()},
        list_fn_for_parent=list_fn,
    )
    result = executor.execute(edge, source=_project())
    list_fn.assert_called_once()
    assert result.values and len(result.values) == 1


def _semgrep_chain_edge() -> RouteEdge:
    """Executor-only chain edge (not shipped on the public accessor surface)."""
    return RouteEdge.from_dict(
        {
            "id": "finding.semgrep_rule.by_linter",
            "from_kind": "Finding",
            "to_kind": "SemgrepRule",
            "edge": "via_intermediate",
            "when": {"categories": ["FINDING_CATEGORY_SAST"]},
            "steps": [
                {
                    "kind": "list_by_uuid_field",
                    "through_kind": "LinterResult",
                    "filter_field": "spec.project_uuid",
                    "uuid_from": "source.spec.project_uuid",
                },
                {
                    "kind": "get_by_uuid",
                    "uuid_from": "through.spec.semgrep.rule_uuid",
                    "optional": True,
                },
                {
                    "kind": "list_by_attribute",
                    "source_attr": "through.spec.semgrep.rule_name",
                    "target_filter_field": "meta.name",
                    "match": "substring",
                    "optional": True,
                },
            ],
        }
    )


def test_list_by_context_partition_missing_context_raises() -> None:
    contract = load_golden_contract()
    edge = contract.edge_by_id("scan.findings")
    assert edge is not None
    executor = _executor(Finding=Mock())
    scan = SimpleNamespace(
        uuid="scan-1",
        tenant_meta=SimpleNamespace(namespace="tenant.child"),
        meta=SimpleNamespace(parent_uuid="proj-1"),
        context=None,
    )
    with pytest.raises(RouteNotApplicableError, match="Missing context partition"):
        executor.execute(edge, source=scan)


def test_list_by_context_partition_merges_caller_filter() -> None:
    contract = load_golden_contract()
    edge = contract.edge_by_id("scan.findings")
    assert edge is not None
    mock_ops = Mock()
    mock_ops.list.return_value = []
    executor = _executor(Finding=mock_ops)
    executor.execute(
        edge,
        source=_scan(),
        filter='spec.level=="FINDING_LEVEL_CRITICAL"',
    )
    lp = mock_ops.list.call_args[0][1]
    assert 'spec.level=="FINDING_LEVEL_CRITICAL"' in lp.filter
    assert "context.type" in lp.filter


def test_when_gate_rejects_non_sast() -> None:
    edge = _semgrep_chain_edge()
    finding = _finding()
    finding.spec.finding_categories = ["FINDING_CATEGORY_SCA"]
    executor = _executor(SemgrepRule=Mock(), LinterResult=Mock())
    with pytest.raises(RouteNotApplicableError, match="finding_categories"):
        executor.execute(edge, source=finding)


def test_list_by_parent_uses_parent_kwarg() -> None:
    contract = load_golden_contract()
    edge = contract.edge_by_id("project.scan_results")
    assert edge is not None
    list_fn = Mock(return_value=[])
    executor = RouteExecutor(
        default_namespace="tenant",
        ops_for_kind={"ScanResult": Mock()},
        list_fn_for_parent=list_fn,
    )
    project = _project()
    executor.execute(edge, source=project, sort_by="meta.create_time")
    list_fn.assert_called_once()
    _, kwargs = list_fn.call_args
    assert kwargs.get("parent") is project


def test_resolve_attr_path_nested() -> None:
    obj = SimpleNamespace(spec=SimpleNamespace(project_uuid="abc"))
    assert resolve_attr_path(obj, "spec.project_uuid") == "abc"


def test_list_by_attribute_package_name() -> None:
    contract = load_golden_contract()
    edge = contract.edge_by_id("finding.dependency_metadata.by_package")
    assert edge is not None
    mock_ops = Mock()
    mock_ops.list.return_value = [SimpleNamespace(uuid="dm-1")]
    executor = _executor(DependencyMetadata=mock_ops)
    finding = _finding(target_uuid="", package="pypi://requests@2.28")
    finding.spec.target_uuid = ""
    result = executor.execute(edge, source=finding)
    mock_ops.list.assert_called_once()
    lp = mock_ops.list.call_args[0][1]
    assert "spec.dependency_data.package_name" in lp.filter
    assert result.value is not None


def test_semgrep_chain_get_by_rule_uuid() -> None:
    edge = _semgrep_chain_edge()
    linter_ops = Mock()
    linter_ops.list.return_value = [
        SimpleNamespace(
            spec=SimpleNamespace(semgrep=SimpleNamespace(rule_uuid="rule-uuid-1"))
        )
    ]
    rule_ops = Mock()
    rule_ops.get.return_value = SimpleNamespace(uuid="rule-uuid-1")
    executor = _executor(LinterResult=linter_ops, SemgrepRule=rule_ops)
    result = executor.execute(edge, source=_finding())
    rule_ops.get.assert_called_once_with("tenant.child", "rule-uuid-1")
    assert result.value is not None
