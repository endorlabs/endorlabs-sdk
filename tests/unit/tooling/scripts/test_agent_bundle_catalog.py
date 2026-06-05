"""Unit tests for agent-skills schema validation and catalog generation."""

from __future__ import annotations

from pathlib import Path

import pytest

from devtools.agent_bundle_catalog import (
    build_workflow_catalog,
    load_supplemental_workflows,
    normalize_skill_for_bundle,
    parse_skill_md,
    portable_frontmatter,
    validate_skill,
    validate_workflow_cli_entries,
)

REPO_ROOT = Path(__file__).resolve().parents[4]
AGENT_SKILLS = REPO_ROOT / "agent-skills"
SCHEMA_DIR = AGENT_SKILLS / "schema"
PYPROJECT = REPO_ROOT / "pyproject.toml"


def test_portable_frontmatter_strips_endorlabs_extension() -> None:
    fm = {
        "name": "demo-skill",
        "description": "Does things when asked.",
        "endorlabs": {"catalog": {"workflow_id": "demo", "module": "mod"}},
        "disable-model-invocation": True,
    }
    portable = portable_frontmatter(fm)
    assert portable == {
        "name": "demo-skill",
        "description": "Does things when asked.",
        "disable-model-invocation": True,
    }
    assert "endorlabs" not in portable


def test_normalize_skill_for_bundle_removes_endorlabs_key(tmp_path: Path) -> None:
    skill_dir = tmp_path / "demo-skill"
    skill_dir.mkdir()
    skill_md = skill_dir / "SKILL.md"
    skill_md.write_text(
        "---\n"
        "name: demo-skill\n"
        "description: Does things when asked.\n"
        "endorlabs:\n"
        "  catalog:\n"
        "    workflow_id: demo\n"
        "    module: endorlabs.demo\n"
        "---\n\n"
        "# Body\n",
        encoding="utf-8",
    )
    parsed = parse_skill_md(skill_md)
    normalized = normalize_skill_for_bundle(parsed)
    assert "endorlabs:" not in normalized
    assert "name: demo-skill" in normalized
    assert "# Body" in normalized


def test_validate_skill_rejects_name_directory_mismatch(tmp_path: Path) -> None:
    skill_dir = tmp_path / "right-name"
    skill_dir.mkdir()
    skill_md = skill_dir / "SKILL.md"
    skill_md.write_text(
        "---\nname: wrong-name\ndescription: Valid summary.\n---\n",
        encoding="utf-8",
    )
    parsed = parse_skill_md(skill_md)
    errors = validate_skill(parsed, skill_schema_path=SCHEMA_DIR / "skill.schema.json")
    assert any("must match directory" in err for err in errors)


def test_build_workflow_catalog_merges_yaml_and_skill_rows() -> None:
    supplemental = load_supplemental_workflows(
        AGENT_SKILLS / "workflows.yaml",
        workflows_schema_path=SCHEMA_DIR / "workflows.schema.json",
    )
    catalog_rows = [
        (
            "project-agent-context",
            {
                "workflow_id": "agent-context",
                "cli": "endor-agent-context",
                "module": "endorlabs.workflows.agent_context.cli",
                "default_output": ".endorlabs-context/workspace/projects/<uuid>/",
                "agent_visible": True,
            },
        )
    ]
    workflows = build_workflow_catalog(supplemental, catalog_rows)
    ids = {row["id"] for row in workflows}
    assert "context-bootstrap" in ids
    assert "agent-context" in ids
    agent_row = next(row for row in workflows if row["id"] == "agent-context")
    assert agent_row["skill"] == "project-agent-context"
    assert agent_row["cli"] == "endor-agent-context"


def test_validate_workflow_cli_entries_matches_pyproject() -> None:
    workflows = [
        {
            "id": "context-bootstrap",
            "cli": "endor-context",
            "module": "endorlabs.context.cli",
            "skill": None,
            "default_output": ".endorlabs-context/",
            "agent_visible": True,
        }
    ]
    errors = validate_workflow_cli_entries(workflows, pyproject_path=PYPROJECT)
    assert errors == []


def test_validate_workflow_cli_entries_reports_module_mismatch() -> None:
    workflows = [
        {
            "id": "bad-row",
            "cli": "endor-context",
            "module": "endorlabs.wrong.module",
            "skill": None,
            "default_output": None,
            "agent_visible": True,
        }
    ]
    errors = validate_workflow_cli_entries(workflows, pyproject_path=PYPROJECT)
    assert len(errors) == 1
    assert "does not match" in errors[0]


@pytest.mark.parametrize(
    "skill_name",
    sorted(
        p.name
        for p in AGENT_SKILLS.iterdir()
        if p.is_dir() and (p / "SKILL.md").is_file() and p.name not in {"schema"}
    ),
)
def test_authoring_skills_validate_against_schema(skill_name: str) -> None:
    skill_md = AGENT_SKILLS / skill_name / "SKILL.md"
    parsed = parse_skill_md(skill_md)
    errors = validate_skill(parsed, skill_schema_path=SCHEMA_DIR / "skill.schema.json")
    assert errors == [], "\n".join(errors)


def test_shipped_skills_have_no_endorlabs_extension() -> None:
    bundle_skills = REPO_ROOT / "src" / "endorlabs" / "agent_bundle" / "skills"
    for skill_md in bundle_skills.glob("*/SKILL.md"):
        parsed = parse_skill_md(skill_md)
        assert "endorlabs" not in parsed.frontmatter, skill_md
