"""Sync agent-skills into the shipped agent bundle and regenerate MANIFEST.json.

Run from repo root::

    uv run python devtools/sync_agent_bundle.py
    uv run python devtools/sync_agent_bundle.py --verify

"""
# ruff: noqa: E402, E501, D103, PLW0603, T201

from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from devtools.agent_bundle_catalog import (
    AGENT_SKILLS_DIRNAME,
    build_contract_manifest_entries,
    build_workflow_catalog,
    collect_skill_catalog_rows,
    iter_skill_dirs,
    list_skill_refs,
    load_supplemental_workflows,
    normalize_skill_for_bundle,
    parse_contract_md,
    parse_skill_md,
    portable_frontmatter,
    render_contract_md,
    rewrite_paths,
    validate_contract,
    validate_workflow_cli_entries,
)

AGENT_SKILLS = REPO_ROOT / AGENT_SKILLS_DIRNAME
SCHEMA_DIR = AGENT_SKILLS / "schema"
BUNDLE_ROOT = REPO_ROOT / "src" / "endorlabs" / "agent_bundle"
BUNDLE_SKILLS = BUNDLE_ROOT / "skills"
BUNDLE_CONTRACTS = BUNDLE_ROOT / "contracts"
MANIFEST_PATH = BUNDLE_ROOT / "MANIFEST.json"
INDEX_PATH = BUNDLE_ROOT / "INDEX.md"
WORKFLOWS_INDEX = BUNDLE_ROOT / "workflows" / "index.md"
WORKFLOWS_ENTRIES = BUNDLE_ROOT / "workflows" / "entries.json"
WORKFLOWS_YAML = AGENT_SKILLS / "workflows.yaml"
PYPROJECT = REPO_ROOT / "pyproject.toml"

TEXT_SUFFIXES = {".md", ".py", ".yaml", ".yml", ".txt"}


def _read_sdk_version() -> str:
    try:
        sys.path.insert(0, str(REPO_ROOT / "src"))
        from endorlabs import __version__

        return __version__
    except Exception:
        return "0.0.0.dev0"


def _raise_validation_errors(errors: list[str]) -> None:
    if not errors:
        return
    for msg in errors:
        print(f"ERROR: {msg}", file=sys.stderr)
    raise SystemExit(1)


def _copy_text_file(src: Path, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    text = src.read_text(encoding="utf-8")
    dest.write_text(rewrite_paths(text), encoding="utf-8")


def sync_skills_tree() -> int:
    """Normalize agent-skills into agent_bundle/skills."""
    if not AGENT_SKILLS.is_dir():
        raise FileNotFoundError(f"Agent skills source not found: {AGENT_SKILLS}")
    skill_schema = SCHEMA_DIR / "skill.schema.json"
    parsed_skills, catalog_rows, errors = collect_skill_catalog_rows(
        AGENT_SKILLS,
        skill_schema_path=skill_schema,
    )
    _raise_validation_errors(errors)

    if BUNDLE_SKILLS.exists():
        shutil.rmtree(BUNDLE_SKILLS)
    BUNDLE_SKILLS.mkdir(parents=True, exist_ok=True)

    copied = 0
    for skill_dir in iter_skill_dirs(AGENT_SKILLS):
        dest_dir = BUNDLE_SKILLS / skill_dir.name
        dest_dir.mkdir(parents=True, exist_ok=True)
        parsed = parse_skill_md(skill_dir / "SKILL.md")
        normalized = normalize_skill_for_bundle(parsed)
        (dest_dir / "SKILL.md").write_text(normalized, encoding="utf-8")
        copied += 1

        for src_path in skill_dir.rglob("*"):
            if not src_path.is_file() or src_path.name == "SKILL.md":
                continue
            rel = src_path.relative_to(skill_dir)
            dest_path = dest_dir / rel
            if src_path.suffix in TEXT_SUFFIXES:
                _copy_text_file(src_path, dest_path)
            else:
                dest_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src_path, dest_path)
            copied += 1

    _ = parsed_skills, catalog_rows
    return copied


