"""Parse, validate, and build agent bundle catalog data from agent-skills/."""

# ruff: noqa: D101, D103, PERF401, TRY004

from __future__ import annotations

import re
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator

AGENT_SKILLS_DIRNAME = "agent-skills"
SKILL_NAME_PATTERN = re.compile(r"^[a-z0-9-]{1,64}$")
PORTABLE_FRONTMATTER_KEYS = frozenset(
    {"name", "description", "disable-model-invocation"}
)
SKIP_SKILL_DIR_NAMES = frozenset({"schema", "_authoring"})
PATH_REWRITES: tuple[tuple[str, str], ...] = (
    ("agent-skills/", "sdk/skills/"),
    ("skills-src/", "sdk/skills/"),
)
FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n?", re.DOTALL)


@dataclass(frozen=True)
class ParsedSkill:
    skill_id: str
    frontmatter: dict[str, Any]
    body: str
    skill_md_path: Path


@dataclass(frozen=True)
class ParsedContract:
    contract_id: str
    frontmatter: dict[str, Any]
    body: str
    source_path: Path


def load_json_schema(schema_path: Path) -> dict[str, Any]:
    import json

    return json.loads(schema_path.read_text(encoding="utf-8"))


def _validator(schema_path: Path) -> Draft202012Validator:
    schema = load_json_schema(schema_path)
    return Draft202012Validator(schema)


def split_skill_md(text: str) -> tuple[dict[str, Any], str]:
    match = FRONTMATTER_RE.match(text)
    if not match:
        return {}, text
    block = match.group(1)
    body = text[match.end() :]
    loaded = yaml.safe_load(block)
    if loaded is None:
        loaded = {}
    if not isinstance(loaded, dict):
        raise ValueError("SKILL.md frontmatter must be a YAML mapping")
    return loaded, body


def portable_frontmatter(frontmatter: dict[str, Any]) -> dict[str, Any]:
    portable: dict[str, Any] = {}
    if "name" in frontmatter:
        portable["name"] = frontmatter["name"]
    if "description" in frontmatter:
        portable["description"] = frontmatter["description"]
    if frontmatter.get("disable-model-invocation") is True:
        portable["disable-model-invocation"] = True
    return portable


def serialize_frontmatter(frontmatter: dict[str, Any]) -> str:
    return yaml.safe_dump(
        frontmatter,
        sort_keys=False,
        default_flow_style=False,
        allow_unicode=True,
    ).rstrip()


def render_skill_md(frontmatter: dict[str, Any], body: str) -> str:
    block = serialize_frontmatter(frontmatter)
    normalized_body = body.lstrip("\n")
    return f"---\n{block}\n---\n\n{normalized_body}"


def rewrite_paths(content: str) -> str:
    updated = content
    for old, new in PATH_REWRITES:
        updated = updated.replace(old, new)
    return updated


def parse_skill_md(skill_md: Path) -> ParsedSkill:
    text = skill_md.read_text(encoding="utf-8")
    frontmatter, body = split_skill_md(text)
    skill_id = skill_md.parent.name
    return ParsedSkill(
        skill_id=skill_id,
        frontmatter=frontmatter,
        body=body,
        skill_md_path=skill_md,
    )


def validate_skill(
    parsed: ParsedSkill,
    *,
    skill_schema_path: Path,
) -> list[str]:
    errors: list[str] = []
    fm = parsed.frontmatter
    skill_id = parsed.skill_id
    name = fm.get("name", skill_id)
    if name != skill_id:
        errors.append(f"{skill_id}: frontmatter name '{name}' must match directory")
    if not SKILL_NAME_PATTERN.fullmatch(str(name)):
        errors.append(f"{skill_id}: invalid skill name '{name}'")
    description = fm.get("description", "")
    if not isinstance(description, str) or not description.strip():
        errors.append(f"{skill_id}: description is required")
    elif len(description) > 1024:
        errors.append(f"{skill_id}: description exceeds 1024 characters")

    extra_keys = set(fm) - PORTABLE_FRONTMATTER_KEYS - {"endorlabs"}
    if extra_keys:
        errors.append(f"{skill_id}: unsupported frontmatter keys: {sorted(extra_keys)}")

    validator = _validator(skill_schema_path)
    for err in sorted(validator.iter_errors(fm), key=lambda e: list(e.path)):
        errors.append(f"{skill_id}: {err.message}")

    return errors


