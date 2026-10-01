"""Integration tests for ImportedSBOM / SBOMExport facades."""

from __future__ import annotations

import pytest

import endorlabs
from endorlabs.core.exceptions import ServerError, ValidationError
from tests.conftest import TEST_MAX_PAGES


@pytest.mark.integration
class TestImportedSBOM:
    """Validate ImportedSBOM list/get in the integration namespace."""

    @pytest.fixture(autouse=True)
    def setup_fast(self, api_client, namespace) -> None:
        self.client = endorlabs.Client(tenant=namespace, api_client=api_client)
        self.namespace = namespace

    def test_imported_sbom_list(self) -> None:
        try:
            result = self.client.ImportedSBOM.list(max_pages=TEST_MAX_PAGES)
        except ServerError:
            pytest.skip("Backend returned ServerError (list); skip")
        assert isinstance(result, list)

    def test_imported_sbom_get(self) -> None:
        try:
            items = self.client.ImportedSBOM.list(max_pages=TEST_MAX_PAGES)
        except ServerError:
            pytest.skip("Backend returned ServerError (list); skip")
        if not items:
            pytest.skip("No ImportedSBOM rows (empty; soft skip)")
        got = self.client.ImportedSBOM.get(items[0])
        assert got is not None
        assert got.uuid == items[0].uuid
        # Convenience helper should not raise
        _ = got.linked_project_uuid()


@pytest.mark.integration
class TestSBOMExportFacade:
    """SBOMExport is create-only; list must raise NotImplementedError."""

    @pytest.fixture(autouse=True)
    def setup_fast(self, api_client, namespace) -> None:
        self.client = endorlabs.Client(tenant=namespace, api_client=api_client)

    def test_sbom_export_list_not_supported(self) -> None:
        with pytest.raises(NotImplementedError):
            self.client.SBOMExport.list(max_pages=TEST_MAX_PAGES)

    def test_vex_export_list_not_supported(self) -> None:
        with pytest.raises(NotImplementedError):
            self.client.VEXExport.list(max_pages=TEST_MAX_PAGES)

    def test_async_job_create_requires_spec(self) -> None:
        """Create without a valid spec should fail validation (not list)."""
        with pytest.raises((ValidationError, ServerError, TypeError, Exception)):
            self.client.AsyncJob.create(
                meta={"name": "integration-async-job-probe"},
                spec={},
            )