def sync_contracts_tree() -> int:
    """Copy agent-skills/contracts into agent_bundle/contracts."""
    contract_schema = SCHEMA_DIR / "contract.schema.json"
    source_dir = AGENT_SKILLS / "contracts"
    if not source_dir.is_dir():
        return 0
    if BUNDLE_CONTRACTS.exists():
        shutil.rmtree(BUNDLE_CONTRACTS)
    BUNDLE_CONTRACTS.mkdir(parents=True, exist_ok=True)

    errors: list[str] = []
    copied = 0
    for src_path in sorted(source_dir.glob("*.md")):
        parsed = parse_contract_md(src_path)
        errors.extend(
            validate_contract(parsed, contract_schema_path=contract_schema)
        )
        rendered = render_contract_md(parsed)
        rendered = rewrite_paths(rendered)
        dest_path = BUNDLE_CONTRACTS / src_path.name
        dest_path.write_text(rendered, encoding="utf-8")
        copied += 1
    _raise_validation_errors(errors)
    return copied


def sync_index() -> None:
    source = AGENT_SKILLS / "INDEX.md"
    if not source.is_file():
        return
    INDEX_PATH.write_text(rewrite_paths(source.read_text(encoding="utf-8")), encoding="utf-8")


def build_skills_manifest_entries() -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    if not BUNDLE_SKILLS.is_dir():
        return entries
    for skill_dir in sorted(BUNDLE_SKILLS.iterdir()):
        if not skill_dir.is_dir():
            continue
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.is_file():
            continue
        parsed = parse_skill_md(skill_md)
        portable = portable_frontmatter(parsed.frontmatter)
        skill_id = skill_dir.name
        entries.append(
            {
                "id": skill_id,
                "path": f"skills/{skill_id}/SKILL.md",
                "name": portable.get("name", skill_id),
                "description": portable.get("description", ""),
                "refs": list_skill_refs(skill_dir, bundle_skill_prefix=f"skills/{skill_id}"),
            }
        )
    return entries


def build_workflows_manifest_entries() -> list[dict[str, Any]]:
    workflows_schema = SCHEMA_DIR / "workflows.schema.json"
    supplemental = load_supplemental_workflows(
        WORKFLOWS_YAML,
        workflows_schema_path=workflows_schema,
    )
    _, catalog_rows, errors = collect_skill_catalog_rows(
        AGENT_SKILLS,
        skill_schema_path=SCHEMA_DIR / "skill.schema.json",
    )
    _raise_validation_errors(errors)
    workflows = build_workflow_catalog(supplemental, catalog_rows)
    cli_errors = validate_workflow_cli_entries(workflows, pyproject_path=PYPROJECT)
    _raise_validation_errors(cli_errors)
    return workflows


def build_manifest() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "sdk_version": _read_sdk_version(),
        "generated_at": datetime.now(UTC).isoformat(),
        "index": "INDEX.md",
        "contracts": build_contract_manifest_entries(AGENT_SKILLS / "contracts"),
        "skills": build_skills_manifest_entries(),
        "workflows": build_workflows_manifest_entries(),
    }