def normalize_skill_for_bundle(parsed: ParsedSkill) -> str:
    portable = portable_frontmatter(parsed.frontmatter)
    body = rewrite_paths(parsed.body)
    return render_skill_md(portable, body)


def split_contract_md(text: str) -> tuple[dict[str, Any], str]:
    return split_skill_md(text)


def parse_contract_md(path: Path) -> ParsedContract:
    text = path.read_text(encoding="utf-8")
    frontmatter, body = split_contract_md(text)
    contract_id = frontmatter.get("id", path.stem)
    return ParsedContract(
        contract_id=str(contract_id),
        frontmatter=frontmatter,
        body=body,
        source_path=path,
    )


def validate_contract(
    parsed: ParsedContract,
    *,
    contract_schema_path: Path,
) -> list[str]:
    errors: list[str] = []
    contract_id = parsed.contract_id
    if parsed.source_path.stem != contract_id:
        errors.append(
            f"contracts/{parsed.source_path.name}: id '{contract_id}' "
            f"must match filename stem"
        )
    validator = _validator(contract_schema_path)
    schema_errors = sorted(
        validator.iter_errors(parsed.frontmatter),
        key=lambda e: list(e.path),
    )
    errors.extend(
        f"contracts/{parsed.source_path.name}: {err.message}" for err in schema_errors
    )
    return errors


def render_contract_md(parsed: ParsedContract) -> str:
    block = serialize_frontmatter(parsed.frontmatter)
    normalized_body = parsed.body.lstrip("\n")
    return f"---\n{block}\n---\n\n{normalized_body}"


def load_supplemental_workflows(
    workflows_yaml: Path,
    *,
    workflows_schema_path: Path,
) -> list[dict[str, Any]]:
    if not workflows_yaml.is_file():
        return []
    raw = yaml.safe_load(workflows_yaml.read_text(encoding="utf-8"))
    if raw is None:
        raw = {"workflows": []}
    validator = _validator(workflows_schema_path)
    for err in sorted(validator.iter_errors(raw), key=lambda e: list(e.path)):
        raise ValueError(f"workflows.yaml: {err.message}")
    workflows = raw.get("workflows", [])
    return [_normalize_workflow_row(row) for row in workflows]


def _optional_workflow_catalog_fields(row: dict[str, Any]) -> dict[str, Any]:
    extra: dict[str, Any] = {}
    composition = row.get("composition")
    if composition is not None:
        extra["composition"] = composition
    entrypoints = row.get("library_entrypoints")
    if entrypoints is not None:
        extra["library_entrypoints"] = list(entrypoints)
    return extra


def _normalize_workflow_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": row["id"],
        "cli": row.get("cli"),
        "module": row["module"],
        "skill": row.get("skill"),
        "default_output": row.get("default_output"),
        "agent_visible": row.get("agent_visible", True),
        **_optional_workflow_catalog_fields(row),
    }


def workflow_row_from_skill_catalog(
    skill_id: str,
    catalog: dict[str, Any],
) -> dict[str, Any]:
    return {
        "id": catalog["workflow_id"],
        "cli": catalog.get("cli"),
        "module": catalog["module"],
        "skill": skill_id,
        "default_output": catalog.get("default_output"),
        "agent_visible": catalog.get("agent_visible", True),
        **_optional_workflow_catalog_fields(catalog),
    }


def build_workflow_catalog(
    supplemental: list[dict[str, Any]],
    skill_rows: list[tuple[str, dict[str, Any]]],
) -> list[dict[str, Any]]:
    by_id: dict[str, dict[str, Any]] = {}
    for row in supplemental:
        by_id[row["id"]] = row
    for skill_id, catalog in skill_rows:
        row = workflow_row_from_skill_catalog(skill_id, catalog)
        existing = by_id.get(row["id"])
        if existing is not None and existing != row:
            raise ValueError(
                f"workflow id '{row['id']}' conflicts between workflows.yaml and "
                f"skill '{skill_id}' catalog"
            )
        by_id[row["id"]] = row
    return [by_id[key] for key in sorted(by_id)]


