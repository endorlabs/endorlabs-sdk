"""Unit tests for PRF analysis pure helpers."""

from __future__ import annotations

import sys
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from types import ModuleType


def _load_module() -> ModuleType:
    repo_root = Path(__file__).resolve().parents[4]
    script_path = (
        repo_root
        / "agent-knowledge"
        / "workflow-reports"
        / "endor-potentially-reachable-analysis"
        / "scripts"
        / "run_analysis.py"
    )
    assert script_path.is_file(), script_path
    spec = spec_from_file_location("prf_run_analysis", script_path)
    assert spec is not None
    assert spec.loader is not None
    module = module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_parse_best_match_defaults() -> None:
    module = _load_module()
    match = module.parse_best_match(None)
    assert match["matching_rule"] == "no best match"


def test_has_dep_resolution_errors() -> None:
    module = _load_module()
    pv = {"spec": {"resolution_errors": {"unresolved": {"x": 1}}}}
    assert module.has_dep_resolution_errors(pv) is True
    assert module.has_dep_resolution_errors({"spec": {}}) is False


def test_findings_by_parent_counts() -> None:
    module = _load_module()
    findings = [
        {"meta": {"parent_uuid": "pv-1"}},
        {"meta": {"parent_uuid": "pv-1"}},
        {"meta": {}},
    ]
    counts = module.findings_by_parent(findings)
    assert counts["pv-1"] == 2
