"""Tests for wheel packaging verification gate."""

from __future__ import annotations

import json
import sys
import zipfile
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[4]
SHIP_DIR = REPO_ROOT / "devtools" / "ship"
if str(SHIP_DIR) not in sys.path:
    sys.path.insert(0, str(SHIP_DIR))

import verify_wheel_contents as wheel_verify  # noqa: E402

DIST_DIR = REPO_ROOT / "dist"


def test_verify_source_packaging_invariants_passes_on_repo_tree() -> None:
    errors = wheel_verify.verify_source_packaging_invariants()
    assert errors == []


def test_verify_estate_init_files_detects_missing_marker(tmp_path: Path) -> None:
    estate_root = tmp_path / "estate"
    module_dir = estate_root / "analyze" / "cardinality"
    module_dir.mkdir(parents=True)
    (module_dir / "export.py").write_text("x = 1\n", encoding="utf-8")
    errors = wheel_verify.verify_package_init_files(estate_root, "estate")
    assert errors
    assert any("analyze" in msg and "__init__.py" in msg for msg in errors)


def test_verify_wheel_archive_paths_requires_analyze_and_manifest(
    tmp_path: Path,
) -> None:
    manifest = wheel_verify.load_manifest()
    wheel_path = tmp_path / "empty.whl"
    with zipfile.ZipFile(wheel_path, "w") as archive:
        archive.writestr(
            "endorlabs/agent_knowledge/MANIFEST.json",
            json.dumps(manifest),
        )
    errors = wheel_verify.verify_wheel_archive_paths(wheel_path, manifest)
    assert any("estate/analyze" in msg for msg in errors)


@pytest.mark.skipif(
    not any(DIST_DIR.glob("endorlabs-*.whl")),
    reason="built wheel not present; run uv build first",
)
def test_built_wheel_passes_archive_path_check() -> None:
    wheel_path = wheel_verify.find_wheel(DIST_DIR, None)
    errors = wheel_verify.verify_wheel_archive_paths(
        wheel_path, wheel_verify.load_manifest()
    )
    assert errors == []
