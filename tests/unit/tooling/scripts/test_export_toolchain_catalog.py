"""Unit tests for toolchain catalog CSV flatten/write (no live API)."""

from __future__ import annotations

import csv
import importlib.util
import io
from pathlib import Path
from types import ModuleType

_FIXTURE = [
    {
        "uuid": "abc",
        "spec": {
            "os": "linux",
            "arch": "amd64",
            "toolchain": "golang",
            "default": True,
            "version": {
                "is_default": True,
                "version": {
                    "name": "1.24.6",
                    "relative_tool_chain_path": "go",
                    "sha256_sum": "deadbeef",
                    "urls": [
                        "https://example.com/dl/go1.24.6.linux-amd64.tar.gz",
                        "https://example.com/mirror/go1.24.6.linux-amd64.tar.gz",
                    ],
                },
            },
        },
    },
    {
        "spec": {
            "os": {"value": "darwin"},
            "arch": {"value": "arm64"},
            "toolchain": {"value": "maven"},
            "version": {
                "version": {
                    "name": {"value": "3.9.4"},
                    "relative_tool_chain_path": {"value": "apache-maven-3.9.4"},
                    "sha256_sum": {"value": "cafebabe"},
                    "urls": [],
                },
            },
        },
    },
]


def _load_export_module() -> ModuleType:
    root = Path(__file__).resolve().parents[4]
    candidate_paths = (
        root
        / "agent-knowledge"
        / "skills"
        / "endor-toolchain-catalog"
        / "scripts"
        / "export_toolchain_catalog.py",
        root
        / "src"
        / "endorlabs"
        / "agent_knowledge"
        / "skills"
        / "endor-toolchain-catalog"
        / "scripts"
        / "export_toolchain_catalog.py",
        root
        / ".cursor"
        / "skills"
        / "endor-toolchain-catalog"
        / "scripts"
        / "export_toolchain_catalog.py",
    )
    script_path = next(path for path in candidate_paths if path.is_file())
    spec = importlib.util.spec_from_file_location(
        "export_toolchain_catalog_for_test", script_path
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_flatten_one_row_per_url_and_blank_when_empty() -> None:
    mod = _load_export_module()
    rows = mod.flatten_catalog_rows(_FIXTURE)
    assert len(rows) == 3
    assert rows[0] == {
        "os": "linux",
        "arch": "amd64",
        "ecosystem": "golang",
        "name": "1.24.6",
        "relative_tool_chain_path": "go",
        "sha256_sum": "deadbeef",
        "url": "https://example.com/dl/go1.24.6.linux-amd64.tar.gz",
    }
    assert rows[1]["url"] == "https://example.com/mirror/go1.24.6.linux-amd64.tar.gz"
    assert rows[2] == {
        "os": "darwin",
        "arch": "arm64",
        "ecosystem": "maven",
        "name": "3.9.4",
        "relative_tool_chain_path": "apache-maven-3.9.4",
        "sha256_sum": "cafebabe",
        "url": "",
    }


def test_flatten_omits_catalog_metadata_keys() -> None:
    mod = _load_export_module()
    rows = mod.flatten_catalog_rows(_FIXTURE)
    for row in rows:
        assert set(row) == set(mod.CSV_COLUMNS)
        assert "uuid" not in row
        assert "default" not in row
        assert "is_default" not in row


def test_write_csv_header_and_rows() -> None:
    mod = _load_export_module()
    rows = mod.flatten_catalog_rows(_FIXTURE)
    buf = io.StringIO()
    count = mod.write_csv(rows, buf)
    assert count == 3
    buf.seek(0)
    reader = csv.DictReader(buf)
    assert reader.fieldnames == list(mod.CSV_COLUMNS)
    written = list(reader)
    assert len(written) == 3
    assert written[0]["ecosystem"] == "golang"
    assert written[2]["url"] == ""
