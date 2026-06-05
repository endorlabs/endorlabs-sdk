"""Sync agent-knowledge/ into the shipped agent_knowledge package and regenerate MANIFEST.json.

Run from repo root::



    uv run python devtools/sync_agent_knowledge.py

    uv run python devtools/sync_agent_knowledge.py --verify



"""

# ruff: noqa: E402, E501, D103, PLW0603, T201

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


from devtools.agent_knowledge_catalog import (
    AGENT_CONTRACTS_SUBDIR,
    AGENT_DIRNAME,
    AGENT_RULES_SUBDIR,
    build_bootstrap_manifest_block,
    build_contract_manifest_entries,
    build_rules_manifest_entries,
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
    validate_rule,
    validate_workflow_cli_entries,
)

AGENT_ROOT = REPO_ROOT / AGENT_DIRNAME

SCHEMA_DIR = AGENT_ROOT / "schema"

BUNDLE_ROOT = REPO_ROOT / "src" / "endorlabs" / "agent_knowledge"

BUNDLE_SKILLS = BUNDLE_ROOT / "skills"

BUNDLE_RULES = BUNDLE_ROOT / "rules"

BUNDLE_CONTRACTS = BUNDLE_ROOT / "contracts"

MANIFEST_PATH = BUNDLE_ROOT / "MANIFEST.json"

INDEX_PATH = BUNDLE_ROOT / "INDEX.md"

WORKFLOWS_INDEX = BUNDLE_ROOT / "workflows" / "index.md"

WORKFLOWS_ENTRIES = BUNDLE_ROOT / "workflows" / "entries.json"

WORKFLOWS_YAML = AGENT_ROOT / "workflows.yaml"

PYPROJECT = REPO_ROOT / "pyproject.toml"

CURSOR_RULES_DIR = REPO_ROOT / ".cursor" / "rules"

CURSOR_GENERATED_MANIFEST = CURSOR_RULES_DIR / "_generated.json"

HAND_MAINTAINED_CURSOR_RULES = frozenset(
    {"agent-knowledge-authoring", "docs-skillbase-consistency"}
)


TEXT_SUFFIXES = {".md", ".py", ".yaml", ".yml", ".txt"}

MANIFEST_SCHEMA_VERSION = 2


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
    """Normalize agent-knowledge/skills into agent_knowledge/skills."""
    if not AGENT_ROOT.is_dir():
        raise FileNotFoundError(f"Agent authoring root not found: {AGENT_ROOT}")

    skill_schema = SCHEMA_DIR / "skill.schema.json"

    parsed_skills, catalog_rows, errors = collect_skill_catalog_rows(
        AGENT_ROOT,
        skill_schema_path=skill_schema,
    )

    _raise_validation_errors(errors)

    if BUNDLE_SKILLS.exists():
        shutil.rmtree(BUNDLE_SKILLS)

    BUNDLE_SKILLS.mkdir(parents=True, exist_ok=True)

    copied = 0

    for skill_dir in iter_skill_dirs(AGENT_ROOT):
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


def sync_rules_tree() -> int:
    """Copy agent-knowledge/rules into agent_knowledge/rules."""
    rule_schema = SCHEMA_DIR / "rule.schema.json"

    source_dir = AGENT_ROOT / AGENT_RULES_SUBDIR

    if not source_dir.is_dir():
        return 0

    if BUNDLE_RULES.exists():
        shutil.rmtree(BUNDLE_RULES)

    BUNDLE_RULES.mkdir(parents=True, exist_ok=True)

    errors: list[str] = []

    copied = 0

    for src_path in sorted(source_dir.glob("*.md")):
        parsed = parse_contract_md(src_path)

        errors.extend(validate_rule(parsed, rule_schema_path=rule_schema))

        rendered = render_contract_md(parsed)

        rendered = rewrite_paths(rendered)

        dest_path = BUNDLE_RULES / src_path.name

        dest_path.write_text(rendered, encoding="utf-8")

        copied += 1

    _raise_validation_errors(errors)

    return copied


def sync_contracts_tree() -> int:
    """Copy agent-knowledge/contracts into agent_knowledge/contracts."""
    contract_schema = SCHEMA_DIR / "contract.schema.json"

    source_dir = AGENT_ROOT / AGENT_CONTRACTS_SUBDIR

    if not source_dir.is_dir():
        return 0

    if BUNDLE_CONTRACTS.exists():
        shutil.rmtree(BUNDLE_CONTRACTS)

    BUNDLE_CONTRACTS.mkdir(parents=True, exist_ok=True)

    errors: list[str] = []

    copied = 0

    for src_path in sorted(source_dir.glob("*.md")):
        parsed = parse_contract_md(src_path)

        errors.extend(validate_contract(parsed, contract_schema_path=contract_schema))

        rendered = render_contract_md(parsed)

        rendered = rewrite_paths(rendered)

        dest_path = BUNDLE_CONTRACTS / src_path.name

        dest_path.write_text(rendered, encoding="utf-8")

        copied += 1

    _raise_validation_errors(errors)

    return copied


