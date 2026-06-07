"""Tests for shipped agent knowledge package."""

from __future__ import annotations

import json

import endorlabs
from endorlabs.agent_knowledge import (
    agent_knowledge_dir,
    agent_knowledge_index_path,
    agent_knowledge_manifest,
    agent_knowledge_manifest_path,
)


def test_agent_knowledge_dir_exists() -> None:
    package_dir = agent_knowledge_dir()
    assert package_dir.is_dir()
    assert (package_dir / "INDEX.md").is_file()
    assert (package_dir / "MANIFEST.json").is_file()


def test_agent_knowledge_index_path() -> None:
    assert agent_knowledge_index_path() == agent_knowledge_dir() / "INDEX.md"
    assert agent_knowledge_index_path().is_file()


def test_agent_knowledge_manifest_has_sixteen_skills() -> None:
    manifest = agent_knowledge_manifest()
    assert manifest["schema_version"] == 2
    assert manifest["index"] == "INDEX.md"
    assert len(manifest["contracts"]) >= 4
    assert len(manifest["rules"]) == 6
    assert len(manifest["skills"]) == 16
    assert any(
        entry["id"] == "endor-retrieve-scan-results" for entry in manifest["skills"]
    )


def test_agent_knowledge_manifest_path_matches_file() -> None:
    path = agent_knowledge_manifest_path()
    assert path.is_file()
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["schema_version"] == agent_knowledge_manifest()["schema_version"]


def test_contracts_and_rules_shipped() -> None:
    package_dir = agent_knowledge_dir()
    for name in (
        "canonical-naming.md",
        "list-parameters.md",
        "dependency-metadata.md",
        "errors-and-auth.md",
    ):
        assert (package_dir / "contracts" / name).is_file()
    for name in (
        "endor-namespace-scoping.md",
        "endor-local-context.md",
        "endor-workflow-composition.md",
    ):
        assert (package_dir / "rules" / name).is_file()


def test_top_level_agent_knowledge_helpers() -> None:
    assert endorlabs.agent_knowledge_dir().is_dir()
    assert endorlabs.agent_knowledge_index_path().name == "INDEX.md"
    assert "skills" in endorlabs.agent_knowledge_manifest()


def test_workflows_index_shipped() -> None:
    workflows_dir = agent_knowledge_dir() / "workflows"
    assert (workflows_dir / "index.md").is_file()
    assert (workflows_dir / "entries.json").is_file()


def test_agent_knowledge_manifest_skill_descriptions_populated() -> None:
    manifest = agent_knowledge_manifest()
    described = [entry for entry in manifest["skills"] if entry.get("description")]
    assert len(described) >= 14
    retrieve = next(
        entry
        for entry in manifest["skills"]
        if entry["id"] == "endor-retrieve-scan-results"
    )
    assert "scan results" in retrieve["description"].lower()
