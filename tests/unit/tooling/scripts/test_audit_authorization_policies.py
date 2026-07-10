"""AuthPolicy form-audit script remains a thin CLI (library owns heuristics)."""

from __future__ import annotations

import sys
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from types import ModuleType

from endorlabs.workflows.auth import audit_target_namespaces


def _load_audit_module() -> ModuleType:
    repo_root = Path(__file__).resolve().parents[4]
    script_path = (
        repo_root
        / "agent-knowledge"
        / "workflow-reports"
        / "endor-audit-authorization-policies"
        / "scripts"
        / "audit_authorization_policies.py"
    )
    assert script_path.is_file(), script_path
    spec = spec_from_file_location("audit_authorization_policies", script_path)
    assert spec is not None
    assert spec.loader is not None
    module = module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_library_comma_blob_still_flagged() -> None:
    findings = audit_target_namespaces(
        policy_uuid=None,
        policy_name="p",
        target_namespaces=["a.b, a.c"],
    )
    assert any(f.code == "comma_separated_namespace_blob" for f in findings)


def test_audit_script_is_thin_cli() -> None:
    module = _load_audit_module()
    assert callable(module.main)
    assert hasattr(module, "list_authorization_policies")
    assert hasattr(module, "audit_authorization_policy_forms")
