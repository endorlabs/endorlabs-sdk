"""Unit tests for sync CLI helpers."""
# pyright: reportMissingImports=false

from __future__ import annotations

import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[4]
_SCRIPTS_DIR = str(_REPO_ROOT / "scripts")
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)

from sync.cli import (
    DEFAULT_CUSTOM_PROFILES_DIR,
    DEFAULT_OUTPUT_ROOT,
    DEFAULT_SPEC_PATH,
    build_parser,
    main,
)
from sync.codegen import _build_codegen_command, load_profiles
from sync.provenance import write_json


def test_build_parser_has_expected_flags() -> None:
    parser = build_parser()
    args = parser.parse_args([])
    assert args.spec_path == DEFAULT_SPEC_PATH
    assert args.output_root == DEFAULT_OUTPUT_ROOT
    assert args.custom_profiles_dir == DEFAULT_CUSTOM_PROFILES_DIR
    assert hasattr(args, "generate_stubs")
    assert hasattr(args, "generate_reference_docs")
    assert hasattr(args, "inventory_only")


def test_main_forwards_parser_args_to_run_sync(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def _fake_run_sync(**kwargs: object) -> int:
        captured.update(kwargs)
        return 7

    import sync.cli as sync_cli_module

    monkeypatch.setattr(sync_cli_module, "run_sync", _fake_run_sync)

    result = main(
        [
            "--spec-path",
            "spec.json",
            "--output-root",
            "out",
            "--custom-profiles-dir",
            "profiles",
            "--generate-stubs",
            "--generate-reference-docs",
        ]
    )

    assert result == 7
    assert captured["spec_path"] == Path("spec.json")
    assert captured["output_root"] == Path("out")
    assert captured["profiles_dir"] == Path("profiles")
    assert captured["generate_stubs"] is True
    assert captured["generate_reference_docs"] is True


def test_main_inventory_only_writes_toolchain_inventory(tmp_path: Path) -> None:
    output_root = tmp_path / "sync-output"
    result = main(["--inventory-only", "--output-root", str(output_root)])
    inventory_path = output_root / "toolchain_inventory.json"
    assert result == 0
    assert inventory_path.exists()
    data = json.loads(inventory_path.read_text(encoding="utf-8"))
    assert "datamodel-codegen" in data
    assert "path" not in data["datamodel-codegen"]
    assert "available" in data["datamodel-codegen"]


def test_build_codegen_command_uses_repo_relative_posix_paths(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    cm = repo_root / "workspace" / "model-sync" / "custom_mapping"
    input_path = cm / "schema_shards" / "a.json"
    output_file = cm / "generated" / "a.py"
    input_path.parent.mkdir(parents=True)
    output_file.parent.mkdir(parents=True)
    input_path.write_text("{}", encoding="utf-8")
    cmd = _build_codegen_command(repo_root, input_path, output_file)
    want_in = "workspace/model-sync/custom_mapping/schema_shards/a.json"
    want_out = "workspace/model-sync/custom_mapping/generated/a.py"
    assert cmd[2].replace("\\", "/") == want_in
    assert cmd[6].replace("\\", "/") == want_out


def test_load_profiles_marks_missing_files(tmp_path: Path) -> None:
    profiles = load_profiles(tmp_path)
    assert profiles["aliases.json"]["missing"] is True
    assert profiles["partition_rules.json"]["missing"] is True


def test_write_json_is_stable(tmp_path: Path) -> None:
    output = tmp_path / "out.json"
    write_json(output, {"b": 2, "a": 1})
    loaded = json.loads(output.read_text(encoding="utf-8"))
    assert loaded == {"a": 1, "b": 2}
