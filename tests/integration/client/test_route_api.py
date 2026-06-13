"""Live integration tests for generated facade accessor helpers."""

from __future__ import annotations

import pytest

import endorlabs
from endorlabs.core.exceptions import RouteNotApplicableError, ServerError
from endorlabs.facade.context_partition import context_partition_filter
from endorlabs.operations.routes import RouteResult
from tests.conftest import TEST_MAX_PAGES


@pytest.mark.integration
class TestRouteAPI:
    """Validate stitched routes against a live tenant (bounded reads)."""

    @pytest.fixture(autouse=True)
    def setup_client(self, api_client, namespace) -> None:
        self.client = endorlabs.Client(tenant=namespace, api_client=api_client)

    def _first_project(self):
        try:
            projects = self.client.Project.list(max_pages=TEST_MAX_PAGES)
        except ServerError as err:
            pytest.skip(f"Project list unavailable: {err}")
        if not projects:
            pytest.skip("No projects in scope")
        return projects[0]

    def _first_scan(self, project):
        try:
            scan_result = self.client.ScanResult.list_by_project(
                project,
                max_pages=TEST_MAX_PAGES,
            )
        except ServerError as err:
            pytest.skip(f"ScanResult list unavailable: {err}")
        if not scan_result.values:
            pytest.skip("No scan results for project")
        scan = scan_result.values[0]
        ctx = getattr(scan, "context", None)
        if ctx is None or not getattr(ctx, "type", None):
            pytest.skip("Scan has no usable context partition")
        return project, scan

    def test_finding_list_by_project_returns_route_result(self) -> None:
        project = self._first_project()
        result = self.client.Finding.list_by_project(
            project,
            max_pages=TEST_MAX_PAGES,
        )
        assert isinstance(result, RouteResult)
        assert result.edge_used == "project.findings"
        assert result.values is not None
        assert isinstance(result.values, list)

    def test_scan_result_list_by_project_returns_route_result(self) -> None:
        project = self._first_project()
        result = self.client.ScanResult.list_by_project(
            project,
            max_pages=TEST_MAX_PAGES,
        )
        assert isinstance(result, RouteResult)
        assert result.edge_used == "project.scan_results"
        assert result.values is not None

    def test_finding_list_for_context_matches_scan_plane(self) -> None:
        _project, scan = self._first_scan(self._first_project())
        try:
            result = self.client.Finding.list_for_context(
                scan,
                max_pages=TEST_MAX_PAGES,
            )
        except ServerError as err:
            pytest.skip(f"Finding list_for_context unavailable: {err}")
        assert result.edge_used == "scan.findings"
        assert result.values is not None

    def test_finding_list_for_context_partition_integrity(self) -> None:
        _project, scan = self._first_scan(self._first_project())
        ctx = scan.context
        try:
            result = self.client.Finding.list_for_context(
                scan,
                max_pages=TEST_MAX_PAGES,
            )
        except ServerError as err:
            pytest.skip(f"Finding list_for_context unavailable: {err}")
        for row in (result.values or [])[:5]:
            row_ctx = getattr(row, "context", None)
            assert row_ctx is not None
            assert getattr(row_ctx, "type", None) == getattr(ctx, "type", None)
            ctx_id = getattr(ctx, "id", None)
            if ctx_id:
                assert getattr(row_ctx, "id", None) == ctx_id

    def test_finding_list_for_context_equivalent_to_manual_filter(self) -> None:
        project, scan = self._first_scan(self._first_project())
        try:
            accessor = self.client.Finding.list_for_context(
                scan,
                max_pages=TEST_MAX_PAGES,
            )
            manual = self.client.Finding.list_by_project(
                project,
                filter=context_partition_filter(scan.context),
                max_pages=TEST_MAX_PAGES,
            )
        except ServerError as err:
            pytest.skip(f"Finding partition list unavailable: {err}")
        accessor_ids = {getattr(r, "uuid", None) for r in (accessor.values or [])}
        manual_ids = {getattr(r, "uuid", None) for r in (manual.values or [])}
        assert accessor_ids.issubset(manual_ids)

    @pytest.mark.parametrize(
        ("edge_id", "list_method"),
        [
            ("scan.package_versions", "PackageVersion"),
            ("scan.dependency_metadata", "DependencyMetadata"),
        ],
    )
    def test_list_for_context_partition_smoke(
        self, edge_id: str, list_method: str
    ) -> None:
        _project, scan = self._first_scan(self._first_project())
        facade = getattr(self.client, list_method)
        try:
            result = facade.list_for_context(scan, max_pages=TEST_MAX_PAGES)
        except ServerError as err:
            pytest.skip(f"{list_method} list_for_context unavailable: {err}")
        assert result.edge_used == edge_id
        assert result.values is not None

    def test_finding_to_dependency_metadata_when_target_present(self) -> None:
        project = self._first_project()
        findings = self.client.Finding.list_by_project(
            project,
            max_pages=TEST_MAX_PAGES,
        )
        if not findings.values:
            pytest.skip("No findings for project")
        target_finding = None
        for row in findings.values:
            spec = getattr(row, "spec", None)
            target_uuid = getattr(spec, "target_uuid", None) if spec else None
            if target_uuid:
                target_finding = row
                break
        if target_finding is None:
            pytest.skip("No finding with spec.target_uuid in sample")
        try:
            result = self.client.Finding.to_dependency_metadata(target_finding)
        except RouteNotApplicableError:
            pytest.skip("DependencyMetadata route not applicable for sample finding")
        assert result.edge_used.startswith("finding.dependency_metadata")
        assert result.value is not None or result.values

    def test_package_version_list_by_project_returns_route_result(self) -> None:
        project = self._first_project()
        result = self.client.PackageVersion.list_by_project(
            project,
            max_pages=TEST_MAX_PAGES,
        )
        assert isinstance(result, RouteResult)
        assert result.edge_used == "project.package_versions"
        assert result.values is not None
