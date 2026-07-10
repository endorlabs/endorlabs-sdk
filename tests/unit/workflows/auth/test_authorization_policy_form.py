"""Unit tests for AuthorizationPolicy form-audit heuristics."""

from __future__ import annotations

from endorlabs.workflows.auth.authorization_policy_form import (
    audit_clause,
    audit_policy_record,
    audit_target_namespaces,
)


def test_comma_separated_namespace_blob() -> None:
    blob = (
        "doordash.doordash-github-creditornot, "
        "doordash.doordash-github-doordash, "
        "doordash.doordash-github-roo"
    )
    findings = audit_target_namespaces(
        policy_uuid="u1",
        policy_name="p1",
        target_namespaces=[blob],
    )
    assert any(f.code == "comma_separated_namespace_blob" for f in findings)
    assert findings[0].severity == "critical"
    assert "doordash.doordash-github-roo" in findings[0].suggestion


def test_good_target_namespaces_ok() -> None:
    findings = audit_target_namespaces(
        policy_uuid=None,
        policy_name="p",
        target_namespaces=[
            "doordash.doordash-github-creditornot",
            "doordash.doordash-github-doordash",
        ],
    )
    assert findings == []


def test_double_provider_suffix() -> None:
    findings = audit_clause(
        policy_uuid=None,
        policy_name="p",
        clause=["user=timmy166@gitlab@gitlab", "gitlab"],
    )
    assert any(f.code == "double_provider_suffix" for f in findings)


def test_good_gitlab_clause_ok() -> None:
    findings = audit_clause(
        policy_uuid=None,
        policy_name="p",
        clause=["user=timmy166@gitlab", "gitlab"],
    )
    assert not any(f.severity == "critical" for f in findings)


def test_audit_policy_record_aggregates() -> None:
    findings = audit_policy_record(
        {
            "uuid": "x",
            "name": "bad",
            "clause": ["user=a@gitlab@gitlab", "gitlab"],
            "target_namespaces": ["a.b, a.c"],
        }
    )
    codes = {f.code for f in findings}
    assert "comma_separated_namespace_blob" in codes
    assert "double_provider_suffix" in codes
