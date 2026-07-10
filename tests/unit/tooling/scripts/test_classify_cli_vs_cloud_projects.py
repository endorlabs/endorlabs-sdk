"""Unit tests for CLI vs Cloud project classification helpers."""

from __future__ import annotations

import sys
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from types import ModuleType
from unittest.mock import MagicMock


def _load_module() -> ModuleType:
    repo_root = Path(__file__).resolve().parents[4]
    script_path = (
        repo_root
        / "agent-knowledge"
        / "workflow-reports"
        / "endor-cli-vs-cloud-projects"
        / "scripts"
        / "classify_cli_vs_cloud_projects.py"
    )
    assert script_path.is_file(), script_path
    spec = spec_from_file_location("classify_cli_vs_cloud_projects", script_path)
    assert spec is not None
    assert spec.loader is not None
    module = module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _mock_client() -> MagicMock:
    client = MagicMock()
    project = MagicMock()
    project.is_app.side_effect = lambda row: bool(
        (row.get("spec") or {}).get("git", {}).get("external_installation_id")
    )
    project.is_cli.side_effect = lambda row: not project.is_app(row)
    client.Project = project
    return client


def test_project_source_cloud_and_cli() -> None:
    from endorlabs.workflows.projects.inventory import registration_source_label

    client = _mock_client()

    cloud = {"spec": {"git": {"external_installation_id": "123"}}}
    cli = {"spec": {"git": {}}}

    assert registration_source_label(client, cloud) == "Cloud Scan"
    assert registration_source_label(client, cli) == "CLI"


def test_installation_name_prefers_external_name() -> None:
    from endorlabs.workflows.projects.inventory import installation_display_name

    row = {
        "meta": {"name": "Installation - tenant"},
        "spec": {
            "external_name": "Acme GitHub Org",
            "login": "acme",
        },
    }

    assert installation_display_name(row) == "Acme GitHub Org"


def test_installation_name_includes_login_for_disambiguation() -> None:
    from endorlabs.workflows.projects.inventory import installation_display_name

    row = {
        "meta": {"name": "Installation - tenant"},
        "spec": {"login": "dev.azure.com/org"},
    }

    assert installation_display_name(row) == "Installation - tenant (dev.azure.com/org)"


def test_row_to_csv_resolves_installation_name() -> None:
    module = _load_module()
    client = _mock_client()

    project = {
        "meta": {"name": "github.com/org/repo"},
        "tenant_meta": {"namespace": "tenant.team"},
        "uuid": "proj-1",
        "spec": {"git": {"external_installation_id": "140464674"}},
    }
    lookup = {
        "140464674": {
            "meta": {"name": "GitHub Endor Pro App - tenant.team"},
            "spec": {"login": "team"},
        }
    }

    row = module.row_to_csv(client, project, lookup, scan_execution="Cloud Scan")

    assert row["source"] == "Cloud Scan"
    assert row["latest scan execution"] == "Cloud Scan"
    assert row["mixed mode"] == "false"
    assert row["external_installation_id"] == "140464674"
    assert row["installation name"] == "GitHub Endor Pro App - tenant.team (team)"


def test_row_to_csv_mixed_mode_when_registration_differs_from_scan() -> None:
    module = _load_module()
    client = _mock_client()

    project = {
        "meta": {"name": "github.com/org/repo"},
        "tenant_meta": {"namespace": "tenant.team"},
        "uuid": "proj-1",
        "spec": {"git": {"external_installation_id": "140464674"}},
    }

    row = module.row_to_csv(client, project, {}, scan_execution="CLI")

    assert row["source"] == "Cloud Scan"
    assert row["latest scan execution"] == "CLI"
    assert row["mixed mode"] == "true"
