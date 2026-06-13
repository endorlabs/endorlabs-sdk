"""Live integration tests for wire/auxiliary facade helpers."""

from __future__ import annotations

import pytest

from endorlabs.core.exceptions import NotFoundError, ServerError
from tests.conftest import TEST_MAX_PAGES, TEST_SCAN_LOG_MAX_ENTRIES
from tests.integration.client.conftest import (
    require_first_project,
)
from tests.integration.client.helper_assertions import nested_attr


@pytest.mark.integration
class TestFacadeWireHelpers:
    """Validate ScanResult.get_logs and CallGraphData decode/fetch on live data."""

    @pytest.fixture(autouse=True)
    def setup_client(self, facade_client) -> None:
        self.client = facade_client

    def test_scan_result_get_logs_for_sample_scan(self) -> None:
        project = require_first_project(self.client)
        route = self.client.ScanResult.list_by_project(
            project,
            max_pages=TEST_MAX_PAGES,
        )
        if not route.values:
            pytest.skip("No scan results for project")
        scan = route.values[0]
        try:
            logs = self.client.ScanResult.get_logs(
                scan,
                max_entries=TEST_SCAN_LOG_MAX_ENTRIES,
            )
        except ServerError as err:
            pytest.skip(f"ScanResult.get_logs unavailable: {err}")
        assert isinstance(logs, list)
        assert len(logs) <= TEST_SCAN_LOG_MAX_ENTRIES
        for entry in logs[:TEST_SCAN_LOG_MAX_ENTRIES]:
            assert hasattr(entry, "timestamp") or hasattr(entry, "level")

    def test_call_graph_data_fetch_and_decode_for_package_version(self) -> None:
        project = require_first_project(self.client)
        try:
            pv_route = self.client.PackageVersion.list_by_project(
                project,
                max_pages=TEST_MAX_PAGES,
            )
        except ServerError as err:
            pytest.skip(f"PackageVersion list unavailable: {err}")
        if not pv_route.values:
            pytest.skip("No package versions for project")
        decoded_any = False
        ns = project.namespace
        if not ns:
            pytest.skip("Project has no namespace for CallGraphData fetch")
        for pv in pv_route.values[:5]:
            try:
                envelope = self.client.CallGraphData.fetch(pv, namespace=ns)
            except NotFoundError:
                continue
            except ServerError as err:
                pytest.skip(f"CallGraphData fetch unavailable: {err}")
            assert isinstance(envelope, dict)
            assert envelope.get("uuid") or envelope.get("meta")
            decoded = self.client.CallGraphData.decode(pv, namespace=ns)
            assert decoded.summary is not None
            assert isinstance(decoded.callables, list)
            assert isinstance(decoded.edges, list)
            decoded_any = True
            break
        if not decoded_any:
            pytest.skip("No CallGraphData rows for sampled package versions")

    def test_scan_result_latest_created_for_project(self) -> None:
        project = require_first_project(self.client)
        route = self.client.ScanResult.list_by_project(
            project,
            max_pages=TEST_MAX_PAGES,
        )
        if not route.values:
            pytest.skip("No scan results for project")
        try:
            latest = self.client.ScanResult.latest_created(parent=project)
        except ServerError as err:
            pytest.skip(f"ScanResult.latest_created unavailable: {err}")
        if latest is None:
            pytest.skip("ScanResult.latest_created returned no row")
        assert nested_attr(latest, "meta.parent_uuid") == project.uuid
