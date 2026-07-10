"""AuthPolicy form-audit script remains a thin CLI (library owns heuristics)."""

from __future__ import annotations

from endorlabs.workflows.auth import audit_target_namespaces


def test_library_comma_blob_still_flagged() -> None:
    findings = audit_target_namespaces(
        policy_uuid=None,
        policy_name="p",
        target_namespaces=["a.b, a.c"],
    )
    assert any(f.code == "comma_separated_namespace_blob" for f in findings)
