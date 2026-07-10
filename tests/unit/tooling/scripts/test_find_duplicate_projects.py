"""Unit tests for duplicate project detection helpers."""

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
        / "endor-duplicate-projects"
        / "scripts"
        / "find_duplicate_projects.py"
    )
    assert script_path.is_file(), script_path
    spec = spec_from_file_location("find_duplicate_projects", script_path)
    assert spec is not None
    assert spec.loader is not None
    module = module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _mock_is_sbom(row: dict) -> bool:
    return (row.get("spec") or {}).get("sbom") is not None


def test_canonical_name_strips_mirror_tokens_when_configured() -> None:
    module = _load_module()
    tokens = frozenset({"mirror", "shadow", "clone"})

    assert (
        module.canonical_name("github.com/org/repo-mirror", strip_tokens=tokens)
        == "github.com/org/repo"
    )
    assert (
        module.canonical_name("github.com/org/SHADOW-clone", strip_tokens=tokens)
        == "github.com/org"
    )


def test_canonical_name_exact_only_without_tokens() -> None:
    module = _load_module()

    assert (
        module.canonical_name("github.com/org/repo-mirror", strip_tokens=None)
        == "github.com/org/repo-mirror"
    )


def test_is_sbom_project_excluded_from_grouping() -> None:
    module = _load_module()

    sbom = {"uuid": "sbom-1", "spec": {"sbom": {"format": "cyclonedx"}}}
    regular = {
        "uuid": "p-1",
        "meta": {"name": "github.com/org/repo"},
        "tenant_meta": {"namespace": "tenant.a"},
        "spec": {"git": {}},
    }
    duplicate = {
        "uuid": "p-2",
        "meta": {"name": "github.com/org/repo"},
        "tenant_meta": {"namespace": "tenant.b"},
        "spec": {"git": {}},
    }

    clusters = module.find_duplicate_groups(
        [sbom, regular, duplicate],
        is_sbom=_mock_is_sbom,
        strip_tokens=None,
    )
    uuids = {row["uuid"] for cluster in clusters for row in cluster}

    assert "sbom-1" not in uuids
    assert uuids == {"p-1", "p-2"}


def test_find_duplicate_groups_exact_name_across_namespaces() -> None:
    module = _load_module()
    client = MagicMock()
    project = MagicMock()
    project.is_app.side_effect = lambda row: bool(
        (row.get("spec") or {}).get("git", {}).get("external_installation_id")
    )
    client.Project = project

    projects = [
        {
            "uuid": "a",
            "meta": {"name": "github.com/org/repo"},
            "tenant_meta": {"namespace": "tenant.team-a"},
            "spec": {"git": {}},
        },
        {
            "uuid": "b",
            "meta": {"name": "github.com/org/repo"},
            "tenant_meta": {"namespace": "tenant.team-b"},
            "spec": {"git": {"external_installation_id": "99"}},
        },
    ]

    clusters = module.find_duplicate_groups(
        projects,
        is_sbom=_mock_is_sbom,
        strip_tokens=None,
    )

    assert len(clusters) == 1
    assert {row["uuid"] for row in clusters[0]} == {"a", "b"}
    assert (
        module.row_to_csv(client, projects[1], scan_execution="CLI")["source"]
        == "Cloud Scan"
    )
    assert (
        module.row_to_csv(client, projects[1], scan_execution="CLI")[
            "latest scan execution"
        ]
        == "CLI"
    )
