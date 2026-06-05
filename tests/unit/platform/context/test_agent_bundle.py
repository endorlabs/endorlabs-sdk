"""Tests for shipped agent bundle."""

from __future__ import annotations

import json

import endorlabs
from endorlabs.agent_bundle import (
    agent_bundle_dir,
    agent_index_path,
    agent_manifest,
    agent_manifest_path,
)


def test_agent_bundle_dir_exists() -> None:
    bundle_dir = agent_bundle_dir()
    assert bundle_dir.is_dir()
    assert (bundle_dir / "INDEX.md").is_file()
    assert (bundle_dir / "MANIFEST.json").is_file()


def test_agent_index_path() -> None:
    assert agent_index_path() == agent_bundle_dir() / "INDEX.md"
    assert agent_index_path().is_file()


def test_agent_manifest_has_sixteen_skills() -> None:
    manifest = agent_manifest()
    assert manifest["schema_version"] == 1
    assert manifest["index"] == "INDEX.md"
    assert len(manifest["contracts"]) >= 5
    assert len(manifest["skills"]) == 16
    assert any(entry["id"] == "retrieve-scan-results" for entry in manifest["skills"])


def test_agent_manifest_path_matches_file() -> None:
    path = agent_manifest_path()
    assert path.is_file()
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["schema_version"] == agent_manifest()["schema_version"]


def test_contracts_shipped() -> None:
    bundle_dir = agent_bundle_dir()
    for name in (
        "canonical-naming.md",
        "namespace-scoping.md",
        "list-parameters.md",
        "dependency-metadata.md",
        "errors-and-auth.md",
    ):
        assert (bundle_dir / "contracts" / name).is_file()


def test_top_level_agent_bundle_helpers() -> None:
    assert endorlabs.agent_bundle_dir().is_dir()
    assert endorlabs.agent_index_path().name == "INDEX.md"
    assert "skills" in endorlabs.agent_manifest()


def test_workflows_index_shipped() -> None:
    workflows_dir = agent_bundle_dir() / "workflows"
    assert (workflows_dir / "index.md").is_file()
    assert (workflows_dir / "entries.json").is_file()


def test_agent_manifest_skill_descriptions_populated() -> None:
    manifest = agent_manifest()
    described = [entry for entry in manifest["skills"] if entry.get("description")]
    assert len(described) >= 14
    retrieve = next(
        entry for entry in manifest["skills"] if entry["id"] == "retrieve-scan-results"
    )
    assert "scan results" in retrieve["description"].lower()
