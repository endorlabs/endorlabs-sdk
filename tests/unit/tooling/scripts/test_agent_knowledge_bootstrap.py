"""Unit tests for agent bundle bootstrap metadata and portable content."""

from __future__ import annotations

import importlib
import json
from pathlib import Path

import pytest

from devtools.agent_bundle_catalog import (
    build_bootstrap_manifest_block,
    build_contract_manifest_entries,
)
from devtools.sync_agent_bundle import build_cursor_rule_contents
from devtools.verify_portable_agent_content import verify_portable_agent_content

REPO_ROOT = Path(__file__).resolve().parents[4]
AGENT_SKILLS = REPO_ROOT / "agent-skills"
BUNDLE_ROOT = REPO_ROOT / "src" / "endorlabs" / "agent_bundle"


def test_build_contract_manifest_includes_tier() -> None:
    entries = build_contract_manifest_entries(AGENT_SKILLS / "contracts")
    assert entries
    tiers = {entry["id"]: entry.get("tier") for entry in entries}
    assert tiers["workflow-composition"] == "bootstrap"
    assert tiers["list-parameters"] == "reference"
    assert "summary" in next(e for e in entries if e["id"] == "namespace-scoping")


def test_manifest_bootstrap_block_matches_tier() -> None:
    contracts = build_contract_manifest_entries(AGENT_SKILLS / "contracts")
    bootstrap = build_bootstrap_manifest_block(contracts)
    expected = sorted(
        entry["id"] for entry in contracts if entry.get("tier") == "bootstrap"
    )
    assert bootstrap == {"index": "INDEX.md", "contract_ids": expected}
    assert "workflow-composition" in bootstrap["contract_ids"]


def test_agent_bootstrap_paths() -> None:
    from endorlabs.agent_bundle import (
        agent_bootstrap_contract_ids,
        agent_bootstrap_paths,
        agent_index_path,
    )

    ids = agent_bootstrap_contract_ids()
    assert "namespace-scoping" in ids
    paths = agent_bootstrap_paths()
    assert agent_index_path() in paths
    assert all(path.is_file() for path in paths)


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


def test_emit_cursor_rules_content() -> None:
    contents = build_cursor_rule_contents()
    mdc = contents["list-query-performance"]
    assert "alwaysApply: true" in mdc
    assert "# List query performance" in mdc
    assert "Do not set `page_size`" in mdc


def test_verify_portable_agent_content_passes() -> None:
    errors = verify_portable_agent_content(AGENT_SKILLS)
    assert errors == [], "\n".join(errors)


def test_verify_portable_agent_content_catches_banned_tenant(tmp_path: Path) -> None:
    bad = tmp_path / "bad-skill.md"
    bad.write_text("tenant: endor-solutions-tgowan\n", encoding="utf-8")
    errors = verify_portable_agent_content(tmp_path)
    assert any("banned tenant" in err for err in errors)
