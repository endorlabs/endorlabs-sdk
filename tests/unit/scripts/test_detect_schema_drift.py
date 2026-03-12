"""Unit tests for schema drift workflow script."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType


def _load_detect_schema_drift_module() -> ModuleType:
    """Load .github/scripts/detect_schema_drift.py as a module."""
    repo_root = Path(__file__).resolve().parents[3]
    script_path = repo_root / ".github" / "scripts" / "detect_schema_drift.py"
    spec = importlib.util.spec_from_file_location("detect_schema_drift", script_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load script module from {script_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_parse_drift_warnings_supports_canonical_and_legacy_formats(
    tmp_path: Path,
) -> None:
    module = _load_detect_schema_drift_module()
    detector = module.SchemaDriftDetector(
        output_file=str(tmp_path / "drift_report.json")
    )

    output = (
        "INFO API Schema Drift Detected in Finding.FindingSpec.spec: "
        "Unknown fields found: epsilon, zeta. Context: list.\n"
        "WARNING Schema drift detected in ProjectSpec.spec: "
        "unknown fields {'theta', 'iota'}\n"
    )
    drifts = detector._parse_drift_warnings(output)
    keys = {d["drift_key"] for d in drifts}
    assert "Finding|FindingSpec.spec|epsilon" in keys
    assert "Finding|FindingSpec.spec|zeta" in keys
    assert "Project|ProjectSpec.spec|theta" in keys
    assert "Project|ProjectSpec.spec|iota" in keys


def test_generate_report_writes_expected_contract(tmp_path: Path) -> None:
    module = _load_detect_schema_drift_module()
    output_file = tmp_path / "schema_drift_report.json"
    detector = module.SchemaDriftDetector(output_file=str(output_file))

    test_results = {
        "drifts": [
            {
                "drift_key": "Project|ProjectSpec.spec|new_field",
                "field_path": "ProjectSpec.spec.new_field",
                "resource_name": "Project",
                "model_path": "ProjectSpec.spec",
                "model": "ProjectSpec",
                "field": "new_field",
                "file_path": "src/endorlabs/resources/project.py",
                "nested_depth": 1,
                "first_seen": "2026-01-01T00:00:00+00:00",
                "status": "new",
                "issue_number": None,
            }
        ],
        "validation_errors": [],
        "test_exit_code": 0,
    }
    report = detector.generate_report(test_results)
    assert output_file.exists()
    assert report["summary"]["new_drifts"] == 1
    assert report["summary"]["test_status"] == "passed"
    assert report["drifts"][0]["drift_key"] == "Project|ProjectSpec.spec|new_field"
    assert report["drifts"][0]["status"] == "new"


def test_parse_drift_warnings_supports_multiline_and_noise(tmp_path: Path) -> None:
    module = _load_detect_schema_drift_module()
    detector = module.SchemaDriftDetector(
        output_file=str(tmp_path / "drift_report_multiline.json")
    )

    output = (
        "random prefix line\n"
        "INFO API Schema Drift Detected in Policy.PolicySpec.spec:\n"
        "Unknown fields found: alpha, beta.\n"
        "Context: read path\n"
        "This may indicate API evolution or missing model fields.\n"
        "WARNING Schema drift detected in NamespaceSpec.spec: "
        "unknown fields {'gamma': 1, 'delta': 2}\n"
        "random suffix line\n"
    )
    drifts = detector._parse_drift_warnings(output)
    keys = {d["drift_key"] for d in drifts}
    assert "Policy|PolicySpec.spec|alpha" in keys
    assert "Policy|PolicySpec.spec|beta" in keys
    assert "Namespace|NamespaceSpec.spec|gamma" in keys
    assert "Namespace|NamespaceSpec.spec|delta" in keys
