"""Unit tests for SSO access spot-check mapping helpers."""

from __future__ import annotations

import sys
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from types import ModuleType


def _load_spotcheck_module() -> ModuleType:
    repo_root = Path(__file__).resolve().parents[4]
    script_path = (
        repo_root
        / ".cursor"
        / "skills"
        / "sso-integration-validation-troubleshooting"
        / "sso_access_spotcheck.py"
    )
    spec = spec_from_file_location("sso_access_spotcheck", script_path)
    assert spec is not None
    assert spec.loader is not None
    module = module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_expand_namespace_scope_without_propagation() -> None:
    module = _load_spotcheck_module()

    scope = module.expand_namespace_scope(["root"], propagate=False)

    assert scope.direct_namespaces == ["root"]
    assert scope.propagated_namespace_prefixes == []


def test_expand_namespace_scope_with_propagation() -> None:
    module = _load_spotcheck_module()

    scope = module.expand_namespace_scope(["root.A"], propagate=True)

    assert scope.direct_namespaces == ["root.A"]
    assert scope.propagated_namespace_prefixes == ["root.A.*"]


def test_build_claim_namespace_map_detects_overlap() -> None:
    module = _load_spotcheck_module()

    policies = [
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

    report = module.build_claim_namespace_map(policies)

    assert "group=eng-a" in report.claims
    assert "group=eng-b" in report.claims
    assert "root.A" in report.overlap.direct_namespace_to_claim_keys
    assert set(report.overlap.direct_namespace_to_claim_keys["root.A"]) == {
        "group=eng-a",
        "group=eng-b",
    }
