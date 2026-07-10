"""Unit tests for sync CLI helpers."""
# pyright: reportMissingImports=false

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[4]
_DEVTOOLS_DIR = str(_REPO_ROOT / "devtools" / "codegen")
if _DEVTOOLS_DIR not in sys.path:
    sys.path.insert(0, _DEVTOOLS_DIR)

from sync.cli import (
    default_custom_profiles_dir,
    default_spec_path,
    main,
)
from sync.codegen import load_profiles
from sync.provenance import write_json


def test_main_forwards_parser_args_to_run_sync(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def _fake_run_sync(**kwargs: object) -> int:
        captured.update(kwargs)
        return 7

    import sync.cli as sync_cli_module

    monkeypatch.setattr(sync_cli_module, "run_sync", _fake_run_sync)

    profiles = _REPO_ROOT / "profiles"
    result = main(
        [
            "--custom-profiles-dir",
            str(profiles),
            "--generate-stubs",
            "--generate-reference-docs",
        ]
    )

    assert result == 7
    assert captured["profiles_dir"] == profiles
    assert captured["generate_stubs"] is True
    assert captured["generate_reference_docs"] is True


def test_main_inventory_only_logs_toolchain(monkeypatch, caplog) -> None:
    import logging

    caplog.set_level(logging.INFO)

    result = main(["--inventory-only"])
    assert result == 0
    assert any("Toolchain inventory" in record.message for record in caplog.records)


def test_datamodel_code_generator_importable() -> None:
    assert importlib.util.find_spec("datamodel_code_generator") is not None


def test_load_profiles_marks_missing_files(tmp_path: Path) -> None:
    profiles = load_profiles(tmp_path)
    assert profiles["aliases.json"]["missing"] is True
    assert profiles["partition_rules.json"]["missing"] is True


def test_write_json_is_stable(tmp_path: Path) -> None:
    output = tmp_path / "out.json"
    write_json(output, {"b": 2, "a": 1})
    loaded = json.loads(output.read_text(encoding="utf-8"))
    assert loaded == {"a": 1, "b": 2}


def test_default_paths_under_repo_root() -> None:
    assert default_spec_path(_REPO_ROOT).is_relative_to(_REPO_ROOT)
    assert default_custom_profiles_dir(_REPO_ROOT).is_relative_to(_REPO_ROOT)