def sync_index() -> None:
    source = AGENT_ROOT / "INDEX.md"

    if not source.is_file():
        return

    INDEX_PATH.write_text(
        rewrite_paths(source.read_text(encoding="utf-8")), encoding="utf-8"
    )


def _rule_description(parsed: Any) -> str:
    summary = parsed.frontmatter.get("summary")

    if isinstance(summary, str) and summary.strip():
        return summary.strip().replace("\n", " ")

    return str(parsed.contract_id)


def _repo_relative_posix(path: Path) -> str:
    return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()


def _source_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_cursor_rule_contents() -> dict[str, str]:
    """Build expected .mdc contents from agent-knowledge/rules."""
    rule_schema = SCHEMA_DIR / "rule.schema.json"

    source_dir = AGENT_ROOT / AGENT_RULES_SUBDIR

    contents: dict[str, str] = {}

    errors: list[str] = []

    if not source_dir.is_dir():
        return contents

    for src_path in sorted(source_dir.glob("*.md")):
        parsed = parse_contract_md(src_path)

        errors.extend(validate_rule(parsed, rule_schema_path=rule_schema))

        rule_id = parsed.contract_id

        body = rewrite_paths(parsed.body.lstrip("\n"))

        description = _rule_description(parsed)

        source_rel = _repo_relative_posix(src_path)

        source_sha256 = _source_sha256(src_path)

        mdc = (
            "---\n"
            f"description: {description}\n"
            "alwaysApply: true\n"
            "x-endor-generated: true\n"
            f"x-endor-source: {source_rel}\n"
            f"x-endor-source-sha256: {source_sha256}\n"
            "---\n\n"
            f"{body}"
        )

        if not mdc.endswith("\n"):
            mdc += "\n"

        contents[rule_id] = mdc

    _raise_validation_errors(errors)

    return contents


def emit_cursor_rules() -> list[str]:
    """Generate always-on .mdc rules from agent-knowledge/rules."""
    CURSOR_RULES_DIR.mkdir(parents=True, exist_ok=True)

    contents = build_cursor_rule_contents()

    generated_ids = sorted(contents)

    for rule_id, mdc in contents.items():
        (CURSOR_RULES_DIR / f"{rule_id}.mdc").write_text(mdc, encoding="utf-8")

    previous_manifest: list[str] = []

    if CURSOR_GENERATED_MANIFEST.is_file():
        loaded = json.loads(CURSOR_GENERATED_MANIFEST.read_text(encoding="utf-8"))

        if isinstance(loaded, list):
            previous_manifest = [str(item) for item in loaded]

    for stale_id in previous_manifest:
        if stale_id in generated_ids or stale_id in HAND_MAINTAINED_CURSOR_RULES:
            continue

        stale_path = CURSOR_RULES_DIR / f"{stale_id}.mdc"

        if stale_path.is_file():
            stale_path.unlink()

    CURSOR_GENERATED_MANIFEST.write_text(
        json.dumps(generated_ids, indent=2) + "\n",
        encoding="utf-8",
    )

    return generated_ids


def verify_cursor_rules() -> list[str]:
    """Compare committed Cursor rules against agent-knowledge/rules generation."""
    errors: list[str] = []

    expected = build_cursor_rule_contents()

    expected_ids = sorted(expected)

    if CURSOR_GENERATED_MANIFEST.is_file():
        loaded = json.loads(CURSOR_GENERATED_MANIFEST.read_text(encoding="utf-8"))

        if list(loaded) != expected_ids:
            errors.append(
                ".cursor/rules/_generated.json drift (run devtools/sync_agent_knowledge.py)"
            )

    else:
        errors.append(
            ".cursor/rules/_generated.json missing (run devtools/sync_agent_knowledge.py)"
        )

    for rule_id, mdc in expected.items():
        path = CURSOR_RULES_DIR / f"{rule_id}.mdc"

        if not path.is_file():
            errors.append(f".cursor/rules/{rule_id}.mdc missing")

            continue

        if path.read_text(encoding="utf-8") != mdc:
            errors.append(f".cursor/rules/{rule_id}.mdc drift")

    return errors


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
                "refs": list_skill_refs(
                    skill_dir, bundle_skill_prefix=f"skills/{skill_id}"
                ),
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
        AGENT_ROOT,
        skill_schema_path=SCHEMA_DIR / "skill.schema.json",
    )

    _raise_validation_errors(errors)

    workflows = build_workflow_catalog(supplemental, catalog_rows)

    cli_errors = validate_workflow_cli_entries(workflows, pyproject_path=PYPROJECT)

    _raise_validation_errors(cli_errors)

    return workflows


