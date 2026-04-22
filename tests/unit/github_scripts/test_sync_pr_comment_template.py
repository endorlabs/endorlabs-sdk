"""Unit tests for .github/scripts/sync_pr_comment_template.py."""

from __future__ import annotations

import sys
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parents[3] / ".github" / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

import sync_pr_comment_template as sync_template


def test_report_failure_hides_exception_details(capsys: object) -> None:
    code = sync_template._report_failure(
        console_message="Template sync failed creating client.",
        status_reason="client_init",
    )
    err = capsys.readouterr().err
    assert code == 1
    assert "Template sync failed creating client." in err
    assert "sensitive" not in err
