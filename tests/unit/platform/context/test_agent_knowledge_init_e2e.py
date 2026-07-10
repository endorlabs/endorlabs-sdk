"""End-to-end tests for agent bundle materialization (no live API)."""

from __future__ import annotations

import json

import endorlabs


def test_init_materializes_sdk_bundle_without_auth(tmp_path) -> None:
    status = endorlabs.init(
        output_dir=tmp_path,
        include_openapi=False,
    )
    assert status.agent_knowledge_path is not None
    assert (status.agent_knowledge_path / "INDEX.md").is_file()
    assert (
        status.agent_knowledge_path
        / "skills"
        / "endor-retrieve-scan-results"
        / "SKILL.md"
    ).is_file()
    assert status.context_json_path is not None
    assert status.context_json_path.is_file()
    payload = json.loads(status.context_json_path.read_text(encoding="utf-8"))
    assert payload.get("agent_knowledge_path") is not None
    assert str(payload["agent_knowledge_path"]).endswith("sdk")


def test_wheel_manifest_matches_materialized_skill_paths(tmp_path) -> None:
    wheel_manifest = endorlabs.agent_knowledge_manifest()
    status = endorlabs.init(
        output_dir=tmp_path,
        include_openapi=False,
    )
    assert status.agent_knowledge_path is not None
    materialized = json.loads(
        (status.agent_knowledge_path / "MANIFEST.json").read_text(encoding="utf-8")
    )
    wheel_skill = next(
        entry
        for entry in wheel_manifest["skills"]
        if entry["id"] == "endor-troubleshoot-sdk"
    )
    materialized_skill = next(
        entry
        for entry in materialized["skills"]
        if entry["id"] == "endor-troubleshoot-sdk"
    )
    assert wheel_skill["description"] == materialized_skill["description"]
    assert (status.agent_knowledge_path / wheel_skill["path"]).is_file()
