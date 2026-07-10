"""Tests for shipped agent knowledge package."""

from __future__ import annotations

import json
from pathlib import Path

import endorlabs
from devtools.codegen.sync_agent_knowledge import MANIFEST_SCHEMA_VERSION
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


def test_agent_knowledge_manifest_structure() -> None:
    manifest = agent_knowledge_manifest()
    package_dir = agent_knowledge_dir()

    assert manifest["schema_version"] == MANIFEST_SCHEMA_VERSION
    assert manifest["index"] == "INDEX.md"
    assert manifest["contracts"]
    assert manifest["rules"]
    assert manifest["skills"]

    rule_ids = [entry["id"] for entry in manifest["rules"]]
    assert len(rule_ids) == len(set(rule_ids))
    bootstrap_ids = manifest["bootstrap"]["rule_ids"]
    assert bootstrap_ids == sorted(bootstrap_ids)
    assert "endor-changelog" not in rule_ids
    assert "endor-changelog" not in bootstrap_ids
    assert set(bootstrap_ids).issubset(set(rule_ids))
    contract_ids = [entry["id"] for entry in manifest["contracts"]]
    bootstrap_contract_ids = manifest["bootstrap"].get("contract_ids", [])
    assert set(bootstrap_contract_ids).issubset(set(contract_ids))
    assert "resource-discovery" in bootstrap_contract_ids
    for entry in manifest["rules"]:
        assert (package_dir / entry["path"]).is_file()

    skill_ids = [entry["id"] for entry in manifest["skills"]]
    assert len(skill_ids) == len(set(skill_ids))
    assert "endor-compile-dependency-graph" not in skill_ids
    for entry in manifest["skills"]:
        assert entry["id"].startswith("endor-")
        assert entry["path"].startswith("skills/")
        assert entry.get("description", "").strip()
        assert (package_dir / entry["path"]).is_file()


def test_workflow_catalog_estate_workspace_not_agent_visible() -> None:
    manifest = agent_knowledge_manifest()
    row = next(e for e in manifest["workflows"] if e["id"] == "estate-workspace")
    assert row["skill"] is None
    assert row["agent_visible"] is False
    assert row["cli"] == "endor-estate"
    assert "endor-estate-workspace" not in {entry["id"] for entry in manifest["skills"]}

    entries = json.loads(
        (agent_knowledge_dir() / "workflows" / "entries.json").read_text(
            encoding="utf-8"
        )
    )
    assert not any(entry["id"] == "estate-workspace" for entry in entries)


def test_agent_knowledge_manifest_path_matches_file() -> None:
    path = agent_knowledge_manifest_path()
    assert path.is_file()
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["schema_version"] == agent_knowledge_manifest()["schema_version"]


def test_contracts_and_rules_shipped() -> None:
    """Shipped rules/contracts on disk match MANIFEST.json (no drift either way)."""
    manifest = agent_knowledge_manifest()
    package_dir = agent_knowledge_dir()

    shipped_rules = {path.name for path in (package_dir / "rules").glob("*.md")}
    manifest_rules = {Path(entry["path"]).name for entry in manifest["rules"]}
    assert shipped_rules == manifest_rules

    shipped_contracts = {path.name for path in (package_dir / "contracts").glob("*.md")}
    manifest_contracts = {Path(entry["path"]).name for entry in manifest["contracts"]}
    assert shipped_contracts == manifest_contracts


def test_top_level_agent_knowledge_helpers() -> None:
    assert endorlabs.agent_knowledge_dir().is_dir()
    assert endorlabs.agent_knowledge_index_path().name == "INDEX.md"
    assert "skills" in endorlabs.agent_knowledge_manifest()


def test_workflows_index_shipped() -> None:
    workflows_dir = agent_knowledge_dir() / "workflows"
    assert (workflows_dir / "index.md").is_file()
    assert (workflows_dir / "entries.json").is_file()


def test_agent_knowledge_manifest_anchor_skill_description() -> None:
    manifest = agent_knowledge_manifest()
    retrieve = next(
        entry
        for entry in manifest["skills"]
        if entry["id"] == "endor-retrieve-scan-results"
    )
    assert "scan results" in retrieve["description"].lower()
