"""Shipped agent knowledge (rules, contracts, skills, workflow index).

Materialized to ``.endorlabs-context/sdk/`` by :func:`endorlabs.init`.
"""

from __future__ import annotations

import json
from importlib import import_module
from pathlib import Path
from typing import Any, cast

_MANIFEST_FILENAME = "MANIFEST.json"
_INDEX_FILENAME = "INDEX.md"


def agent_knowledge_dir() -> Path:
    """Return the installed wheel path to the shipped agent knowledge package."""
    module = import_module("endorlabs.agent_knowledge")
    if module.__file__ is None:
        raise RuntimeError(
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


def agent_knowledge_rule_ids() -> list[str]:
    """Return bootstrap rule ids from the shipped manifest."""
    manifest: dict[str, Any] = agent_knowledge_manifest()
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


def agent_knowledge_bootstrap_paths() -> list[Path]:
    """Return INDEX.md plus bootstrap rule paths for harness injection."""
    bundle = agent_knowledge_dir()
    paths: list[Path] = [agent_knowledge_index_path()]
    manifest: dict[str, Any] = agent_knowledge_manifest()
    rules_raw = manifest.get("rules")
    if not isinstance(rules_raw, list):
        return paths
    bootstrap_ids = set(agent_knowledge_rule_ids())
    for entry_raw in cast("list[object]", rules_raw):
        if not isinstance(entry_raw, dict):
            continue
        entry = cast("dict[str, Any]", entry_raw)
        rule_id = entry.get("id")
        rel_path = entry.get("path")
        if (
            not isinstance(rule_id, str)
            or rule_id not in bootstrap_ids
            or not isinstance(rel_path, str)
        ):
            continue
        paths.append(bundle / rel_path)
    return paths


__all__ = [
    "agent_knowledge_bootstrap_paths",
    "agent_knowledge_dir",
    "agent_knowledge_index_path",
    "agent_knowledge_manifest",
    "agent_knowledge_manifest_path",
    "agent_knowledge_rule_ids",
]
