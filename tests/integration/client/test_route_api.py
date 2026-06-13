"""Live integration tests for generated facade accessor helpers."""

from __future__ import annotations

import pytest

from endorlabs.core.exceptions import (
    RouteNotApplicableError,
    ServerError,
)
from endorlabs.facade.context_partition import context_partition_filter
from endorlabs.operations.routes import RouteResult
from tests.conftest import TEST_MAX_PAGES
from tests.integration.client.conftest import (
    require_first_project,
    require_list_for_context_sample,
    require_scan_with_context,
    resource_has_rows_in_scope,
)
from tests.integration.client.helper_assertions import (
    CONTEXT_PARTITION_ANCHORS,
    assert_rows_have_field_value,
    assert_scan_context_partition,
    nested_attr,
)

# Kinds whose list rows reliably expose the same scan context partition on the wire.
CONTEXT_ON_ROW_KINDS = frozenset({"Finding", "FindingLog"})
SCAN_CONTEXT_LIST_METHODS: tuple[tuple[str, str], ...] = (
    ("scan.findings", "Finding"),
    ("scan.package_versions", "PackageVersion"),
    ("scan.dependency_metadata", "DependencyMetadata"),
    ("scan.repository_versions", "RepositoryVersion"),
    ("scan.finding_logs", "FindingLog"),
    ("scan.linter_results", "LinterResult"),
    ("scan.metrics", "Metric"),
    ("scan.package_licenses", "PackageLicense"),
    ("scan.scan_workflow_results", "ScanWorkflowResult"),
    ("scan.version_upgrades", "VersionUpgrade"),
)


