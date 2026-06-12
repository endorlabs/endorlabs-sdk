"""Live integration tests for generated facade accessor helpers."""

from __future__ import annotations

import pytest

import endorlabs
from endorlabs.core.exceptions import (
    RouteNotApplicableError,
    ServerError,
    ValidationError,
)
from endorlabs.operations.routes import RouteResult
from endorlabs.utils.namespace import resolve_namespace_for_resource
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

    def test_finding_list_by_scan_when_scan_exists(self) -> None:
        project = self._first_project()
        project_ns = resolve_namespace_for_resource(
            project, getattr(self.client, "_default_namespace", None)
        )
        scan_result = self.client.ScanResult.list_by_project(
            project,
            namespace=project_ns,
            max_pages=TEST_MAX_PAGES,
        )
        if not scan_result.values:
            pytest.skip("No scan results for project")
        scan = scan_result.values[0]
        try:
            result = self.client.Finding.list_by_scan(
                scan,
                max_pages=TEST_MAX_PAGES,
            )
        except (ServerError, ValidationError) as err:
            if "context.scan_uuid" in str(err):
                pytest.skip("context.scan_uuid not filterable in this namespace")
            pytest.skip(f"Finding list_by_scan unavailable: {err}")
        assert result.edge_used == "scan.findings"
        assert result.warnings
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
