"""Tests for codegen filter enum reference."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
_CODEGEN = REPO_ROOT / "devtools" / "codegen"
if str(_CODEGEN) not in sys.path:
    sys.path.insert(0, str(_CODEGEN))


def test_render_filter_enum_snippets_contains_key_values() -> None:
    from doc_facade_helpers import render_filter_enum_snippets_md
    from endorlabs.generated.models.finding_service import SpecFindingLevel
    from endorlabs.generated.models.scan_result_service import ScanResultSpecStatus

    md = render_filter_enum_snippets_md()
    assert "STATUS_SUCCESS" in md
    assert "FINDING_LEVEL_CRITICAL" in md
    assert "generated" in md.lower()
    assert md.count("| `STATUS_") == len(list(ScanResultSpecStatus))
    assert md.count("| `FINDING_LEVEL_") == len(list(SpecFindingLevel))


def test_generate_filter_enum_reference_cli_writes_file(tmp_path: Path) -> None:
    out = tmp_path / "docs" / "generated-reference" / "filter-enum-snippets.md"
    script = REPO_ROOT / "devtools" / "codegen" / "generate_filter_enum_reference.py"
    # Run from a temp tree: patch output by setting cwd isn't enough; call render directly.
    from doc_facade_helpers import render_filter_enum_snippets_md

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render_filter_enum_snippets_md(), encoding="utf-8")
    assert "FINDING_LEVEL_CRITICAL" in out.read_text(encoding="utf-8")

    result = subprocess.run(
        [sys.executable, str(script)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr or result.stdout
    committed = REPO_ROOT / "docs" / "generated-reference" / "filter-enum-snippets.md"
    assert committed.is_file()
    assert "STATUS_SUCCESS" in committed.read_text(encoding="utf-8")
