"""Consolidated unit tests for greenfield attribute aliases across resources.

Each test class validates that a resource exposes the greenfield (renamed)
attribute names and that model_dump(by_alias=True) serialises them correctly.
"""

from endorlabs.resources.finding import Finding
from endorlabs.resources.finding_log import FindingLog
from endorlabs.resources.project import Project, ProjectMeta
from endorlabs.resources.scan_result import ScanResult


class TestProjectGreenfieldAlias:
    """Unit tests: greenfield attribute names (processing_status, index_data).

    These tests assert .processing_status and .meta.index_data and serialization
    so that after renaming project_processing_status -> processing_status and
    project_index_data -> index_data, they pass without change.
    """

    def test_project_processing_status_attribute_and_serialization(self) -> None:
        """Project exposes .processing_status and serializes as 'processing_status'."""
        payload = {
            "uuid": "proj-uuid",
            "meta": {"name": "proj-meta"},
            "spec": {},
            "tenant_meta": {"namespace": "test-ns"},
            "processing_status": {
                "disable_automated_scan": False,
                "scan_state": "idle",
            },
        }
        project = Project(**payload)
        assert project.processing_status is not None
        assert getattr(project.processing_status, "scan_state", None) == "idle"
        dumped = project.model_dump(by_alias=True)
        assert "processing_status" in dumped
        assert dumped["processing_status"] is not None

    def test_project_meta_index_data_attribute_and_serialization(self) -> None:
        """ProjectMeta exposes .index_data and serializes with key 'index_data'."""
        meta = ProjectMeta(
            name="proj-meta",
            index_data={"data": ["d1"], "tenant": "t1"},
        )
        assert getattr(meta, "index_data", None) is not None
        index_data = getattr(meta, "index_data", None)
        assert index_data is not None
        if hasattr(index_data, "tenant"):
            assert index_data.tenant == "t1"
        else:
            assert index_data.get("tenant") == "t1"
        dumped_meta = meta.model_dump(by_alias=True)
        assert "index_data" in dumped_meta
        assert dumped_meta["index_data"] is not None


class TestFindingGreenfieldAlias:
    """Unit tests: greenfield attribute names (context) and serialization.

    These tests assert .context and model_dump(by_alias=True)["context"] so that
    after renaming finding_context -> context, they pass without change.
    """

    def test_finding_context_attribute_and_serialization(self) -> None:
        """Finding exposes .context and serializes with key 'context'."""
        payload = {
            "uuid": "test-uuid",
            "meta": {"name": "test-finding"},
            "spec": {},
            "tenant_meta": {"namespace": "test-ns"},
            "context": {"id": "c1", "type": "scan"},
        }
        finding = Finding(**payload)
        assert finding.context is not None
        assert getattr(finding.context, "id", None) == "c1"
        dumped = finding.model_dump(by_alias=True)
        assert "context" in dumped
        assert dumped["context"] is not None


class TestFindingLogGreenfieldAlias:
    """Unit tests: greenfield attribute names (context) and serialization.

    These tests assert .context and model_dump(by_alias=True)['context'] so that
    after renaming finding_log_context -> context, they pass without change.
    """

    def test_finding_log_context_attribute_and_serialization(self) -> None:
        """FindingLog exposes .context and serializes with key 'context'."""
        minimal_spec = {
            "finding_uuid": "f1",
            "finding_parent_kind": "Finding",
            "finding_parent_uuid": "p1",
            "operation": "CREATE",
            "introduced_at": "2020-01-01T00:00:00Z",
            "method": "METHOD_UNSPECIFIED",
            "level": "FINDING_LEVEL_UNSPECIFIED",
            "finding_tags": [],
            "finding_categories": [],
        }
        payload = {
            "uuid": "log-uuid",
            "meta": {"name": "log-meta"},
            "spec": minimal_spec,
            "tenant_meta": {"namespace": "test-ns"},
            "context": {"id": "c1", "type": "scan"},
        }
        finding_log_obj = FindingLog(**payload)
        assert finding_log_obj.context is not None
        assert getattr(finding_log_obj.context, "id", None) == "c1"
        dumped = finding_log_obj.model_dump(by_alias=True)
        assert "context" in dumped
        assert dumped["context"] is not None


class TestScanResultGreenfieldAlias:
    """Unit tests: greenfield attribute names (context) and serialization.

    These tests assert .context and model_dump(by_alias=True)['context'] so that
    after renaming scan_result_context -> context, they pass without change.
    """

    def test_scan_result_context_attribute_and_serialization(self) -> None:
        """ScanResult exposes .context and serializes with key 'context'."""
        payload = {
            "uuid": "scan-uuid",
            "meta": {"name": "scan-meta"},
            "tenant_meta": {"namespace": "test-ns"},
            "context": {"id": "c1", "type": "scan"},
        }
        scan_result_obj = ScanResult(**payload)
        assert scan_result_obj.context is not None
        assert getattr(scan_result_obj.context, "id", None) == "c1"
        dumped = scan_result_obj.model_dump(by_alias=True)
        assert "context" in dumped
        assert dumped["context"] is not None
