"""SDK host-integration contract (portable hosting surfaces).

Guards the public APIs hosts rely on for injected transport, bounded pages,
data-first workflow acquisition, offline describe/filter discovery, and
typed non-receipts. Never invent digests, completeness, concurrency, or
permissions. Hosts can re-run this module against a pinned SDK revision to
qualify an upgrade.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import Mock

import pytest

import endorlabs
from endorlabs.api_client import APIClient
from endorlabs.facade.description import describe_resource
from endorlabs.facade.specialized import (
    FindingFacade,
    PackageVersionFacade,
    ScanResultFacade,
)
from endorlabs.filters import describe_filter_fields, describe_filter_operators
from endorlabs.operations.pagination import ResourcePage
from endorlabs.operations.route_contract import load_golden_contract
from endorlabs.operations.routes import RouteExecutor
from endorlabs.resources.scan_dependency_receipt import read_scan_dependency_receipt
from endorlabs.workflows.platform.change_plans import draft_update_plan
from endorlabs.workflows.troubleshooting_scans import (
    acquire_scan_logs,
    acquire_scan_pair_evidence,
    acquire_scan_results,
    assemble_scan_pair_evidence,
    search_embedded_scan_errors,
)


@pytest.fixture
def clear_auth_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for var in (
        "ENDOR_TOKEN",
        "ENDOR_API_CREDENTIALS_KEY",
        "ENDOR_API_CREDENTIALS_SECRET",
        "ENDOR_NAMESPACE",
    ):
        monkeypatch.delenv(var, raising=False)


# --- SDK-001 -----------------------------------------------------------------


def test_sdk001_receipt_unavailable_never_invents_digest() -> None:
    receipt = read_scan_dependency_receipt(
        scan_result_uuid="scan-1",
        owner_namespace="tenant.child",
        dependency_identity="pypi://requests@2.28.0",
    )
    assert receipt.status == "unavailable"
    assert receipt.digest is None
    assert receipt.algorithm is None
    assert receipt.byte_scope is None
    assert (
        "scan-bound" in receipt.detail.lower() or "platform" in receipt.detail.lower()
    )


# --- SDK-002 -----------------------------------------------------------------


def test_sdk002_relationship_page_twins_exist() -> None:
    assert hasattr(FindingFacade, "list_pages_by_project")
    assert hasattr(FindingFacade, "list_pages_for_context")
    assert hasattr(ScanResultFacade, "list_pages_by_project")
    assert hasattr(PackageVersionFacade, "list_pages_by_project")


def test_sdk002_page_size_folds_into_list_parameters_on_uuid_field_route() -> None:
    contract = load_golden_contract()
    edge = contract.edge_by_id("project.findings")
    assert edge is not None
    mock_ops = Mock()
    mock_ops.list.return_value = []
    executor = RouteExecutor(
        default_namespace="tenant",
        ops_for_kind={"Finding": mock_ops},
    )
    project = SimpleNamespace(
        uuid="proj-1",
        tenant_meta=SimpleNamespace(namespace="tenant.child"),
    )
    executor.execute(edge, source=project, page_size=2, sort_by="meta.name")
    lp = mock_ops.list.call_args.args[1]
    assert lp.page_size == 2
    assert lp.sort_by == "meta.name"


def test_sdk002_list_params_object_merges_on_uuid_field_route() -> None:
    from endorlabs.core.types import ListParameters

    contract = load_golden_contract()
    edge = contract.edge_by_id("project.findings")
    assert edge is not None
    mock_ops = Mock()
    mock_ops.list.return_value = []
    executor = RouteExecutor(
        default_namespace="tenant",
        ops_for_kind={"Finding": mock_ops},
    )
    project = SimpleNamespace(
        uuid="proj-1",
        tenant_meta=SimpleNamespace(namespace="tenant.child"),
    )
    executor.execute(
        edge,
        source=project,
        list_params=ListParameters(mask="uuid,meta.name"),
        page_size=3,
    )
    lp = mock_ops.list.call_args.args[1]
    assert lp.mask == "uuid,meta.name"
    assert lp.page_size == 3


def test_sdk002_empty_non_complete_page_is_not_absence() -> None:
    page = ResourcePage(
        items=(),
        owner_namespace="tenant.child",
        traverse=False,
        requested_page_size=2,
        page_index=0,
        next_cursor=None,
        stop_reason="max_pages",
        completeness="capped",
        pages_fetched=1,
        items_fetched=0,
    )
    assert page.items == ()
    assert page.completeness != "complete"


def test_sdk002_describe_surfaces_list_pages_twins() -> None:
    desc = describe_resource("Finding")
    assert "list_by_project" in desc.route_methods
    assert "list_pages_by_project" in desc.route_methods
    assert "list_pages_for_context" in desc.route_methods


def test_sdk002_describe_omits_context_pages_without_route_edge() -> None:
    """ScanResult has list_by_project pages, not scan-plane context pages."""
    desc = describe_resource("ScanResult")
    assert "list_pages_by_project" in desc.route_methods
    assert "list_for_context" not in desc.route_methods
    assert "list_pages_for_context" not in desc.route_methods
    assert "list_for_context" not in desc.methods
    assert "list_pages_for_context" not in desc.methods


def test_sdk002_describe_context_kind_includes_page_twin() -> None:
    desc = describe_resource("DependencyMetadata")
    assert "list_for_context" in desc.route_methods
    assert "list_pages_for_context" in desc.route_methods


def test_sdk002_inapplicable_list_for_context_raises() -> None:
    from endorlabs.core.exceptions import RouteNotApplicableError
    from endorlabs.registry import RESOURCE_REGISTRY

    entry = next(e for e in RESOURCE_REGISTRY if e.attr_name == "ScanResult")
    facade = ScanResultFacade(Mock(spec=APIClient), "tenant", entry)
    with pytest.raises(RouteNotApplicableError):
        facade.list_for_context(SimpleNamespace(uuid="scan-1"))


# --- SDK-003 -----------------------------------------------------------------


def test_sdk003_offline_describe_resource_no_client(clear_auth_env: None) -> None:
    desc = describe_resource("Finding")
    assert desc.attr_name == "Finding"
    assert "list_by_project" in desc.route_methods


def test_sdk003_injected_deadline_and_cancel_construct(clear_auth_env: None) -> None:
    import threading

    cancel = threading.Event()
    client = APIClient(deadline_seconds=30.0, cancel_event=cancel)
    assert client is not None
    client.close()


# --- SDK-004 / 008 / 009 / 010 -----------------------------------------------


def test_sdk004_toolchain_facade_without_private_client() -> None:
    from endorlabs.facade.specialized import SupportedToolChainVersionFacade

    api = Mock(spec=APIClient)
    api.get_all.return_value = []
    facade = SupportedToolChainVersionFacade(api, default_namespace="system")
    assert callable(facade.list)


def test_sdk008_draft_update_plan_is_pure() -> None:
    plan = draft_update_plan(
        kind="policy",
        resource_uuid="pol-1",
        namespace="tenant",
        update_mask=["spec.rules"],
        patch={"spec.rules": []},
    )
    assert plan.kind == "policy"
    assert plan.status in {"ready", "rejected"}
    assert any("Planning only" in n for n in plan.notes)
    empty = draft_update_plan(
        kind="policy",
        resource_uuid="pol-1",
        namespace="tenant",
        update_mask=[],
        patch={},
    )
    assert empty.status == "rejected"
    assert empty.rejections


def test_sdk008_rejects_revision_mismatch() -> None:
    plan = draft_update_plan(
        kind="policy",
        resource_uuid="pol-1",
        namespace="tenant",
        update_mask=["spec.rules"],
        patch={"spec.rules": []},
        expected_revision="rev-a",
        current={"meta": {"update_time": "rev-b"}},
    )
    assert plan.status == "rejected"
    assert any("revision" in r for r in plan.rejections)


def test_sdk009_filter_discovery_data_only() -> None:
    ops = describe_filter_operators()
    assert any(o.name == "matches" for o in ops.operators)
    fields = describe_filter_fields("Finding")
    assert any(f.path == "spec.project_uuid" for f in fields.fields)


def test_sdk010_request_observer_optional(clear_auth_env: None) -> None:
    events: list[str] = []

    def observer(event: object) -> None:
        events.append(type(event).__name__)

    client = APIClient(request_observer=observer)
    assert client is not None
    assert events == []
    client.close()


# --- SDK-006 / 007 -----------------------------------------------------------


def test_sdk006_007_library_entrypoints_importable() -> None:
    assert callable(acquire_scan_results)
    assert callable(acquire_scan_logs)
    assert callable(acquire_scan_pair_evidence)
    assert callable(assemble_scan_pair_evidence)
    assert callable(search_embedded_scan_errors)


def test_sdk006_acquire_scan_results_no_filesystem() -> None:
    client = Mock()
    client.ScanResult.list_by_project.return_value = []
    evidence = acquire_scan_results(
        client,
        query_namespace="tenant",
        projects=[{"uuid": "p1", "tenant_meta": {"namespace": "tenant.child"}}],
        limit=5,
    )
    assert evidence.scan_result_count == 0
    assert evidence.project_count == 1
    assert evidence.status == "partial"  # per-project limit → unknown completeness


def test_sdk007_assemble_scan_pair_is_offline() -> None:
    primary = {
        "uuid": "a",
        "spec": {"status": "STATUS_SUCCESS", "start_time": "2024-01-02T00:00:00Z"},
        "meta": {"create_time": "2024-01-02T00:00:00Z", "parent_uuid": "proj-1"},
        "tenant_meta": {"namespace": "tenant.child"},
    }
    secondary = {
        "uuid": "b",
        "spec": {"status": "STATUS_FAILURE", "start_time": "2024-01-01T00:00:00Z"},
        "meta": {"create_time": "2024-01-01T00:00:00Z", "parent_uuid": "proj-1"},
        "tenant_meta": {"namespace": "tenant.child"},
    }
    result = assemble_scan_pair_evidence(
        primary,
        secondary,
        primary_logs=["ok"],
        secondary_logs=[],
    )
    assert result.concurrency == "unknown"
    assert result.primary is not None
    assert result.secondary is not None


def test_sdk007_scope_validation_rejects_order() -> None:
    from endorlabs.workflows.troubleshooting_scans.scan_pair_evidence import (
        ScanPairValidationError,
    )

    newer = {
        "uuid": "a",
        "spec": {"start_time": "2024-01-02T00:00:00Z"},
        "meta": {"parent_uuid": "proj-1"},
        "tenant_meta": {"namespace": "tenant.child"},
    }
    older = {
        "uuid": "b",
        "spec": {"start_time": "2024-01-01T00:00:00Z"},
        "meta": {"parent_uuid": "proj-1"},
        "tenant_meta": {"namespace": "tenant.child"},
    }
    with pytest.raises(ScanPairValidationError, match="previous_scan_not_older"):
        # primary must be newer; swap so secondary is newer → reject
        assemble_scan_pair_evidence(
            older,
            newer,
            namespace="tenant.child",
            project_uuid="proj-1",
            validate_scope=True,
        )


def test_sdk007_acquire_logs_reraises_cancel() -> None:
    from endorlabs.core.exceptions import RequestCancelledError

    client = Mock()
    client.ScanResult.get_logs.side_effect = RequestCancelledError("cancelled")
    with pytest.raises(RequestCancelledError):
        acquire_scan_logs(
            client,
            scan_result_uuid="scan-1",
            namespace="tenant.child",
        )


def test_sdk009_inspect_predicate() -> None:
    from endorlabs.filters import inspect_predicate

    ok = inspect_predicate(
        "Finding",
        {"op": "eq", "path": "meta.name", "value": "demo"},
    )
    assert ok.accepted
    assert ok.wire_filter
    bad = inspect_predicate("Finding", {"op": "explode", "path": "x", "value": 1})
    assert not bad.accepted


def test_sdk005_bom_adjacency_string_cap() -> None:
    from endorlabs.resources.bom_adjacency import validate_bom_adjacency_entry

    validate_bom_adjacency_entry("mvn://x@1")
    validate_bom_adjacency_entry({"name": "x"})
    with pytest.raises(ValueError, match="4096"):
        validate_bom_adjacency_entry("x" * 4097)
    with pytest.raises(TypeError, match="object or string"):
        validate_bom_adjacency_entry(1)


def test_public_package_exports_host_surfaces() -> None:
    assert hasattr(endorlabs, "read_scan_dependency_receipt")
    assert hasattr(endorlabs, "describe_resource")
    assert hasattr(endorlabs, "ResourcePage")
    assert hasattr(endorlabs, "PageCursor")
    assert hasattr(endorlabs, "ClientIdentity")


def test_client_identity_factories_for_hosts() -> None:
    """Hosts use ClientIdentity — sdk/workflow/custom; never forge endorctl."""
    sdk = endorlabs.ClientIdentity.sdk()
    assert sdk.caller == "endorlabs-sdk"
    assert sdk.as_headers()["User-Agent"].startswith("endorlabs-sdk/")
    custom = endorlabs.ClientIdentity.custom(
        caller="example-host", caller_version="1.0.0"
    )
    assert custom.caller == "example-host"
    assert custom.user_agent == "example-host/1.0.0"
    wf = endorlabs.ClientIdentity.workflow("endor-reports")
    assert wf.op_comment is not None
    assert wf.op_comment.startswith("endor-reports/")
