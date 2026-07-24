"""Unit tests for runtime path containment helpers."""

from __future__ import annotations

from pathlib import Path

import pytest

from endorlabs.utils.path_safety import safe_write_bytes, safe_write_text


def test_safe_write_text_writes_inside_base(tmp_path: Path) -> None:
    target = tmp_path / "out" / "note.txt"
    safe_write_text(tmp_path, target, "hello")
    assert target.read_text(encoding="utf-8") == "hello"


def test_safe_write_text_rejects_escape(tmp_path: Path) -> None:
    base = tmp_path / "base"
    base.mkdir()
    outside = tmp_path / "outside.txt"
    with pytest.raises(ValueError, match="outside base directory"):
        safe_write_text(base, outside, "nope")


def test_safe_write_bytes_writes_inside_base(tmp_path: Path) -> None:
    target = tmp_path / "bin" / "data.bin"
    safe_write_bytes(tmp_path, target, b"\x00\x01")
    assert target.read_bytes() == b"\x00\x01"
