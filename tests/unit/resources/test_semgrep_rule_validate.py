"""Unit tests for Semgrep rule payload validation helpers."""

from endorlabs.resources.semgrep_rule import (
    CreateSemgrepRulePayload,
    SemgrepNativeRule,
    SemgrepRuleMetaCreate,
    SemgrepRuleSpec,
    validate_semgrep_rule,
)


def test_validate_semgrep_rule_accepts_hyphenated_pattern_either() -> None:
    """YAML ``pattern-either`` lands in model_extra and must still validate."""
    rule_dict = {
        "id": "endor.test.compound",
        "languages": ["python"],
        "severity": "WARNING",
        "message": "test compound rule",
        "pattern-either": [
            {"pattern": "bad()"},
            {"pattern": "worse()"},
        ],
    }
    native = SemgrepNativeRule.model_validate(rule_dict)
    payload = CreateSemgrepRulePayload(
        meta=SemgrepRuleMetaCreate(name=rule_dict["id"], description="test"),
        spec=SemgrepRuleSpec(rule=native, yaml="rules:\n  - ..."),
    )

    ok, errors = validate_semgrep_rule(payload, validate_yaml=False)

    assert ok is True
    assert errors == []
