"""Unit tests for agent knowledge bootstrap metadata and portable content."""

from __future__ import annotations

import importlib
import json
from pathlib import Path

import pytest

from devtools.codegen.agent_knowledge_catalog import (
    BOOTSTRAP_CONTRACT_IDS,
    MAINTAINER_ONLY_RULE_IDS,
    build_bootstrap_manifest_block,
    build_contract_manifest_entries,
    build_rules_manifest_entries,
)
from devtools.codegen.sync_agent_knowledge import (
    MANIFEST_SCHEMA_VERSION,
    build_cursor_rule_contents,
)

REPO_ROOT = Path(__file__).resolve().parents[4]
AGENT_ROOT = REPO_ROOT / "agent-knowledge"
BUNDLE_ROOT = REPO_ROOT / "src" / "endorlabs" / "agent_knowledge"


def test_rules_manifest_entries() -> None:
    rules_dir = AGENT_ROOT / "rules"
    rules = build_rules_manifest_entries(rules_dir)
    assert len(rules) == len(list(rules_dir.glob("*.md"))) - len(
        MAINTAINER_ONLY_RULE_IDS
    )
    ids = {entry["id"] for entry in rules}
    assert "endor-workflow-composition" in ids
    assert "endor-changelog" not in ids
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
    expected_ids = sorted(entry["id"] for entry in rules)
    assert bootstrap == {
        "index": "INDEX.md",
        "rule_ids": expected_ids,
        "contract_ids": list(BOOTSTRAP_CONTRACT_IDS),
    }
    assert "endor-workflow-composition" in bootstrap["rule_ids"]
    assert "endor-changelog" not in bootstrap["rule_ids"]
    assert "resource-discovery" in bootstrap["contract_ids"]


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
        agent_knowledge_contract_ids,
        agent_knowledge_index_path,
        agent_knowledge_rule_ids,
    )

    ids = agent_knowledge_rule_ids()
    assert "endor-namespace-scoping" in ids
    contract_ids = agent_knowledge_contract_ids()
    assert "resource-discovery" in contract_ids
    paths = agent_knowledge_bootstrap_paths()
    assert agent_knowledge_index_path() in paths
    assert all(path.is_file() for path in paths)
    rule_paths = [
        path
        for path in paths
        if path != agent_knowledge_index_path() and "rules" in path.as_posix()
    ]
    contract_paths = [path for path in paths if "contracts" in path.as_posix()]
    assert rule_paths
    assert contract_paths
    assert any("resource-discovery" in path.name for path in contract_paths)


def _resolve_library_entrypoint(target: str) -> str | None:
    """Return an error message, or None when the entrypoint resolves."""
    if target.startswith("endorlabs.Client."):
        parts = target.split(".")
        if len(parts) != 4:
            return f"expected endorlabs.Client.<Resource>.<method>, got {target!r}"
        _, _, resource, method = parts
        facade_mod = importlib.import_module("endorlabs.facade")
        facade_cls = getattr(facade_mod, f"{resource}Facade", None)
        if facade_cls is None:
            return f"no facade class {resource}Facade"
        if not hasattr(facade_cls, method):
            return f"missing method {method!r} on {resource}Facade"
        return None

    module_name, attr_name = target.rsplit(".", 1)
    try:
        module = importlib.import_module(module_name)
    except ImportError as exc:
        return f"import failed ({exc})"
    if not hasattr(module, attr_name):
        return f"missing attribute {attr_name!r}"
    return None


def test_library_entrypoints_importable() -> None:
    manifest = json.loads((BUNDLE_ROOT / "MANIFEST.json").read_text(encoding="utf-8"))
    errors: list[str] = []
    for row in manifest.get("workflows", []):
        for target in row.get("library_entrypoints") or []:
            err = _resolve_library_entrypoint(target)
            if err is not None:
                errors.append(f"{target}: {err}")
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
    rule_id = "endor-list-query-performance"
    mdc = contents[rule_id]
    assert rule_id in mdc
    assert "alwaysApply: true" in mdc
    assert "globs:" not in mdc
    assert "x-endor-generated: true" in mdc
    assert f"x-endor-source: agent-knowledge/rules/{rule_id}.md" in mdc
    assert "x-endor-source-sha256: " in mdc
    assert mdc.startswith("---\n")
    assert "\n---\n" in mdc


def test_portable_examples_rule_has_summary() -> None:
    rules = build_rules_manifest_entries(AGENT_ROOT / "rules")
    portable = next(
        entry for entry in rules if entry["id"] == "endor-portable-examples"
    )
    assert portable.get("summary")
