"""Unit tests for agent knowledge bootstrap metadata and portable content."""

from __future__ import annotations

import importlib
import json
from pathlib import Path

import pytest

from devtools.agent_knowledge_catalog import (
    BOOTSTRAP_EXCLUDE_RULE_IDS,
    build_bootstrap_manifest_block,
    build_contract_manifest_entries,
    build_rules_manifest_entries,
)
from devtools.sync_agent_knowledge import (
    MANIFEST_SCHEMA_VERSION,
    build_cursor_rule_contents,
)

REPO_ROOT = Path(__file__).resolve().parents[4]
AGENT_ROOT = REPO_ROOT / "agent-knowledge"
BUNDLE_ROOT = REPO_ROOT / "src" / "endorlabs" / "agent_knowledge"


def test_rules_manifest_entries() -> None:
    rules_dir = AGENT_ROOT / "rules"
    rules = build_rules_manifest_entries(rules_dir)
    assert len(rules) == len(list(rules_dir.glob("*.md")))
    ids = {entry["id"] for entry in rules}
    assert "endor-workflow-composition" in ids
    assert "endor-changelog" in ids
    assert all(entry["path"].startswith("rules/") for entry in rules)
    assert all("summary" in entry for entry in rules)


def test_contract_manifest_entries_reference_only() -> None:
    contracts = build_contract_manifest_entries(AGENT_ROOT / "contracts")
    assert contracts
    ids = {entry["id"] for entry in contracts}
    assert "list-parameters" in ids
    assert "endor-workflow-composition" not in ids
    assert all(entry["path"].startswith("contracts/") for entry in contracts)
    assert all("tier" not in entry for entry in contracts)


def test_manifest_bootstrap_block_matches_rules() -> None:
    rules = build_rules_manifest_entries(AGENT_ROOT / "rules")
    bootstrap = build_bootstrap_manifest_block(rules)
    expected_ids = sorted(
        entry["id"] for entry in rules if entry["id"] not in BOOTSTRAP_EXCLUDE_RULE_IDS
    )
    assert bootstrap == {"index": "INDEX.md", "rule_ids": expected_ids}
    assert "endor-workflow-composition" in bootstrap["rule_ids"]
    assert "endor-changelog" not in bootstrap["rule_ids"]


def test_shipped_manifest_schema_v2() -> None:
    manifest = json.loads((BUNDLE_ROOT / "MANIFEST.json").read_text(encoding="utf-8"))
    assert manifest["schema_version"] == MANIFEST_SCHEMA_VERSION
    assert manifest["bootstrap"]["rule_ids"]
    assert manifest["rules"]
    assert manifest["contracts"]
    rule_ids = {entry["id"] for entry in manifest["rules"]}
    contract_ids = {entry["id"] for entry in manifest["contracts"]}
    assert rule_ids.isdisjoint(contract_ids)


def test_agent_knowledge_bootstrap_paths() -> None:
    from endorlabs.agent_knowledge import (
        agent_knowledge_bootstrap_paths,
        agent_knowledge_index_path,
        agent_knowledge_rule_ids,
    )

    ids = agent_knowledge_rule_ids()
    assert "endor-namespace-scoping" in ids
    paths = agent_knowledge_bootstrap_paths()
    assert agent_knowledge_index_path() in paths
    assert all(path.is_file() for path in paths)
    assert all(
        "rules" in path.as_posix()
        for path in paths
        if path != agent_knowledge_index_path()
    )


def test_library_entrypoints_importable() -> None:
    manifest = json.loads((BUNDLE_ROOT / "MANIFEST.json").read_text(encoding="utf-8"))
    errors: list[str] = []
    for row in manifest.get("workflows", []):
        for target in row.get("library_entrypoints") or []:
            module_name, attr_name = target.rsplit(".", 1)
            try:
                module = importlib.import_module(module_name)
            except ImportError as exc:
                errors.append(f"{target}: import failed ({exc})")
                continue
            if not hasattr(module, attr_name):
                errors.append(f"{target}: missing attribute {attr_name!r}")
    if errors:
        pytest.fail("\n".join(errors))


def test_emit_cursor_rules_footgun_rules_always_apply() -> None:
    contents = build_cursor_rule_contents()
    for rule_id in ("endor-namespace-scoping", "endor-list-query-performance"):
        mdc = contents[rule_id]
        assert "alwaysApply: true" in mdc
        assert "globs:" not in mdc
        assert "x-endor-generated: true" in mdc


def test_emit_cursor_rules_maintainer_rules_glob_scoped() -> None:
    contents = build_cursor_rule_contents()
    mdc = contents["endor-workflow-composition"]
    assert "alwaysApply: false" in mdc
    assert "globs:" in mdc
    assert "src/endorlabs/**" in mdc
    assert "**/*.py" in mdc


def test_emit_cursor_rules_list_query_performance_content() -> None:
    contents = build_cursor_rule_contents()
    mdc = contents["endor-list-query-performance"]
    assert "alwaysApply: true" in mdc
    assert (
        "x-endor-source: agent-knowledge/rules/endor-list-query-performance.md" in mdc
    )
    assert "x-endor-source-sha256: " in mdc
    assert "# List query performance" in mdc
    assert "Do not set `page_size`" in mdc


def test_portable_examples_rule_has_summary() -> None:
    rules = build_rules_manifest_entries(AGENT_ROOT / "rules")
    portable = next(
        entry for entry in rules if entry["id"] == "endor-portable-examples"
    )
    assert portable.get("summary")
