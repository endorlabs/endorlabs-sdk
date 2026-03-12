"""Test cases for model consistency utilities.

Tests enumerate_spec_top_level_refs, compute_attribute_overlap_report,
and integration in run_model_consistency_report (attribute overlap section).

The module under test lives in .github/scripts/ (CI/analysis tooling, not
shipped in the library).  sys.path is adjusted so ``import model_consistency``
resolves to that file.
"""

import sys
from pathlib import Path

import pytest

# model_consistency.py lives in .github/scripts/ (not in the installed package)
_repo_root = Path(__file__).resolve().parent.parent.parent.parent
_scripts_dir = str(_repo_root / ".github" / "scripts")
if _scripts_dir not in sys.path:
    sys.path.insert(0, _scripts_dir)

from model_consistency import (
    compute_attribute_overlap_report,
    compute_flatten_collision_report,
    compute_model_consistency_diff,
    enumerate_sdk_models_flat_paths,
    enumerate_spec_top_level_refs,
    get_shared_sdk_paths,
    load_spec,
    path_to_flattened,
    run_model_consistency_report,
)


def _minimal_spec_with_overlap_and_collision() -> dict:
    """Minimal OpenAPI definitions: shared meta/context refs and one collision."""
    return {
        "definitions": {
            "v1Meta": {"type": "object", "properties": {"name": {"type": "string"}}},
            "v1Context": {"type": "object", "properties": {"tags": {"type": "array"}}},
            "v1Finding": {
                "type": "object",
                "properties": {
                    "uuid": {"type": "string"},
                    "meta": {"$ref": "#/definitions/v1Meta"},
                    "context": {"$ref": "#/definitions/v1Context"},
                },
            },
            "v1Project": {
                "type": "object",
                "properties": {
                    "meta": {"$ref": "#/definitions/v1Meta"},
                    "name": {"type": "string"},
                },
            },
            "v1Collision": {
                "type": "object",
                "properties": {
                    "context": {"type": "string"},
                },
            },
        },
    }


class TestEnumerateSpecTopLevelRefs:
    """Tests for enumerate_spec_top_level_refs."""

    def test_returns_definition_to_prop_ref_pairs(self) -> None:
        spec = _minimal_spec_with_overlap_and_collision()
        names = {"v1Finding", "v1Project", "v1Collision", "v1Meta", "v1Context"}
        result = enumerate_spec_top_level_refs(spec, definition_names=names)
        assert "v1Finding" in result
        assert ("meta", "v1Meta") in result["v1Finding"]
        assert ("context", "v1Context") in result["v1Finding"]
        assert ("uuid", "string") in result["v1Finding"]
        assert ("meta", "v1Meta") in result["v1Project"]
        assert ("context", "string") in result["v1Collision"]

    def test_skips_missing_definitions(self) -> None:
        spec = _minimal_spec_with_overlap_and_collision()
        result = enumerate_spec_top_level_refs(
            spec, definition_names={"v1Finding", "v1Nonexistent"}
        )
        assert "v1Finding" in result
        assert "v1Nonexistent" not in result


class TestComputeAttributeOverlapReport:
    """Tests for compute_attribute_overlap_report."""

    def test_overlap_includes_meta_and_context(self) -> None:
        spec = _minimal_spec_with_overlap_and_collision()
        names = {"v1Finding", "v1Project", "v1Collision", "v1Meta", "v1Context"}
        report = compute_attribute_overlap_report(spec, definition_names=names)
        overlap = report["attribute_overlap"]
        assert "meta" in overlap
        assert "context" in overlap
        assert len(overlap["meta"]) >= 2
        assert len(overlap["context"]) >= 2

    def test_same_meaning_includes_meta(self) -> None:
        spec = _minimal_spec_with_overlap_and_collision()
        names = {"v1Finding", "v1Project", "v1Collision", "v1Meta", "v1Context"}
        report = compute_attribute_overlap_report(spec, definition_names=names)
        assert "meta" in report["same_meaning"]
        # meta appears in v1Finding and v1Project with same ref v1Meta
        assert "meta" not in report["collisions"]

    def test_collisions_includes_context_when_refs_differ(self) -> None:
        spec = _minimal_spec_with_overlap_and_collision()
        names = {"v1Finding", "v1Project", "v1Collision", "v1Meta", "v1Context"}
        report = compute_attribute_overlap_report(spec, definition_names=names)
        # v1Finding.context -> v1Context, v1Collision.context -> string
        assert "context" in report["collisions"]
        assert "context" not in report["same_meaning"]

    def test_same_meaning_and_collisions_are_sorted(self) -> None:
        spec = _minimal_spec_with_overlap_and_collision()
        names = {"v1Finding", "v1Project", "v1Collision", "v1Meta", "v1Context"}
        report = compute_attribute_overlap_report(spec, definition_names=names)
        assert report["same_meaning"] == sorted(report["same_meaning"])
        assert report["collisions"] == sorted(report["collisions"])


