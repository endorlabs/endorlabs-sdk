"""Unit tests for experimental.workflows.semgrep_management."""

from pathlib import Path
from unittest.mock import Mock

from endorlabs.experimental.workflows.semgrep_management import (
    ImportResult,
    _parse_yaml_file,
    _rule_display_id,
    _wrap_yaml,
    calibrate_rules,
    export_rules_to_yaml,
    import_rules_from_yaml,
    is_ai_model_rule,
)

# ---------------------------------------------------------------------------
# is_ai_model_rule (pure domain logic — most important to test)
# ---------------------------------------------------------------------------


def _make_rule(
    *,
    rule_id: str | None = None,
    name: str | None = None,
    endor_targets: list[str] | None = None,
    category: str | None = None,
    subcategory: list[str] | None = None,
    description: str | None = None,
    message: str | None = None,
    technology: list[str] | None = None,
    defined_by: str | None = None,
    disabled: bool = False,
) -> Mock:
    """Build a mock SemgrepRule for classification tests."""
    rule = Mock()
    rule.uuid = "rule-uuid"
    rule.disabled = disabled
    rule.meta.name = name

    native = Mock()
    native.id = rule_id
    native.message = message

    meta = Mock()
    meta.endor_targets = endor_targets
    meta.category = category
    meta.subcategory = subcategory
    meta.description = description
    meta.technology = technology
    native.metadata = meta

    rule.spec.rule = native
    rule.spec.defined_by = defined_by
    rule.spec.disabled = disabled
    rule.spec.yaml = None

    return rule


class TestIsAiModelRule:
    """Tests for is_ai_model_rule classification."""

    def test_by_endor_targets(self) -> None:
        rule = _make_rule(endor_targets=["ECOSYSTEM_AI_MODEL"])
        assert is_ai_model_rule(rule) is True

    def test_by_rule_id_ai_model(self) -> None:
        rule = _make_rule(rule_id="py-ai_model-detect-openai")
        assert is_ai_model_rule(rule) is True

    def test_by_rule_id_detect_pattern(self) -> None:
        rule = _make_rule(rule_id="py-detect-openai-models")
        assert is_ai_model_rule(rule) is True

    def test_by_rule_id_detect_anthropic(self) -> None:
        rule = _make_rule(rule_id="js-detect-anthropic-models")
        assert is_ai_model_rule(rule) is True

    def test_by_name_ai_model(self) -> None:
        rule = _make_rule(name="AI Model Detection Rule")
        assert is_ai_model_rule(rule) is True

    def test_by_category(self) -> None:
        rule = _make_rule(category="AI Model Security")
        assert is_ai_model_rule(rule) is True

    def test_by_subcategory(self) -> None:
        rule = _make_rule(subcategory=["ai_model_detection"])
        assert is_ai_model_rule(rule) is True

    def test_by_description(self) -> None:
        rule = _make_rule(description="Detects usage of AI model endpoints")
        assert is_ai_model_rule(rule) is True

    def test_by_message(self) -> None:
        rule = _make_rule(message="This code uses an AI model API")
        assert is_ai_model_rule(rule) is True

    def test_by_technology(self) -> None:
        rule = _make_rule(technology=["ai model framework"])
        assert is_ai_model_rule(rule) is True

    def test_negative_regular_rule(self) -> None:
        rule = _make_rule(rule_id="py-sql-injection", category="security")
        assert is_ai_model_rule(rule) is False

    def test_negative_no_spec(self) -> None:
        rule = Mock()
        rule.spec = None
        assert is_ai_model_rule(rule) is False

    def test_negative_no_native_rule(self) -> None:
        rule = Mock()
        rule.spec.rule = None
        assert is_ai_model_rule(rule) is False

    def test_detect_without_ai_provider_is_false(self) -> None:
        rule = _make_rule(rule_id="py-detect-sql-models")
        assert is_ai_model_rule(rule) is False


# ---------------------------------------------------------------------------
# YAML parsing helpers
# ---------------------------------------------------------------------------


class TestParseYamlFile:
    """Tests for _parse_yaml_file."""

    def test_parses_rules_wrapper(self, tmp_path: Path) -> None:
        f = tmp_path / "rule.yaml"
        f.write_text("rules:\n  - id: test\n    message: hello\n")
        result = _parse_yaml_file(f)
        assert len(result) == 1
        assert result[0]["id"] == "test"

    def test_parses_bare_rule(self, tmp_path: Path) -> None:
        f = tmp_path / "rule.yaml"
        f.write_text("id: test\nmessage: hello\n")
        result = _parse_yaml_file(f)
        assert len(result) == 1
        assert result[0]["id"] == "test"

    def test_empty_file_returns_empty(self, tmp_path: Path) -> None:
        f = tmp_path / "empty.yaml"
        f.write_text("")
        result = _parse_yaml_file(f)
        assert result == []


