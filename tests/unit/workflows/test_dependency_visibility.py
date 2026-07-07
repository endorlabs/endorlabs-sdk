"""Unit tests for dependency reports and scan log comparison workflows."""

from unittest.mock import Mock

from endorlabs.workflows.dependencies import (
    DependencyReport,
    VisibilityReport,
    check_dependency_visibility,
    list_project_dependencies,
)
from endorlabs.workflows.troubleshooting_scans.scan_logs import (
    ScanLogComparison,
    compare_scan_logs,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_scan_result(
    uuid: str = "sr-1",
    status: str = "COMPLETED",
    exit_code: int = 0,
) -> Mock:
    """Build a mock ScanResult."""
    sr = Mock()
    sr.uuid = uuid
    sr.spec.status = status
    sr.spec.exit_code = exit_code
    sr.spec.start_time = "2025-01-01T00:00:00Z"
    sr.spec.end_time = "2025-01-01T00:10:00Z"
    return sr


def _make_log_message(level: str = "ERROR", payload: str = "bad") -> Mock:
    msg = Mock()
    msg.level = level
    msg.timestamp = "2025-01-01T00:05:00Z"
    msg.json_payload = {"message": payload}
    return msg


def _make_dep(
    uuid: str = "d-1",
    namespace: str = "ns",
    package_name: str = "pkg",
    ecosystem: str = "PYPI",
    importer_name: str = "importer",
    public: bool | None = None,
) -> Mock:
    dep = Mock()
    dep.uuid = uuid
    dep.tenant_meta.namespace = namespace
    dep.spec.dependency_data.package_name = package_name
    dep.spec.dependency_data.resolved_version = "1.0.0"
    dep.spec.dependency_data.scope = None
    dep.spec.dependency_data.reachability = None

    eco = Mock()
    eco.value = ecosystem
    dep.spec.dependency_data.ecosystem = eco

    # model_dump for visibility check
    dep.spec.dependency_data.model_dump.return_value = {
        "package_name": package_name,
        "public": public,
    }

    dep.spec.importer_data.package_name = importer_name
    return dep


# ---------------------------------------------------------------------------
# compare_scan_logs
# ---------------------------------------------------------------------------


class TestCompareScanLogs:
    """Tests for compare_scan_logs."""

    def test_no_scan_results(self) -> None:
        client = Mock()
        client.ScanResult.list_by_project.return_value = []

        result = compare_scan_logs(client, "ns", "proj-1")
        assert isinstance(result, ScanLogComparison)
        assert result.num_scans_found == 0
        assert result.entries == []

    def test_fetches_logs_for_each_scan(self) -> None:
        sr1 = _make_scan_result("sr-1")
        sr2 = _make_scan_result("sr-2", status="FAILED", exit_code=1)
        client = Mock()
        client.ScanResult.list_by_project.return_value = [sr1, sr2]
        client.ScanResult.get_logs.return_value = [
            _make_log_message("ERROR", "something failed")
        ]

        result = compare_scan_logs(client, "ns", "proj-1", num_scans=2)
        assert result.num_scans_found == 2
        assert len(result.entries) == 2
        assert client.ScanResult.get_logs.call_count == 2

    def test_handles_log_fetch_failure(self) -> None:
        sr = _make_scan_result("sr-1")
        client = Mock()
        client.ScanResult.list_by_project.return_value = [sr]
        client.ScanResult.get_logs.side_effect = RuntimeError("timeout")

        result = compare_scan_logs(client, "ns", "proj-1")
        assert len(result.entries) == 1
        assert "error" in result.entries[0].log_messages[0]

    def test_respects_num_scans(self) -> None:
        client = Mock()
        client.ScanResult.list_by_project.return_value = [
            _make_scan_result(f"sr-{i}") for i in range(5)
        ]
        client.ScanResult.get_logs.return_value = []

        result = compare_scan_logs(client, "ns", "proj-1", num_scans=3)
        assert len(result.entries) == 3

    def test_custom_log_levels(self) -> None:
        sr = _make_scan_result("sr-1")
        client = Mock()
        client.ScanResult.list_by_project.return_value = [sr]
        client.ScanResult.get_logs.return_value = []

        compare_scan_logs(client, "ns", "proj-1", log_levels=["ERROR", "INFO"])
        call_kwargs = client.ScanResult.get_logs.call_args.kwargs
        assert len(call_kwargs["log_levels"]) == 2


# ---------------------------------------------------------------------------
# list_project_dependencies
# ---------------------------------------------------------------------------


class TestListProjectDependencies:
    """Tests for list_project_dependencies."""

    def test_empty_results(self) -> None:
        client = Mock()
        client.DependencyMetadata.list.return_value = []

        result = list_project_dependencies(client, "ns")
        assert isinstance(result, DependencyReport)
        assert result.stats.total == 0

    def test_aggregates_statistics(self) -> None:
        d1 = _make_dep("d-1", "ns1", "pkg-a", "PYPI", "imp-a")
        d2 = _make_dep("d-2", "ns1", "pkg-b", "NPM", "imp-b")
        d3 = _make_dep("d-3", "ns2", "pkg-a", "PYPI", "imp-a")

        client = Mock()
        client.DependencyMetadata.list.return_value = [d1, d2, d3]

        result = list_project_dependencies(client, "ns")
        assert result.stats.total == 3
        assert result.stats.by_namespace["ns1"] == 2
        assert result.stats.by_namespace["ns2"] == 1
        assert result.stats.by_ecosystem["PYPI"] == 2
        assert result.stats.by_ecosystem["NPM"] == 1
        assert result.stats.unique_packages == 2  # pkg-a, pkg-b
        assert len(result.dependencies) == 3

    def test_traverse_kwarg_forwarded(self) -> None:
        client = Mock()
        client.DependencyMetadata.list.return_value = []

        list_project_dependencies(client, "ns", traverse=False)
        assert client.DependencyMetadata.list.call_args.kwargs["traverse"] is False


# ---------------------------------------------------------------------------
# check_dependency_visibility
# ---------------------------------------------------------------------------


class TestCheckDependencyVisibility:
    """Tests for check_dependency_visibility."""

    def test_counts_visibility(self) -> None:
        d_pub = _make_dep("d-1", public=True)
        d_priv = _make_dep("d-2", public=False)
        d_unk = _make_dep("d-3", public=None)

        client = Mock()
        client.DependencyMetadata.list.return_value = [d_pub, d_priv, d_unk]

        result = check_dependency_visibility(client, "ns")
        assert isinstance(result, VisibilityReport)
        assert result.stats.total == 3
        assert result.stats.public == 1
        assert result.stats.private == 1
        assert result.stats.unknown == 1

    def test_filter_public_kwarg(self) -> None:
        client = Mock()
        client.DependencyMetadata.list.return_value = []

        check_dependency_visibility(client, "ns", filter_public=True)
        kw = client.DependencyMetadata.list.call_args.kwargs
        assert "true" in kw["filter"]

    def test_no_filter_when_none(self) -> None:
        client = Mock()
        client.DependencyMetadata.list.return_value = []

        check_dependency_visibility(client, "ns")
        kw = client.DependencyMetadata.list.call_args.kwargs
        assert "filter" not in kw