class TestRunModelConsistencyReportAttributeOverlap:
    """Tests that run_model_consistency_report includes attribute_overlap_report."""

    def test_report_contains_attribute_overlap_report_and_summary(self) -> None:
        from pathlib import Path

        # Run with default (loads from path or URL); skip if spec unavailable
        spec_path = Path(".endorlabs-context/openapiv2.swagger.json")
        if not spec_path.exists():
            pytest.skip("OpenAPI spec not present (run sync or use --spec-url)")
        report = run_model_consistency_report(
            spec_path=spec_path,
            output_file=Path("model_consistency_report_test_out"),
            output_format="json",
        )
        assert "attribute_overlap_report" in report
        assert "attribute_overlap" in report["attribute_overlap_report"]
        assert "same_meaning" in report["attribute_overlap_report"]
        assert "collisions" in report["attribute_overlap_report"]
        assert "overlap_attribute_count" in report["summary"]
        assert "same_meaning_count" in report["summary"]
        assert "collisions_count" in report["summary"]
        # Clean up generated file
        for suf in [".json", ".txt"]:
            p = Path("model_consistency_report_test_out" + suf)
            if p.exists():
                p.unlink()


class TestModelConsistencyUtilities:
    """Additional utility coverage for model consistency helpers."""

    def test_path_to_flattened_processing_status(self) -> None:
        assert path_to_flattened("processing_status.scan_state") == "scan_state"
        assert path_to_flattened("meta.description") == "meta_description"

    def test_compute_flatten_collision_report_detects_collision(self) -> None:
        spec = {
            "definitions": {
                "v1ProcessingStatus": {
                    "type": "object",
                    "properties": {"scan_state": {"type": "string"}},
                },
                "v1Collision": {
                    "type": "object",
                    "properties": {
                        "processing_status": {
                            "$ref": "#/definitions/v1ProcessingStatus"
                        },
                        "scan_state": {"type": "string"},
                    },
                },
            }
        }
        report = compute_flatten_collision_report(spec, {"v1Collision"})
        assert report["summary"]["total_collisions"] >= 1
        collisions = report["by_definition"]["v1Collision"]["collisions"]
        assert any(c["flattened_name"] == "scan_state" for c in collisions)

    def test_load_spec_prefers_local_path(self, tmp_path: Path) -> None:
        path = tmp_path / "openapi.json"
        path.write_text(
            '{"definitions":{"v1Local":{"type":"object"}}}', encoding="utf-8"
        )
        loaded = load_spec(path=path, url=None)
        assert "v1Local" in loaded["definitions"]

    def test_compute_model_consistency_diff_inheritance_aware_excludes_shared(
        self,
    ) -> None:
        sdk_models = {
            "BaseResource": ["uuid", "meta", "context"],
            "BaseSpec": ["notification"],
            "Project": ["uuid", "meta", "context", "spec.notification", "spec.custom"],
        }
        spec_fields = {"v1Project": ["uuid", "meta", "context", "spec"]}
        diff = compute_model_consistency_diff(
            sdk_models, spec_fields, inheritance_aware=True
        )
        project_extra = diff["by_resource"]["Project"]["extra_in_sdk"]
        assert "spec.custom" in project_extra
        assert "uuid" not in project_extra


class TestGreenfieldSdkPaths:
    """SDK models use greenfield paths (context, processing_status, index_data).

    After the greenfield refactor, Finding/FindingLog/ScanResult expose .context,
    Project exposes .processing_status, and ProjectMeta exposes .index_data;
    enumerate_sdk_models_flat_paths() should list those paths (no prefixed names).
    """

    def test_finding_has_context_path_not_finding_context(self) -> None:
        """Finding model paths include 'context', not 'finding_context'."""
        paths = enumerate_sdk_models_flat_paths()
        assert "Finding" in paths
        finding_paths = paths["Finding"]
        assert "context" in finding_paths
        assert "finding_context" not in finding_paths

    def test_finding_log_has_context_path_not_finding_log_context(self) -> None:
        """FindingLog model paths include 'context', not 'finding_log_context'."""
        paths = enumerate_sdk_models_flat_paths()
        assert "FindingLog" in paths
        fl_paths = paths["FindingLog"]
        assert "context" in fl_paths
        assert "finding_log_context" not in fl_paths

    def test_scan_result_has_context_path_not_scan_result_context(self) -> None:
        """ScanResult model paths include 'context', not 'scan_result_context'."""
        paths = enumerate_sdk_models_flat_paths()
        assert "ScanResult" in paths
        sr_paths = paths["ScanResult"]
        assert "context" in sr_paths
        assert "scan_result_context" not in sr_paths

    def test_project_has_processing_status_path_not_project_processing_status(
        self,
    ) -> None:
        """Paths include 'processing_status', not 'project_processing_status'."""
        paths = enumerate_sdk_models_flat_paths()
        assert "Project" in paths
        proj_paths = paths["Project"]
        assert "processing_status" in proj_paths
        assert "project_processing_status" not in proj_paths

    def test_shared_sdk_paths_include_context_and_processing_status(self) -> None:
        """Shared paths include context and processing_status (no alias map needed)."""
        shared = get_shared_sdk_paths()
        assert "context" in shared
        assert "processing_status" in shared
