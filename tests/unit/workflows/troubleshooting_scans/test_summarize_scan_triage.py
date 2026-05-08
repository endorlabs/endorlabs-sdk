"""Tests for summarize_scan_triage helper branches and main flow."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from endorlabs.workflows.troubleshooting_scans import summarize_scan_triage as sst


def test_load_json_rejects_non_object(tmp_path: Path) -> None:
    artifact = tmp_path / "bad.json"
    artifact.write_text('["not-object"]', encoding="utf-8")
    with pytest.raises(TypeError, match="not a JSON object"):
        sst._load_json(str(artifact))


def test_error_entries_filters_error_levels() -> None:
    artifact = {
        "messages": [
            {"level": "LOG_LEVEL_INFO", "json_payload": {"level": "info"}},
            {"level": "LOG_LEVEL_ERROR", "json_payload": {"msg": "boom"}},
            {
                "level": "LOG_LEVEL_INFO",
                "json_payload": {"level": "error", "msg": "boom2"},
            },
        ]
    }
    errors = sst._error_entries(artifact)
    assert len(errors) == 2


def test_signature_tags_detects_known_patterns() -> None:
    scan_raw = {
        "spec": {
            "status": "STATUS_PARTIAL_SUCCESS",
            "provisioning_result": {
                "error": "hash sum mismatch while build did not complete successfully bazel"
            },
        }
    }
    logs_artifact = {
        "messages": [
            {
                "json_payload": {
                    "msg": "unable to generate manifest path after gradle init"
                }
            }
        ]
    }
    tags = sst._signature_tags(scan_raw, logs_artifact)
    assert "partial_scan_coverage" in tags
    assert "repo_index_hash_mismatch" in tags
    assert "manifest_or_tooling_discovery_issue" in tags
    assert "manifest_generation_failure" in tags
    assert "build_orchestration_failure" in tags


def test_main_writes_summary_and_evidence(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    results = {
        "project_uuid": "p1",
        "scan_results": [
            {
                "uuid": "scan-1",
                "spec": {
                    "status": "STATUS_SUCCESS",
                    "type": "TYPE_ALL_SCANS",
                    "provisioning_result": {"exit_code": 0},
                    "stats": {"scan_success": 1},
                },
            }
        ],
        "scan_results_summary": [{"uuid": "scan-1", "namespace": "tenant.ns"}],
    }
    logs = {
        "project_uuid": "p1",
        "namespace": "tenant.ns",
        "scan_result_uuid": "scan-1",
        "messages": [
            {
                "level": "LOG_LEVEL_ERROR",
                "json_payload": {"msg": "dependency-scanning-error"},
            }
        ],
    }
    search = {"projects": [{"meta": {"name": "repo-a"}}]}
    results_path = tmp_path / "results.json"
    logs_path = tmp_path / "logs.json"
    search_path = tmp_path / "search.json"
    results_path.write_text(json.dumps(results), encoding="utf-8")
    logs_path.write_text(json.dumps(logs), encoding="utf-8")
    search_path.write_text(json.dumps(search), encoding="utf-8")

    with (
        patch(
            "endorlabs.workflows.troubleshooting_scans.summarize_scan_triage.root_tenant",
            return_value="tenant",
        ),
        patch(
            "endorlabs.workflows.troubleshooting_scans.summarize_scan_triage.write_text",
            return_value=tmp_path / "summary.md",
        ),
        patch(
            "endorlabs.workflows.troubleshooting_scans.summarize_scan_triage.write_json",
            return_value=tmp_path / "evidence.json",
        ),
        patch(
            "endorlabs.workflows.troubleshooting_scans.summarize_scan_triage._build_parser",
            return_value=SimpleNamespace(
                parse_args=lambda: SimpleNamespace(
                    tenant="tenant.ns",
                    scan_results_artifact=str(results_path),
                    scan_logs_artifact=str(logs_path),
                    project_search_artifact=str(search_path),
                    max_errors=5,
                    output_dir=str(tmp_path),
                    timestamped=False,
                )
            ),
        ),
    ):
        code = sst.main()

    assert code == 0
    payload = json.loads(capsys.readouterr().out.strip())
    assert payload["summary_markdown"].endswith("summary.md")
    assert payload["summary_evidence"].endswith("evidence.json")
