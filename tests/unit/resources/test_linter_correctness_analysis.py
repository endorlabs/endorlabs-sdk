"""LinterResult nested correctness analysis wire tolerance."""

from __future__ import annotations

from endorlabs.resources.linter_result import LinterResultSpec


def test_linter_correctness_analysis_openapi_shape() -> None:
    spec = LinterResultSpec.model_validate(
        {
            "project_uuid": "proj-1",
            "origin": "LINTER_RESULT_ORIGIN_SEMGREP",
            "extra_key": "k",
            "linter_correctness_analyses": [
                {
                    "version": "1",
                    "analyzer": "CORRECTNESS_ANALYZER_AI_GEMINI_FLASH_2_5",
                    "correctness": "CORRECTNESS_TRUE_POSITIVE",
                    "confidence_level": "CONFIDENCE_LEVEL_HIGH",
                    "analysis_summary": "likely true positive",
                }
            ],
        }
    )
    assert spec.linter_correctness_analyses is not None
    row = spec.linter_correctness_analyses[0]
    assert row.version == "1"
    assert row.correctness == "CORRECTNESS_TRUE_POSITIVE"


def test_linter_correctness_analysis_partial_list_row() -> None:
    """List payloads may omit nested required OpenAPI fields."""
    spec = LinterResultSpec.model_validate(
        {
            "project_uuid": "proj-1",
            "origin": "LINTER_RESULT_ORIGIN_SEMGREP",
            "extra_key": "k",
            "linter_correctness_analyses": [{"analysis_summary": "incomplete row"}],
        }
    )
    assert spec.linter_correctness_analyses is not None
    assert spec.linter_correctness_analyses[0].analysis_summary == "incomplete row"


def test_linter_correctness_analysis_extra_allow_legacy_keys() -> None:
    """Unknown nested keys are retained via extra=allow (not required OpenAPI fields)."""
    spec = LinterResultSpec.model_validate(
        {
            "project_uuid": "proj-1",
            "origin": "LINTER_RESULT_ORIGIN_SEMGREP",
            "extra_key": "k",
            "linter_correctness_analyses": [
                {"analysis_type": "taint", "result": "pass", "confidence": 0.9}
            ],
        }
    )
    row = spec.linter_correctness_analyses
    assert row is not None
    assert row[0].model_extra == {
        "analysis_type": "taint",
        "result": "pass",
        "confidence": 0.9,
    }
