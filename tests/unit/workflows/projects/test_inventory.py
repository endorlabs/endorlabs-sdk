"""Tests for project inventory scan-execution helpers."""

from __future__ import annotations

from unittest.mock import MagicMock

from endorlabs.workflows.projects.inventory import (
    extract_run_by_system,
    is_huggingface_installation,
    is_mixed_registration_execution,
    scan_execution_label,
)


def test_extract_run_by_system_from_dict() -> None:
    row = {"spec": {"environment": {"config": {"RunBySystem": True}}}}
    assert extract_run_by_system(row) is True
    row["spec"]["environment"]["config"]["RunBySystem"] = False
    assert extract_run_by_system(row) is False


def test_scan_execution_label_mapping() -> None:
    assert scan_execution_label(True) == "Cloud Scan"
    assert scan_execution_label(False) == "CLI"
    assert scan_execution_label(None) == "unknown"


def test_is_mixed_registration_execution() -> None:
    assert is_mixed_registration_execution("Cloud Scan", "CLI") is True
    assert is_mixed_registration_execution("CLI", "CLI") is False
    assert is_mixed_registration_execution("Cloud Scan", "unknown") is False


def test_is_huggingface_installation() -> None:
    assert is_huggingface_installation(
        {"spec": {"platform_type": "PLATFORM_SOURCE_HUGGING_FACE"}}
    )
    assert is_huggingface_installation(
        {
            "spec": {
                "huggingface_config": {"host_url": "https://example.com/example-org"}
            }
        }
    )
    assert not is_huggingface_installation(
        {"spec": {"platform_type": "PLATFORM_SOURCE_GITHUB"}}
    )
    assert not is_huggingface_installation(None)


def test_latest_scan_execution_label_uses_list_by_project() -> None:
    from endorlabs.workflows.projects.inventory import latest_scan_execution_label

    client = MagicMock()
    client.ScanResult.list_by_project.return_value = [
        {"spec": {"environment": {"config": {"RunBySystem": False}}}}
    ]
    project = {
        "uuid": "p-1",
        "tenant_meta": {"namespace": "tenant.team"},
    }

    assert latest_scan_execution_label(client, project) == "CLI"
    client.ScanResult.list_by_project.assert_called_once()


def test_latest_scan_execution_label_uses_list_by_project_model() -> None:
    from endorlabs.workflows.projects.inventory import latest_scan_execution_label

    client = MagicMock()
    client.ScanResult.list_by_project.return_value = [
        {"spec": {"environment": {"config": {"RunBySystem": False}}}}
    ]
    project = MagicMock()
    project.uuid = "p-1"

    assert latest_scan_execution_label(client, project) == "CLI"
    client.ScanResult.list_by_project.assert_called_once()