def write_workflows_index(manifest: dict[str, Any]) -> None:
    WORKFLOWS_INDEX.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Workflow CLI index",
        "",
        "Thin index of SDK workflow entry points. See `MANIFEST.json` for machine-readable data.",
        "",
        "| ID | CLI | Module | Skill | Default output |",
        "|----|-----|--------|-------|----------------|",
    ]
    for entry in manifest["workflows"]:
        if not entry.get("agent_visible", True):
            continue
        cli = entry.get("cli") or "—"
        skill = entry.get("skill") or "—"
        default_out = entry.get("default_output") or "—"
        lines.append(
            f"| {entry['id']} | `{cli}` | `{entry['module']}` | {skill} | {default_out} |"
        )
    WORKFLOWS_INDEX.write_text("\n".join(lines) + "\n", encoding="utf-8")
    visible = [e for e in manifest["workflows"] if e.get("agent_visible", True)]
    WORKFLOWS_ENTRIES.write_text(
        json.dumps(visible, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def sync_bundle(*, bundle_root: Path | None = None) -> dict[str, Any]:
    global BUNDLE_ROOT, BUNDLE_SKILLS, BUNDLE_CONTRACTS, MANIFEST_PATH
    global INDEX_PATH, WORKFLOWS_INDEX, WORKFLOWS_ENTRIES
    root = bundle_root or BUNDLE_ROOT
    prev = (
        BUNDLE_ROOT,
        BUNDLE_SKILLS,
        BUNDLE_CONTRACTS,
        MANIFEST_PATH,
        INDEX_PATH,
        WORKFLOWS_INDEX,
        WORKFLOWS_ENTRIES,
    )
    BUNDLE_ROOT = root
    BUNDLE_SKILLS = root / "skills"
    BUNDLE_CONTRACTS = root / "contracts"
    MANIFEST_PATH = root / "MANIFEST.json"
    INDEX_PATH = root / "INDEX.md"
    WORKFLOWS_INDEX = root / "workflows" / "index.md"
    WORKFLOWS_ENTRIES = root / "workflows" / "entries.json"
    try:
        skill_files = sync_skills_tree()
        contract_files = sync_contracts_tree()
        sync_index()
        manifest = build_manifest()
        new_manifest_bytes = (
            json.dumps(manifest, indent=2, sort_keys=True).encode("utf-8") + b"\n"
        )
        if not MANIFEST_PATH.is_file() or _normalize_manifest_bytes(
            MANIFEST_PATH.read_bytes()
        ) != _normalize_manifest_bytes(new_manifest_bytes):
            MANIFEST_PATH.write_bytes(new_manifest_bytes)
        write_workflows_index(manifest)
    finally:
        if bundle_root is not None:
            (
                BUNDLE_ROOT,
                BUNDLE_SKILLS,
                BUNDLE_CONTRACTS,
                MANIFEST_PATH,
                INDEX_PATH,
                WORKFLOWS_INDEX,
                WORKFLOWS_ENTRIES,
            ) = prev

    rel_root = root.relative_to(REPO_ROOT) if root.is_relative_to(REPO_ROOT) else root
    print(f"Synced {skill_files} skill files into {rel_root / 'skills'}")
    print(f"Synced {contract_files} contract files into {rel_root / 'contracts'}")
    print(f"Wrote {rel_root / 'MANIFEST.json'} ({len(manifest['skills'])} skills)")
    return manifest


def _file_tree_hash(root: Path) -> dict[str, str]:
    import hashlib

    out: dict[str, str] = {}
    if not root.exists():
        return out
    for path in sorted(root.rglob("*")):
        if path.is_file():
            rel = path.relative_to(root).as_posix()
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            out[rel] = digest
    return out


def _normalize_manifest_bytes(payload: bytes) -> bytes:
    data = json.loads(payload.decode("utf-8"))
    data.pop("generated_at", None)
    data.pop("sdk_version", None)
    return json.dumps(data, indent=2, sort_keys=True).encode("utf-8") + b"\n"


def verify_bundle() -> int:
    """Regenerate to a temp dir and compare against committed bundle artifacts."""
    import tempfile

    snapshot_skills = _file_tree_hash(BUNDLE_SKILLS)
    snapshot_contracts = _file_tree_hash(BUNDLE_CONTRACTS)
    snapshot_index_tree = _file_tree_hash(BUNDLE_ROOT)
    snapshot_index = snapshot_index_tree.get("INDEX.md")
    snapshot_manifest = _normalize_manifest_bytes(
        MANIFEST_PATH.read_bytes() if MANIFEST_PATH.is_file() else b"{}"
    )
    snapshot_workflows = _file_tree_hash(WORKFLOWS_INDEX.parent)

    with tempfile.TemporaryDirectory() as tmp:
        tmp_root = Path(tmp) / "agent_bundle"
        sync_bundle(bundle_root=tmp_root)

        regen_skills = _file_tree_hash(tmp_root / "skills")
        regen_contracts = _file_tree_hash(tmp_root / "contracts")
        regen_index_hash = _file_tree_hash(tmp_root).get("INDEX.md")
        regen_manifest = _normalize_manifest_bytes(
            (tmp_root / "MANIFEST.json").read_bytes()
        )
        regen_workflows = _file_tree_hash(tmp_root / "workflows")

    errors: list[str] = []
    if snapshot_skills != regen_skills:
        errors.append("agent_bundle/skills drift (run devtools/sync_agent_bundle.py)")
    if snapshot_contracts != regen_contracts:
        errors.append("agent_bundle/contracts drift (run devtools/sync_agent_bundle.py)")
    if snapshot_index != regen_index_hash:
        errors.append("agent_bundle/INDEX.md drift (run devtools/sync_agent_bundle.py)")
    if snapshot_manifest != regen_manifest:
        errors.append("agent_bundle/MANIFEST.json drift")
    if snapshot_workflows != regen_workflows:
        errors.append("agent_bundle/workflows drift")
    if errors:
        for msg in errors:
            print(f"ERROR: {msg}", file=sys.stderr)
        return 1
    print("Agent bundle is up to date.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Sync agent-skills into agent_bundle."
    )
    _ = parser.add_argument(
        "--verify",
        action="store_true",
        help="Verify committed bundle matches agent-skills (no writes).",
    )
    args = parser.parse_args(argv)
    if args.verify:
        return verify_bundle()
    sync_bundle()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