@pytest.mark.integration
class TestRouteAPI:
    """Validate stitched routes return the intended resources on a live tenant."""

    @pytest.fixture(autouse=True)
    def setup_client(
        self, facade_client, facade_root_client, facade_oss_client
    ) -> None:
        self.client = facade_client
        self.root_client = facade_root_client
        self.oss_client = facade_oss_client

    def test_linter_result_list_for_context_when_tenant_has_rows(self) -> None:
        """LinterResult exists in many tenants but not every scan plane — probe, do not skip blindly."""
        if not resource_has_rows_in_scope(
            self.client, "LinterResult", root_client=self.root_client
        ):
            pytest.skip("No LinterResult rows in tenant scope")
        _project, scan, result = require_list_for_context_sample(
            self.client,
            "LinterResult",
            "scan.linter_results",
            root_client=self.root_client,
        )
        assert result.edge_used == "scan.linter_results"
        project_uuid = nested_attr(scan, "meta.parent_uuid")
        if project_uuid:
            assert_rows_have_field_value(
                result.values or [],
                "spec.project_uuid",
                str(project_uuid),
            )

    def test_package_license_list_for_context_skips_only_when_absent(self) -> None:
        """PackageLicense catalog rows live on the ``oss`` namespace path — probe it."""
        if not resource_has_rows_in_scope(
            self.client,
            "PackageLicense",
            root_client=self.root_client,
            oss_client=self.oss_client,
        ):
            pytest.skip(
                "No PackageLicense rows in tenant or oss scope; "
                "list_for_context scan-plane test not applicable"
            )
        _project, scan, result = require_list_for_context_sample(
            self.client,
            "PackageLicense",
            "scan.package_licenses",
            root_client=self.root_client,
            oss_client=self.oss_client,
        )
        assert result.edge_used == "scan.package_licenses"
        assert result.values
        project_uuid = nested_attr(scan, "meta.parent_uuid")
        if project_uuid:
            assert_rows_have_field_value(
                result.values or [],
                "spec.project_uuid",
                str(project_uuid),
            )

    def test_finding_list_by_project_scoped_to_source(self) -> None:
        project = require_first_project(self.client)
        result = self.client.Finding.list_by_project(
            project,
            max_pages=TEST_MAX_PAGES,
        )
        assert isinstance(result, RouteResult)
        assert result.edge_used == "project.findings"
        assert result.values is not None
        if result.values:
            assert_rows_have_field_value(
                result.values,
                "spec.project_uuid",
                project.uuid,
            )

    def test_scan_result_list_by_project_scoped_to_source(self) -> None:
        project = require_first_project(self.client)
        result = self.client.ScanResult.list_by_project(
            project,
            max_pages=TEST_MAX_PAGES,
        )
        assert isinstance(result, RouteResult)
        assert result.edge_used == "project.scan_results"
        assert result.values is not None
        if result.values:
            assert_rows_have_field_value(
                result.values,
                "meta.parent_uuid",
                project.uuid,
            )

    def test_package_version_list_by_project_scoped_to_source(self) -> None:
        project = require_first_project(self.client)
        result = self.client.PackageVersion.list_by_project(
            project,
            max_pages=TEST_MAX_PAGES,
        )
        assert isinstance(result, RouteResult)
        assert result.edge_used == "project.package_versions"
        assert result.values is not None
        if result.values:
            assert_rows_have_field_value(
                result.values,
                "spec.project_uuid",
                project.uuid,
            )

    def test_finding_list_for_context_partition_integrity(self) -> None:
        _project, scan = require_scan_with_context(
            self.client, require_first_project(self.client)
        )
        try:
            result = self.client.Finding.list_for_context(
                scan,
                max_pages=TEST_MAX_PAGES,
            )
        except ServerError as err:
            pytest.skip(f"Finding list_for_context unavailable: {err}")
        assert result.edge_used == "scan.findings"
        if result.values:
            assert_scan_context_partition(result.values, scan)
            project_uuid = nested_attr(scan, "meta.parent_uuid")
            if project_uuid:
                assert_rows_have_field_value(
                    result.values,
                    "spec.project_uuid",
                    str(project_uuid),
                )

    def test_finding_list_for_context_equivalent_to_manual_filter(self) -> None:
        project, scan = require_scan_with_context(
            self.client, require_first_project(self.client)
        )
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
        accessor_ids = {nested_attr(r, "uuid") for r in (accessor.values or [])}
        manual_ids = {nested_attr(r, "uuid") for r in (manual.values or [])}
        assert accessor_ids.issubset(manual_ids)

    @pytest.mark.parametrize(("edge_id", "list_method"), SCAN_CONTEXT_LIST_METHODS)
    def test_list_for_context_returns_intended_resources(
        self, edge_id: str, list_method: str
    ) -> None:
        _project, scan, result = require_list_for_context_sample(
            self.client,
            list_method,
            edge_id,
            root_client=self.root_client,
            oss_client=self.oss_client,
        )
        assert result.edge_used == edge_id
        assert result.values is not None
        assert result.values, (
            f"require_list_for_context_sample returned empty {list_method}"
        )
        if list_method in CONTEXT_ON_ROW_KINDS:
            assert_scan_context_partition(result.values, scan)
        anchor = CONTEXT_PARTITION_ANCHORS.get(list_method)
        if anchor is not None:
            row_field, scan_field = anchor
            expected = nested_attr(scan, scan_field)
            if expected:
                assert_rows_have_field_value(result.values, row_field, str(expected))

    def test_finding_to_dependency_metadata_matches_target(self) -> None:
        project = require_first_project(self.client)
        findings = self.client.Finding.list_by_project(
            project,
            max_pages=TEST_MAX_PAGES,
        )
        if not findings.values:
            pytest.skip("No findings for project")
        target_finding = None
        for row in findings.values:
            target_uuid = nested_attr(row, "spec.target_uuid")
            if target_uuid:
                target_finding = row
                break
        if target_finding is None:
            pytest.skip("No finding with spec.target_uuid in sample")
        target_uuid = nested_attr(target_finding, "spec.target_uuid")
        try:
            result = self.client.Finding.to_dependency_metadata(target_finding)
        except RouteNotApplicableError:
            pytest.skip("DependencyMetadata route not applicable for sample finding")
        assert result.edge_used.startswith("finding.dependency_metadata")
        if result.edge_used == "finding.dependency_metadata.get":
            assert result.value is not None
            assert nested_attr(result.value, "uuid") == target_uuid
        elif result.values:
            uuids = {nested_attr(row, "uuid") for row in result.values}
            assert target_uuid in uuids
        else:
            pytest.skip("DependencyMetadata route returned no rows for sample finding")

    def test_scan_result_parent_returns_project(self) -> None:
        project = require_first_project(self.client)
        route = self.client.ScanResult.list_by_project(
            project,
            max_pages=TEST_MAX_PAGES,
        )
        if not route.values:
            pytest.skip("No scan results for project")
        scan = route.values[0]
        parent_uuid = nested_attr(scan, "meta.parent_uuid")
        if not parent_uuid:
            pytest.skip("Scan result has no meta.parent_uuid")
        parent = self.client.ScanResult.parent(scan)
        assert nested_attr(parent, "uuid") == parent_uuid

    def test_finding_count_matches_bounded_list(self) -> None:
        project = require_first_project(self.client)
        ns = project.namespace
        if not ns:
            pytest.skip("Project has no namespace for count scope")
        try:
            route = self.client.Finding.list_by_project(
                project,
                max_pages=TEST_MAX_PAGES,
            )
            total = self.client.Finding.count(
                namespace=ns,
                filter=f'spec.project_uuid=="{project.uuid}"',
            )
        except ServerError as err:
            pytest.skip(f"Finding count unavailable: {err}")
        listed = len(route.values or [])
        assert total >= listed
