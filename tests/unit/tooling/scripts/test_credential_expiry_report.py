"""Unit tests for credential expiry report script helpers."""

from __future__ import annotations

import sys
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from types import ModuleType

from endorlabs.workflows.auth.credential_expiry import CredentialExpiryRow


def _load_module() -> ModuleType:
    repo_root = Path(__file__).resolve().parents[4]
    candidate_paths = (
        repo_root
        / "agent-knowledge"
        / "skills"
        / "endor-auth-credential-expiry"
        / "scripts"
        / "credential_expiry_report.py",
        repo_root
        / "src"
        / "endorlabs"
        / "agent_knowledge"
        / "skills"
        / "endor-auth-credential-expiry"
        / "scripts"
        / "credential_expiry_report.py",
    )
    script_path = next(path for path in candidate_paths if path.is_file())
    spec = spec_from_file_location("credential_expiry_report", script_path)
    assert spec is not None
    assert spec.loader is not None
    module = module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_csv_fieldnames_match_skill_schema() -> None:
    module = _load_module()
    assert module._csv_fieldnames() == [
        "kind",
        "name",
        "namespace",
        "uuid",
        "key id",
        "expiration time",
        "status",
        "days until expiry",
        "propagate",
        "issuing user",
    ]


def test_write_credential_expiry_csv_round_trip(tmp_path: Path) -> None:
    module = _load_module()
    output = tmp_path / "credential-expiry.csv"
    rows = [
        CredentialExpiryRow(
            kind="APIKey",
            name="ci-readonly",
            namespace="tenant.child",
            uuid="key-uuid",
            key_id="key-id-123",
            expiration_time="2026-07-20T00:00:00Z",
            status="expiring_soon",
            days_until_expiry=11,
            propagate=True,
            issuing_user="automation@example.com",
        )
    ]
    module.write_credential_expiry_csv(rows, output)
    text = output.read_text(encoding="utf-8")
    assert "kind,name,namespace,uuid,key id,expiration time,status" in text
    assert "ci-readonly" in text
    assert "expiring_soon" in text


def test_build_summary_counts_status_buckets() -> None:
    module = _load_module()
    rows = [
        CredentialExpiryRow(
            kind="APIKey",
            name="old",
            namespace="tenant",
            uuid="1",
            key_id="k1",
            expiration_time="2026-01-01T00:00:00Z",
            status="expired",
            days_until_expiry=-10,
            propagate=False,
            issuing_user="",
        ),
        CredentialExpiryRow(
            kind="APIKey",
            name="soon",
            namespace="tenant",
            uuid="2",
            key_id="k2",
            expiration_time="2026-07-20T00:00:00Z",
            status="expiring_soon",
            days_until_expiry=12,
            propagate=False,
            issuing_user="",
        ),
    ]
    summary = module.build_summary(
        "tenant",
        within_days=30,
        rows=rows,
        raw_row_count=5,
    )
    assert summary["tenant"] == "tenant"
    assert summary["expired_count"] == 1
    assert summary["expiring_soon_count"] == 1
    assert summary["raw_api_keys_listed"] == 5
