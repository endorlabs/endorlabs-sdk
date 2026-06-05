"""Unit tests for agent bundle sync helpers."""

from __future__ import annotations

from pathlib import Path

from devtools.agent_knowledge_catalog import parse_skill_md, portable_frontmatter


def test_parse_skill_frontmatter_inline_description(tmp_path: Path) -> None:
    skill_md = tmp_path / "SKILL.md"
    skill_md.write_text(
        "---\nname: inline-skill\ndescription: One line summary.\n---\n",
        encoding="utf-8",
    )
    parsed = parse_skill_md(skill_md)
    portable = portable_frontmatter(parsed.frontmatter)
    assert portable["name"] == "inline-skill"
    assert portable["description"] == "One line summary."


def test_parse_skill_frontmatter_multiline_block_scalar(tmp_path: Path) -> None:
    skill_md = tmp_path / "SKILL.md"
    skill_md.write_text(
        "---\n"
        "name: retrieve-scan-results\n"
        "description: >-\n"
        "  Query projects, scan results, and findings from the Endor Labs platform\n"
        "  using the SDK. Use when the user wants to retrieve scan results.\n"
        "---\n",
        encoding="utf-8",
    )
    parsed = parse_skill_md(skill_md)
    portable = portable_frontmatter(parsed.frontmatter)
    assert portable["name"] == "retrieve-scan-results"
    assert "Query projects" in portable["description"]
    assert portable["description"].endswith("retrieve scan results.")


def test_parse_skill_frontmatter_missing_block_returns_empty_description(
    tmp_path: Path,
) -> None:
    skill_dir = tmp_path / "no-frontmatter"
    skill_dir.mkdir()
    skill_md = skill_dir / "SKILL.md"
    skill_md.write_text("# No frontmatter\n", encoding="utf-8")
    parsed = parse_skill_md(skill_md)
    portable = portable_frontmatter(parsed.frontmatter)
    assert parsed.skill_id == "no-frontmatter"
    assert portable.get("description", "") == ""