def build_manifest() -> dict[str, Any]:
    rules = build_rules_manifest_entries(AGENT_ROOT / AGENT_RULES_SUBDIR)

    contracts = build_contract_manifest_entries(AGENT_ROOT / AGENT_CONTRACTS_SUBDIR)

    return {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "sdk_version": _read_sdk_version(),
        "generated_at": datetime.now(UTC).isoformat(),
        "index": "INDEX.md",
        "bootstrap": build_bootstrap_manifest_block(rules),
        "rules": rules,
        "contracts": contracts,
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
    global BUNDLE_ROOT, BUNDLE_SKILLS, BUNDLE_RULES, BUNDLE_CONTRACTS

    global MANIFEST_PATH, INDEX_PATH, WORKFLOWS_INDEX, WORKFLOWS_ENTRIES

    root = bundle_root or BUNDLE_ROOT

    prev = (
        BUNDLE_ROOT,
        BUNDLE_SKILLS,
        BUNDLE_RULES,
        BUNDLE_CONTRACTS,
        MANIFEST_PATH,
        INDEX_PATH,
        WORKFLOWS_INDEX,
        WORKFLOWS_ENTRIES,
    )

    BUNDLE_ROOT = root

    BUNDLE_SKILLS = root / "skills"

    BUNDLE_RULES = root / "rules"

    BUNDLE_CONTRACTS = root / "contracts"

    MANIFEST_PATH = root / "MANIFEST.json"

    INDEX_PATH = root / "INDEX.md"

    WORKFLOWS_INDEX = root / "workflows" / "index.md"

    WORKFLOWS_ENTRIES = root / "workflows" / "entries.json"

    generated_rules: list[str] = []

    try:
        skill_files = sync_skills_tree()

        rule_files = sync_rules_tree()

        contract_files = sync_contracts_tree()

        sync_index()

        generated_rules = emit_cursor_rules()

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
                BUNDLE_RULES,
                BUNDLE_CONTRACTS,
                MANIFEST_PATH,
                INDEX_PATH,
                WORKFLOWS_INDEX,
                WORKFLOWS_ENTRIES,
            ) = prev

    rel_root = root.relative_to(REPO_ROOT) if root.is_relative_to(REPO_ROOT) else root

    print(f"Synced {skill_files} skill files into {rel_root / 'skills'}")

    print(f"Synced {rule_files} rule files into {rel_root / 'rules'}")

    print(f"Synced {contract_files} contract files into {rel_root / 'contracts'}")

    print(f"Wrote {rel_root / 'MANIFEST.json'} ({len(manifest['skills'])} skills)")

    if generated_rules:
        print(f"Generated {len(generated_rules)} Cursor rules into .cursor/rules/")

    return manifest


def _file_tree_hash(root: Path) -> dict[str, str]:
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

    snapshot_rules = _file_tree_hash(BUNDLE_RULES)

    snapshot_contracts = _file_tree_hash(BUNDLE_CONTRACTS)

    snapshot_index_tree = _file_tree_hash(BUNDLE_ROOT)

    snapshot_index = snapshot_index_tree.get("INDEX.md")

    snapshot_manifest = _normalize_manifest_bytes(
        MANIFEST_PATH.read_bytes() if MANIFEST_PATH.is_file() else b"{}"
    )

    snapshot_workflows = _file_tree_hash(WORKFLOWS_INDEX.parent)

    with tempfile.TemporaryDirectory() as tmp:
        tmp_root = Path(tmp) / "agent_knowledge"

        sync_bundle(bundle_root=tmp_root)

        regen_skills = _file_tree_hash(tmp_root / "skills")

        regen_rules = _file_tree_hash(tmp_root / "rules")

        regen_contracts = _file_tree_hash(tmp_root / "contracts")

        regen_index_hash = _file_tree_hash(tmp_root).get("INDEX.md")

        regen_manifest = _normalize_manifest_bytes(
            (tmp_root / "MANIFEST.json").read_bytes()
        )

        regen_workflows = _file_tree_hash(tmp_root / "workflows")

    errors: list[str] = []

    errors.extend(verify_cursor_rules())

    if snapshot_skills != regen_skills:
        errors.append("agent_knowledge/skills drift (run devtools/sync_agent_knowledge.py)")

    if snapshot_rules != regen_rules:
        errors.append("agent_knowledge/rules drift (run devtools/sync_agent_knowledge.py)")

    if snapshot_contracts != regen_contracts:
        errors.append(
            "agent_knowledge/contracts drift (run devtools/sync_agent_knowledge.py)"
        )

    if snapshot_index != regen_index_hash:
        errors.append("agent_knowledge/INDEX.md drift (run devtools/sync_agent_knowledge.py)")

    if snapshot_manifest != regen_manifest:
        errors.append("agent_knowledge/MANIFEST.json drift")

        import difflib

        committed_lines = snapshot_manifest.decode("utf-8").splitlines()

        regen_lines = regen_manifest.decode("utf-8").splitlines()

        for line in difflib.unified_diff(
            committed_lines,
            regen_lines,
            fromfile="committed",
            tofile="regenerated",
            lineterm="",
        ):
            print(line, file=sys.stderr)

    if snapshot_workflows != regen_workflows:
        errors.append("agent_knowledge/workflows drift")

    if errors:
        for msg in errors:
            print(f"ERROR: {msg}", file=sys.stderr)

        return 1

    print("Agent knowledge is up to date.")

    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Sync agent-knowledge/ into agent_knowledge.")

    _ = parser.add_argument(
        "--verify",
        action="store_true",
        help="Verify committed bundle matches agent-knowledge/ (no writes).",
    )

    args = parser.parse_args(argv)

    if args.verify:
        return verify_bundle()

    sync_bundle()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
