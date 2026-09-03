"""Shipped agent knowledge (rules, contracts, skills, workflow index).

Materialized to ``.endorlabs/_cache/sdk/`` by :func:`endorlabs.init`.
"""

from __future__ import annotations

import json
from importlib import import_module
from pathlib import Path
from typing import Any, cast

from endorlabs.core.exceptions import ValidationError

_MANIFEST_FILENAME = "MANIFEST.json"
_INDEX_FILENAME = "INDEX.md"


def agent_knowledge_dir() -> Path:
    """Return the installed wheel path to the shipped agent knowledge package."""
    module = import_module("endorlabs.agent_knowledge")
    if module.__file__ is None:
        raise ValidationError(
            "endorlabs.agent_knowledge is a namespace package without a path"
        )
    return Path(module.__file__).resolve().parent


def agent_knowledge_index_path() -> Path:
    """Return path to Tier-0 INDEX.md inside the shipped package."""
    return agent_knowledge_dir() / _INDEX_FILENAME


def agent_knowledge_manifest_path() -> Path:
    """Return path to MANIFEST.json inside the shipped agent knowledge package."""
    return agent_knowledge_dir() / _MANIFEST_FILENAME


def agent_knowledge_manifest() -> dict[str, Any]:
    """Load and parse the shipped MANIFEST.json."""
    path = agent_knowledge_manifest_path()
    if not path.is_file():
        raise FileNotFoundError(f"Agent knowledge manifest not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _append_bootstrap_manifest_paths(
    paths: list[Path],
    *,
    bundle_root: Path,
    entries_raw: object,
    allowed_ids: set[str],
    id_key: str,
) -> None:
    if not isinstance(entries_raw, list):
        return
    for entry_raw in cast("list[object]", entries_raw):
        if not isinstance(entry_raw, dict):
            continue
        entry = cast("dict[str, Any]", entry_raw)
        entry_id = entry.get(id_key)
        rel_path = entry.get("path")
        if (
            not isinstance(entry_id, str)
            or entry_id not in allowed_ids
            or not isinstance(rel_path, str)
        ):
            continue
        paths.append(bundle_root / rel_path)


def agent_knowledge_bootstrap_paths(
    *,
    bundle: Path | None = None,
    validate: bool = False,
) -> list[Path]:
    """Return INDEX.md plus bootstrap rule and contract paths for harness injection."""
    bundle_root = bundle or agent_knowledge_dir()
    paths: list[Path] = [bundle_root / _INDEX_FILENAME]
    manifest_path = bundle_root / _MANIFEST_FILENAME
    if not manifest_path.is_file():
        if validate:
            raise ValidationError(
                f"Agent knowledge manifest not found: {manifest_path}"
            )
        return paths
    manifest: dict[str, Any] = json.loads(manifest_path.read_text(encoding="utf-8"))
    _append_bootstrap_manifest_paths(
        paths,
        bundle_root=bundle_root,
        entries_raw=manifest.get("rules"),
        allowed_ids=set(_bootstrap_rule_ids_from_manifest(manifest)),
        id_key="id",
    )
    _append_bootstrap_manifest_paths(
        paths,
        bundle_root=bundle_root,
        entries_raw=manifest.get("contracts"),
        allowed_ids=set(_bootstrap_contract_ids_from_manifest(manifest)),
        id_key="id",
    )
    if validate:
        missing = _missing_bootstrap_path_labels(bundle_root, paths)
        if missing:
            raise ValidationError(
                "Shipped agent knowledge bundle is incomplete "
                f"(missing {len(missing)} bootstrap path(s)): "
                + ", ".join(missing[:8])
                + ("..." if len(missing) > 8 else "")
                + ". Reinstall endorlabs or run endorlabs.init(force=True)."
            )
    return paths


def _missing_bootstrap_path_labels(
    bundle_root: Path,
    paths: list[Path],
) -> list[str]:
    return [
        path.relative_to(bundle_root).as_posix() for path in paths if not path.is_file()
    ]


def _bootstrap_rule_ids_from_manifest(manifest: dict[str, Any]) -> list[str]:
    bootstrap_obj = manifest.get("bootstrap")
    if not isinstance(bootstrap_obj, dict):
        return []
    bootstrap = cast("dict[str, Any]", bootstrap_obj)
    rule_ids_raw = bootstrap.get("rule_ids")
    if not isinstance(rule_ids_raw, list):
        return []
    return [
        item for item in cast("list[object]", rule_ids_raw) if isinstance(item, str)
    ]


def _bootstrap_contract_ids_from_manifest(manifest: dict[str, Any]) -> list[str]:
    bootstrap_obj = manifest.get("bootstrap")
    if not isinstance(bootstrap_obj, dict):
        return []
    bootstrap = cast("dict[str, Any]", bootstrap_obj)
    contract_ids_raw = bootstrap.get("contract_ids")
    if not isinstance(contract_ids_raw, list):
        return []
    return [
        item for item in cast("list[object]", contract_ids_raw) if isinstance(item, str)
    ]


def validate_agent_knowledge_tree(bundle: Path | None = None) -> None:
    """Raise when bootstrap or manifest catalog paths are missing on disk."""
    bundle_root = bundle or agent_knowledge_dir()
    _ = agent_knowledge_bootstrap_paths(bundle=bundle_root, validate=True)
    manifest: dict[str, Any] = json.loads(
        (bundle_root / _MANIFEST_FILENAME).read_text(encoding="utf-8")
    )
    missing_catalog: list[str] = []
    for key in ("skills", "rules", "contracts"):
        entries = manifest.get(key)
        if not isinstance(entries, list):
            continue
        for entry_raw in cast("list[object]", entries):
            if not isinstance(entry_raw, dict):
                continue
            entry = cast("dict[str, Any]", entry_raw)
            rel_path = entry.get("path")
            if not isinstance(rel_path, str):
                continue
            if not (bundle_root / rel_path).is_file():
                missing_catalog.append(rel_path)
    if missing_catalog:
        raise ValidationError(
            "Shipped agent knowledge bundle is incomplete "
            f"(missing {len(missing_catalog)} MANIFEST path(s)): "
            + ", ".join(missing_catalog[:8])
            + ("..." if len(missing_catalog) > 8 else "")
            + ". Reinstall endorlabs or run endorlabs.init(force=True)."
        )


def agent_knowledge_rule_ids() -> list[str]:
    """Return bootstrap rule ids from the shipped manifest."""
    return _bootstrap_rule_ids_from_manifest(agent_knowledge_manifest())


def agent_knowledge_contract_ids() -> list[str]:
    """Return bootstrap contract ids from the shipped manifest."""
    return _bootstrap_contract_ids_from_manifest(agent_knowledge_manifest())


__all__ = [
    "agent_knowledge_bootstrap_paths",
    "agent_knowledge_contract_ids",
    "agent_knowledge_dir",
    "agent_knowledge_index_path",
    "agent_knowledge_manifest",
    "agent_knowledge_manifest_path",
    "agent_knowledge_rule_ids",
    "validate_agent_knowledge_tree",
]
