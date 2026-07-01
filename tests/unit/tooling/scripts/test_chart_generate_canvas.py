"""Unit tests for new-vs-resolved chart canvas generation."""

from __future__ import annotations

import json
import sys
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from types import ModuleType


def _load_module() -> ModuleType:
    repo_root = Path(__file__).resolve().parents[4]
    candidate_paths = (
        repo_root
        / "agent-knowledge"
        / "skills"
        / "endor-chart-new-vs-resolved-findings"
        / "scripts"
        / "generate_canvas.py",
        repo_root
        / "src"
        / "endorlabs"
        / "agent_knowledge"
        / "skills"
        / "endor-chart-new-vs-resolved-findings"
        / "scripts"
        / "generate_canvas.py",
    )
    script_path = next(path for path in candidate_paths if path.is_file())
    scripts_dir = str(script_path.parent)
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)
    spec = spec_from_file_location("chart_generate_canvas", script_path)
    assert spec is not None
    assert spec.loader is not None
    module = module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_render_canvas_from_fixture() -> None:
    module = _load_module()
    fixture = (
        Path(__file__).resolve().parents[3]
        / "fixtures"
        / "chart"
        / "new_vs_resolved_analysis_min.json"
    )
    data = json.loads(fixture.read_text(encoding="utf-8"))
    tsx = module.render_canvas(data)

    assert "TenantAcmeCumulativeWeeklyTrend" in tsx
    assert "Cumulative New vs Resolved Reachable Vulnerabilities" in tsx
    assert "tenant_acme" in tsx
    assert "through week of" in tsx and "01/11" in tsx
    assert '"widening"' in tsx or "widening" in tsx


def test_render_canvas_rejects_invalid_payload() -> None:
    module = _load_module()
    try:
        module.render_canvas({"namespace": "tenant"})
    except ValueError as exc:
        assert "missing keys" in str(exc)
    else:
        raise AssertionError("expected ValueError for invalid chart JSON")
