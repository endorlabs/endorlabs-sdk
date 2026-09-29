"""Unit tests for JsonlKeyedStore."""

from __future__ import annotations

import json
from pathlib import Path

from endorlabs.utils.jsonl_store import JsonlKeyedStore


def test_upsert_and_atomic_rewrite(tmp_path: Path) -> None:
    path = tmp_path / "rows.jsonl"
    store = JsonlKeyedStore(path, ("project_uuid", "package_version_uuid"))
    store.upsert(
        {
            "project_uuid": "p1",
            "package_version_uuid": "v1",
            "package_name": "a",
        }
    )
    store.upsert(
        {
            "project_uuid": "p1",
            "package_version_uuid": "v2",
            "package_name": "b",
        }
    )
    store.flush()
    assert path.is_file()
    lines = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    assert len(lines) == 2

    store.upsert(
        {
            "project_uuid": "p1",
            "package_version_uuid": "v1",
            "package_name": "a-updated",
        }
    )
    store.flush()
    reloaded = JsonlKeyedStore(path, ("project_uuid", "package_version_uuid"))
    assert len(reloaded) == 2
    row = reloaded.get("p1", "v1")
    assert row is not None
    assert row["package_name"] == "a-updated"


def test_single_key_field(tmp_path: Path) -> None:
    path = tmp_path / "cache.jsonl"
    store = JsonlKeyedStore(path, ("package_version_uuid",))
    store.upsert({"package_version_uuid": "pv1", "primary_spdx": "MIT"})
    store.flush()
    store.upsert({"package_version_uuid": "pv1", "primary_spdx": "Apache-2.0"})
    store.flush()
    lines = path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    assert json.loads(lines[0])["primary_spdx"] == "Apache-2.0"
