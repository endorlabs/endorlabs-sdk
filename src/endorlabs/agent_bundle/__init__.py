"""Shipped agent knowledge bundle (skills, contracts, workflow index).

Materialized to ``.endorlabs-context/sdk/`` by :func:`endorlabs.init`.
"""

from __future__ import annotations

import json
from importlib import import_module
from pathlib import Path
from typing import Any

_MANIFEST_FILENAME = "MANIFEST.json"
_INDEX_FILENAME = "INDEX.md"


def agent_bundle_dir() -> Path:
    """Return the installed wheel path to the shipped agent bundle."""
    module = import_module("endorlabs.agent_bundle")
    if module.__file__ is None:
        raise RuntimeError(
            "endorlabs.agent_bundle is a namespace package without a path"
        )
    return Path(module.__file__).resolve().parent


def agent_index_path() -> Path:
    """Return path to Tier-0 INDEX.md inside the shipped bundle."""
    return agent_bundle_dir() / _INDEX_FILENAME


def agent_manifest_path() -> Path:
    """Return path to MANIFEST.json inside the shipped bundle."""
    return agent_bundle_dir() / _MANIFEST_FILENAME


def agent_manifest() -> dict[str, Any]:
    """Load and parse the shipped MANIFEST.json."""
    path = agent_manifest_path()
    if not path.is_file():
        raise FileNotFoundError(f"Agent bundle manifest not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


__all__ = [
    "agent_bundle_dir",
    "agent_index_path",
    "agent_manifest",
    "agent_manifest_path",
]
