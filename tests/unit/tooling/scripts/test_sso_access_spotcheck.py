"""SSO spot-check script remains a thin CLI (library owns mapping helpers)."""

from __future__ import annotations

import sys
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from types import ModuleType

from endorlabs.workflows.auth import build_claim_namespace_map, expand_namespace_scope


def _load_spotcheck_module() -> ModuleType:
    repo_root = Path(__file__).resolve().parents[4]
    candidate_paths = (
        repo_root
        / "agent-knowledge"
        / "skills"
        / "endor-sso-integration-validation-troubleshooting"
        / "sso_access_spotcheck.py",
        repo_root
        / "src"
        / "endorlabs"
        / "agent_knowledge"
        / "skills"
        / "endor-sso-integration-validation-troubleshooting"
        / "sso_access_spotcheck.py",
        repo_root
        / ".cursor"
        / "skills"
        / "endor-sso-integration-validation-troubleshooting"
        / "sso_access_spotcheck.py",
    )
    script_path = next(path for path in candidate_paths if path.is_file())
    spec = spec_from_file_location("sso_access_spotcheck", script_path)
    assert spec is not None
    assert spec.loader is not None
    module = module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_library_expand_namespace_scope() -> None:
    scope = expand_namespace_scope(["root.A"], propagate=True)
    assert scope.direct_namespaces == ["root.A"]
    assert scope.propagated_namespace_prefixes == ["root.A.*"]


def test_library_build_claim_namespace_map_detects_overlap() -> None:
    report = build_claim_namespace_map(
        [
            {
                "name": "policy-a",
                "clause": ["group=eng-a"],
                "target_namespaces": ["root.A"],
                "propagate": False,
            },
            {
                "name": "policy-b",
                "clause": ["group=eng-b"],
                "target_namespaces": ["root.A", "root.B"],
                "propagate": False,
            },
        ]
    )
    assert "root.A" in report.overlap.direct_namespace_to_claim_keys


def test_spotcheck_script_imports_library() -> None:
    module = _load_spotcheck_module()
    assert callable(module.main)
    assert "list_authorization_policies" in module.__dict__ or hasattr(
        module, "list_authorization_policies"
    )