class TestRuleDisplayId:
    """Tests for _rule_display_id."""

    def test_uses_id_field(self) -> None:
        assert _rule_display_id({"id": "my-rule"}) == "my-rule"

    def test_falls_back_to_message(self) -> None:
        assert _rule_display_id({"message": "Some msg"}) == "Some msg"

    def test_truncates_long_ids(self) -> None:
        result = _rule_display_id({"id": "x" * 200})
        assert len(result) == 80


class TestWrapYaml:
    """Tests for _wrap_yaml."""

    def test_already_wrapped(self) -> None:
        raw = "rules:\n  - id: test\n"
        assert _wrap_yaml({"id": "test"}, raw) == raw

    def test_wraps_bare_dict(self) -> None:
        raw = "id: test\nmessage: hello\n"
        wrapped = _wrap_yaml({"id": "test", "message": "hello"}, raw)
        assert wrapped.startswith("rules:")
        assert "test" in wrapped


# ---------------------------------------------------------------------------
# import_rules_from_yaml
# ---------------------------------------------------------------------------


class TestImportRulesFromYaml:
    """Tests for import_rules_from_yaml."""

    def test_dry_run_skips_api_calls(self, tmp_path: Path) -> None:
        f = tmp_path / "rule.yaml"
        f.write_text("rules:\n  - id: test-rule\n    message: hello\n")

        client = Mock()
        result = import_rules_from_yaml(client, "ns", [f], dry_run=True)
        assert isinstance(result, ImportResult)
        assert result.skipped == 1
        assert result.created == 0
        client.semgrep_rule.list.assert_not_called()

    def test_creates_new_rule(self, tmp_path: Path) -> None:
        f = tmp_path / "rule.yaml"
        f.write_text("rules:\n  - id: new-rule\n    message: hello\n")

        client = Mock()
        client.semgrep_rule.list.return_value = []  # no existing rule
        client.semgrep_rule.create.return_value = Mock(uuid="new-uuid")

        result = import_rules_from_yaml(client, "ns", [f])
        assert result.created == 1
        client.semgrep_rule.create.assert_called_once()

    def test_skips_existing_without_force(self, tmp_path: Path) -> None:
        f = tmp_path / "rule.yaml"
        f.write_text("rules:\n  - id: existing\n    message: hello\n")

        existing_rule = Mock()
        existing_rule.uuid = "existing-uuid"
        client = Mock()
        client.semgrep_rule.list.return_value = [existing_rule]

        result = import_rules_from_yaml(client, "ns", [f])
        assert result.skipped == 1
        assert result.created == 0

    def test_updates_existing_with_force(self, tmp_path: Path) -> None:
        f = tmp_path / "rule.yaml"
        f.write_text("rules:\n  - id: existing\n    message: hello\n")

        existing_rule = Mock()
        existing_rule.uuid = "existing-uuid"
        client = Mock()
        client.semgrep_rule.list.return_value = [existing_rule]

        result = import_rules_from_yaml(client, "ns", [f], force=True)
        assert result.updated == 1
        client.semgrep_rule.update.assert_called_once()

    def test_handles_parse_error(self, tmp_path: Path) -> None:
        f = tmp_path / "bad.yaml"
        f.write_text(": invalid: yaml: {{")

        client = Mock()
        result = import_rules_from_yaml(client, "ns", [f])
        assert result.failed == 1
        assert len(result.errors) == 1


# ---------------------------------------------------------------------------
# export_rules_to_yaml
# ---------------------------------------------------------------------------


