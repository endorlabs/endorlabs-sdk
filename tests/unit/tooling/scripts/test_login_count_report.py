"""Unit tests for login count report script helpers."""

from __future__ import annotations

import sys
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from types import ModuleType

from endorlabs.workflows.auth.authentication_log import LoginActivityRow


def _load_module() -> ModuleType:
    repo_root = Path(__file__).resolve().parents[4]
    candidate_paths = (
        repo_root
        / "agent-knowledge"
        / "skills"
        / "endor-auth-login-count"
        / "scripts"
        / "login_count_report.py",
        repo_root
        / "src"
        / "endorlabs"
        / "agent_knowledge"
        / "skills"
        / "endor-auth-login-count"
        / "scripts"
        / "login_count_report.py",
    )
    script_path = next(path for path in candidate_paths if path.is_file())
    spec = spec_from_file_location("login_count_report", script_path)
    assert spec is not None
    assert spec.loader is not None
    module = module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_csv_fieldnames_include_days() -> None:
    module = _load_module()
    assert module._csv_fieldnames(7) == [
        "identity",
        "user identifiers",
        "last login",
        "login count in 7 days",
    ]


def test_write_login_count_csv_round_trip(tmp_path: Path) -> None:
    module = _load_module()
    output = tmp_path / "login-count.csv"
    activity = [
        LoginActivityRow(
            identity="user2@example.com",
            user_identifiers=(
                "email=user2@example.com",
                "id=12345",
            ),
            last_login="2026-07-07T15:13:55.374Z",
            login_count=9,
            days=7,
        )
    ]
    module.write_login_count_csv(activity, output, days=7)
    text = output.read_text(encoding="utf-8")
    assert "identity,user identifiers,last login,login count in 7 days" in text
    assert "user2@example.com" in text
    assert ",9" in text


def test_build_summary_includes_identity_count() -> None:
    module = _load_module()
    activity = [
        LoginActivityRow(
            identity="user@example.com",
            user_identifiers=("email=user@example.com",),
            last_login="2026-07-03T07:47:45.743Z",
            login_count=9,
            days=7,
        )
    ]
    summary = module.build_summary(
        "example-tenant",
        days=7,
        activity=activity,
        raw_row_count=159,
    )
    assert summary["tenant"] == "example-tenant"
    assert summary["identity_count"] == 1
    assert summary["total_login_events"] == 9
    assert summary["raw_rows_after_filters"] == 159