def load_pyproject_scripts(pyproject_path: Path) -> dict[str, str]:
    data = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
    scripts = data.get("project", {}).get("scripts", {})
    if not isinstance(scripts, dict):
        return {}
    return {str(k): str(v) for k, v in scripts.items()}


def _entry_module(entry_point: str) -> str:
    return entry_point.split(":", 1)[0]


def validate_workflow_cli_entries(
    workflows: list[dict[str, Any]],
    *,
    pyproject_path: Path,
) -> list[str]:
    errors: list[str] = []
    scripts = load_pyproject_scripts(pyproject_path)
    for row in workflows:
        cli = row.get("cli")
        module = row.get("module")
        if not cli:
            continue
        entry = scripts.get(cli)
        if entry is None:
            errors.append(
                f"workflow '{row['id']}': cli '{cli}' missing from pyproject scripts"
            )
            continue
        expected_module = _entry_module(entry)
        if module != expected_module:
            errors.append(
                f"workflow '{row['id']}': module '{module}' does not match "
                f"pyproject script '{cli}' -> '{expected_module}'"
            )
    return errors


def build_contract_manifest_entries(contracts_dir: Path) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    if not contracts_dir.is_dir():
        return entries
    for path in sorted(contracts_dir.glob("*.md")):
        parsed = parse_contract_md(path)
        entry: dict[str, Any] = {
            "id": parsed.contract_id,
            "path": f"contracts/{path.name}",
            "tier": parsed.frontmatter.get("tier"),
            "tags": sorted(
                tag
                for tag in parsed.frontmatter.get("tags", [])
                if isinstance(tag, str)
            ),
        }
        summary = parsed.frontmatter.get("summary")
        if isinstance(summary, str) and summary.strip():
            entry["summary"] = summary.strip()
        entries.append(entry)
    return entries


def build_bootstrap_manifest_block(
    contracts: list[dict[str, Any]],
) -> dict[str, Any]:
    """Derive bootstrap contract ids from tier metadata."""
    contract_ids = sorted(
        entry["id"] for entry in contracts if entry.get("tier") == "bootstrap"
    )
    return {"index": "INDEX.md", "contract_ids": contract_ids}


def list_skill_refs(skill_dir: Path, *, bundle_skill_prefix: str) -> list[str]:
    refs: list[str] = []
    for path in sorted(
        skill_dir.rglob("*"),
        key=lambda candidate: candidate.relative_to(skill_dir).as_posix().encode(),
    ):
        if not path.is_file():
            continue
        rel = path.relative_to(skill_dir).as_posix()
        if rel == "SKILL.md":
            continue
        refs.append(f"{bundle_skill_prefix}/{rel}")
    return refs


def iter_skill_dirs(agent_skills_root: Path) -> list[Path]:
    if not agent_skills_root.is_dir():
        return []
    dirs: list[Path] = []
    for child in sorted(agent_skills_root.iterdir()):
        if not child.is_dir():
            continue
        if child.name in SKIP_SKILL_DIR_NAMES:
            continue
        if (child / "SKILL.md").is_file():
            dirs.append(child)
    return dirs


def collect_skill_catalog_rows(
    agent_skills_root: Path,
    *,
    skill_schema_path: Path,
) -> tuple[list[ParsedSkill], list[tuple[str, dict[str, Any]]], list[str]]:
    parsed_skills: list[ParsedSkill] = []
    catalog_rows: list[tuple[str, dict[str, Any]]] = []
    errors: list[str] = []
    for skill_dir in iter_skill_dirs(agent_skills_root):
        parsed = parse_skill_md(skill_dir / "SKILL.md")
        parsed_skills.append(parsed)
        errors.extend(validate_skill(parsed, skill_schema_path=skill_schema_path))
        endorlabs = parsed.frontmatter.get("endorlabs")
        if not endorlabs:
            continue
        if not isinstance(endorlabs, dict):
            errors.append(f"{parsed.skill_id}: endorlabs must be a mapping")
            continue
        catalog = endorlabs.get("catalog")
        if catalog is None:
            continue
        if not isinstance(catalog, dict):
            errors.append(f"{parsed.skill_id}: endorlabs.catalog must be a mapping")
            continue
        catalog_rows.append((parsed.skill_id, catalog))
    return parsed_skills, catalog_rows, errors