class TestExportRulesToYaml:
    """Tests for export_rules_to_yaml."""

    def test_dry_run_does_not_write_files(self, tmp_path: Path) -> None:
        rule = Mock()
        rule.uuid = "r1"
        rule.spec.rule.id = "my-rule"
        rule.spec.yaml = "rules:\n  - id: my-rule\n"
        rule.meta.name = "my-rule"

        client = Mock()
        client.semgrep_rule.list.return_value = [rule]

        result = export_rules_to_yaml(
            client, "ns", tmp_path, export_all=True, dry_run=True
        )
        assert result.exported == 1
        assert result.paths == []  # no files written
        assert not list(tmp_path.glob("*.yaml"))

    def test_writes_yaml_files(self, tmp_path: Path) -> None:
        rule = Mock()
        rule.uuid = "r1"
        rule.spec.rule.id = "my-rule"
        rule.spec.yaml = "rules:\n  - id: my-rule\n"
        rule.meta.name = "my-rule"

        client = Mock()
        client.semgrep_rule.list.return_value = [rule]

        result = export_rules_to_yaml(client, "ns", tmp_path, export_all=True)
        assert result.exported == 1
        assert len(result.paths) == 1
        written = Path(result.paths[0])
        assert written.exists()
        assert "my-rule" in written.read_text()

    def test_no_matching_rules(self, tmp_path: Path) -> None:
        client = Mock()
        client.semgrep_rule.list.return_value = []

        result = export_rules_to_yaml(client, "ns", tmp_path, export_all=True)
        assert result.total == 0
        assert result.exported == 0


# ---------------------------------------------------------------------------
# calibrate_rules
# ---------------------------------------------------------------------------


class TestCalibrateRules:
    """Tests for calibrate_rules."""

    def test_dry_run_does_not_update(self) -> None:
        ai_rule = _make_rule(
            rule_id="py-detect-openai-models",
            defined_by="Endor Labs",
            disabled=True,
        )
        client = Mock()
        client.semgrep_rule.list.return_value = [ai_rule]

        result = calibrate_rules(client, "ns", dry_run=True)
        assert result.enabled == 1
        assert result.disabled == 0
        client.semgrep_rule.update.assert_not_called()

    def test_enables_ai_model_rules(self) -> None:
        ai_rule = _make_rule(
            rule_id="py-detect-openai-models",
            defined_by="Endor Labs",
            disabled=True,
        )
        client = Mock()
        client.semgrep_rule.list.return_value = [ai_rule]

        result = calibrate_rules(client, "ns")
        assert result.enabled == 1
        client.semgrep_rule.update.assert_called_once()

    def test_disables_third_party_non_ai_rules(self) -> None:
        tp_rule = _make_rule(
            rule_id="py-sql-injection",
            defined_by="3rd-Party",
            disabled=False,
        )
        # Ensure it's not classified as AI
        tp_rule.spec.rule.metadata.endor_targets = None
        tp_rule.spec.rule.metadata.category = "security"
        tp_rule.spec.rule.metadata.subcategory = None
        tp_rule.spec.rule.metadata.description = "SQL injection"
        tp_rule.spec.rule.metadata.technology = None
        tp_rule.spec.rule.message = "SQL injection detected"
        tp_rule.meta.name = "sql-injection"

        client = Mock()
        client.semgrep_rule.list.return_value = [tp_rule]

        result = calibrate_rules(client, "ns")
        assert result.disabled == 1

    def test_skips_user_defined_rules(self) -> None:
        user_rule = _make_rule(
            rule_id="my-custom-rule",
            defined_by="my-tenant",
            disabled=False,
        )
        # Not AI, not 3rd-party/Endor Labs
        user_rule.spec.rule.metadata.endor_targets = None
        user_rule.spec.rule.metadata.category = None
        user_rule.spec.rule.metadata.subcategory = None
        user_rule.spec.rule.metadata.description = None
        user_rule.spec.rule.metadata.technology = None
        user_rule.spec.rule.message = None
        user_rule.meta.name = None

        client = Mock()
        client.semgrep_rule.list.return_value = [user_rule]

        result = calibrate_rules(client, "ns")
        assert result.skipped == 1
        client.semgrep_rule.update.assert_not_called()

    def test_already_correct_counted(self) -> None:
        ai_rule = _make_rule(
            rule_id="py-detect-openai-models",
            defined_by="Endor Labs",
            disabled=False,  # already enabled
        )
        client = Mock()
        client.semgrep_rule.list.return_value = [ai_rule]

        result = calibrate_rules(client, "ns")
        assert result.already_correct == 1
        assert result.enabled == 0

    def test_handles_update_failure(self) -> None:
        ai_rule = _make_rule(
            rule_id="py-detect-openai-models",
            defined_by="Endor Labs",
            disabled=True,
        )
        client = Mock()
        client.semgrep_rule.list.return_value = [ai_rule]
        client.semgrep_rule.update.side_effect = RuntimeError("501 Method Not Allowed")

        result = calibrate_rules(client, "ns")
        assert result.failed == 1
        assert result.status == "partial"
