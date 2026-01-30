"""Test cases for schema drift detection utilities.

Tests SchemaDriftDetector.log_unknown_fields and extract_unknown_fields
used by base and resource models.
"""

from endor_cockpit.utils.schema_drift import SchemaDriftDetector


class TestSchemaDriftDetectorExtractUnknownFields:
    """Tests for extract_unknown_fields."""

    def test_no_unknown_returns_empty(self) -> None:
        data = {"a": 1, "b": 2}
        model_fields = {"a", "b"}
        result = SchemaDriftDetector.extract_unknown_fields(
            data, model_fields, "TestModel"
        )
        assert result == {}

    def test_unknown_fields_returned(self) -> None:
        data = {"a": 1, "b": 2, "unknown": "x"}
        model_fields = {"a", "b"}
        result = SchemaDriftDetector.extract_unknown_fields(
            data, model_fields, "TestModel"
        )
        assert result == {"unknown": "x"}

    def test_known_ignored_suppressed_in_log_not_in_extract(self) -> None:
        data = {"a": 1, "tenant": "t", "search_score": 0.9}
        model_fields = {"a"}
        result = SchemaDriftDetector.extract_unknown_fields(
            data, model_fields, "TestModel"
        )
        assert "tenant" in result
        assert "search_score" in result
        assert "a" not in result


class TestSchemaDriftDetectorLogUnknownFields:
    """Tests for log_unknown_fields."""

    def test_empty_does_not_raise(self) -> None:
        SchemaDriftDetector.log_unknown_fields("M", {})

    def test_with_resource_name(self) -> None:
        SchemaDriftDetector.log_unknown_fields(
            "Spec", {"extra": 1}, resource_name="Finding"
        )

    def test_with_context(self) -> None:
        SchemaDriftDetector.log_unknown_fields("M", {"x": 1}, context="list response")


class TestSchemaDriftDetectorCreateFieldValidator:
    """Tests for create_field_validator."""

    def test_returns_callable(self) -> None:
        fn = SchemaDriftDetector.create_field_validator({"a", "b"}, "TestModel")
        assert callable(fn)

    def test_validator_returns_value_unchanged(self) -> None:
        fn = SchemaDriftDetector.create_field_validator({"a", "b"}, "TestModel")
        value = {"a": 1}

        # info mock: field_validator passes (value, info); info has field_name
        class Info:
            field_name = "spec"

        result = fn(value, Info())
        assert result == value
