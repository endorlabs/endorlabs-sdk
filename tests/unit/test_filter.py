"""Tests for the filter builder module.

Covers all 12 API filter operators, composition (& / |), nesting,
negation, date()/now() helpers, string escaping, enum-like value
detection, and __str__ round-trips.
"""

from __future__ import annotations

import pytest

from endorlabs.filter import Clause, CompositeFilter, F, FilterExpression

# ---------------------------------------------------------------------------
# Equality / Comparison operators
# ---------------------------------------------------------------------------


class TestEqualityOperators:
    """Tests for == and != operators."""

    def test_eq_string_value(self) -> None:
        expr = F("meta.name") == "my-project"
        assert str(expr) == 'meta.name == "my-project"'

    def test_eq_enum_like_value_unquoted(self) -> None:
        """Enum-like constants (UPPER_CASE) are emitted unquoted."""
        expr = F("spec.level") == "FINDING_LEVEL_CRITICAL"
        assert str(expr) == "spec.level == FINDING_LEVEL_CRITICAL"

    def test_ne_string_value(self) -> None:
        expr = F("meta.name") != "archived"
        assert str(expr) == 'meta.name != "archived"'

    def test_ne_enum_like_value(self) -> None:
        expr = F("spec.level") != "FINDING_LEVEL_LOW"
        assert str(expr) == "spec.level != FINDING_LEVEL_LOW"

    def test_eq_integer_value(self) -> None:
        expr = F("spec.count") == 42
        assert str(expr) == "spec.count == 42"

    def test_eq_bool_value(self) -> None:
        expr = F("spec.dependency_data.public") == False  # noqa: E712
        assert str(expr) == "spec.dependency_data.public == false"

    def test_eq_bool_true(self) -> None:
        expr = F("spec.active") == True  # noqa: E712
        assert str(expr) == "spec.active == true"


class TestComparisonOperators:
    """Tests for <, <=, >, >= operators."""

    def test_lt(self) -> None:
        expr = F("spec.score") < 5
        assert str(expr) == "spec.score < 5"

    def test_le(self) -> None:
        expr = F("spec.score") <= 5
        assert str(expr) == "spec.score <= 5"

    def test_gt(self) -> None:
        expr = F("spec.score") > 3
        assert str(expr) == "spec.score > 3"

    def test_ge(self) -> None:
        expr = F("spec.score") >= 3
        assert str(expr) == "spec.score >= 3"


# ---------------------------------------------------------------------------
# Contains / Not Contains
# ---------------------------------------------------------------------------


class TestContainsOperator:
    """Tests for contains and not_contains."""

    def test_contains_single_value(self) -> None:
        expr = F("spec.finding_tags").contains("FINDING_TAGS_REACHABLE_FUNCTION")
        assert (
            str(expr) == "spec.finding_tags contains [FINDING_TAGS_REACHABLE_FUNCTION]"
        )

    def test_contains_multiple_values(self) -> None:
        expr = F("spec.finding_tags").contains(
            "FINDING_TAGS_FIX_AVAILABLE", "FINDING_TAGS_REACHABLE_FUNCTION"
        )
        assert str(expr) == (
            "spec.finding_tags contains "
            "[FINDING_TAGS_FIX_AVAILABLE, FINDING_TAGS_REACHABLE_FUNCTION]"
        )

    def test_contains_string_values_quoted(self) -> None:
        expr = F("meta.tags").contains("sanity", "test")
        assert str(expr) == 'meta.tags contains ["sanity", "test"]'

    def test_not_contains_single_value(self) -> None:
        expr = F("meta.tags").not_contains("sanity")
        assert str(expr) == 'meta.tags not contains ["sanity"]'

    def test_not_contains_multiple_values(self) -> None:
        expr = F("meta.tags").not_contains("sanity", "test")
        assert str(expr) == 'meta.tags not contains ["sanity", "test"]'

    def test_contains_mixed_values(self) -> None:
        """Mixed enum and string values keep their appropriate quoting."""
        expr = F("spec.finding_categories").contains("FINDING_CATEGORY_VULNERABILITY")
        assert str(expr) == (
            "spec.finding_categories contains [FINDING_CATEGORY_VULNERABILITY]"
        )


# ---------------------------------------------------------------------------
# In / Not In
# ---------------------------------------------------------------------------


class TestInOperator:
    """Tests for is_in and not_in."""

    def test_in_enum_values(self) -> None:
        expr = F("spec.level").is_in("FINDING_LEVEL_CRITICAL", "FINDING_LEVEL_HIGH")
        assert str(expr) == (
            "spec.level in [FINDING_LEVEL_CRITICAL, FINDING_LEVEL_HIGH]"
        )

    def test_in_string_values(self) -> None:
        expr = F("uuid").is_in("64a3b8326dda5fb62bfcceea", "658323c91aa208f231cc7eff")
        assert str(expr) == (
            'uuid in ["64a3b8326dda5fb62bfcceea", "658323c91aa208f231cc7eff"]'
        )

    def test_not_in_values(self) -> None:
        expr = F("spec.ecosystem").not_in("ECOSYSTEM_MAVEN", "ECOSYSTEM_NPM")
        assert str(expr) == ("spec.ecosystem not in [ECOSYSTEM_MAVEN, ECOSYSTEM_NPM]")


# ---------------------------------------------------------------------------
# Matches (regex)
# ---------------------------------------------------------------------------


class TestMatchesOperator:
    """Tests for matches (regex)."""

    def test_matches_simple(self) -> None:
        expr = F("meta.name").matches("validation bypass")
        assert str(expr) == 'meta.name matches "validation bypass"'

    def test_matches_case_insensitive(self) -> None:
        expr = F("meta.description").matches("(?i)django")
        assert str(expr) == 'meta.description matches "(?i)django"'

    def test_matches_regex_pattern(self) -> None:
        expr = F("spec.claims").matches(".*api-key.*")
        assert str(expr) == 'spec.claims matches ".*api-key.*"'


# ---------------------------------------------------------------------------
# Exists / Not Exists
# ---------------------------------------------------------------------------


class TestExistsOperator:
    """Tests for exists and not_exists."""

    def test_exists(self) -> None:
        expr = F("spec.remediation").exists()
        assert str(expr) == "spec.remediation exists"

    def test_not_exists(self) -> None:
        expr = F("spec.remediation").not_exists()
        assert str(expr) == "spec.remediation not exists"

    def test_invert_exists(self) -> None:
        """~exists() produces not exists."""
        expr = ~F("spec.remediation").exists()
        assert str(expr) == "spec.remediation not exists"


# ---------------------------------------------------------------------------
# Date / Now helpers
# ---------------------------------------------------------------------------


class TestDateNowHelpers:
    """Tests for F.date() and F.now() helpers."""

    def test_date_value(self) -> None:
        expr = F("meta.create_time") >= F.date("2024-05-01")
        assert str(expr) == "meta.create_time >= date(2024-05-01)"

    def test_date_with_timestamp(self) -> None:
        expr = F("meta.create_time") >= F.date("2024-05-01T13:30:00.000Z")
        assert str(expr) == "meta.create_time >= date(2024-05-01T13:30:00.000Z)"

    def test_now_value(self) -> None:
        expr = F("meta.create_time") >= F.now("-72h")
        assert str(expr) == "meta.create_time >= now(-72h)"

    def test_now_minutes(self) -> None:
        expr = F("meta.create_time") >= F.now("-15m")
        assert str(expr) == "meta.create_time >= now(-15m)"

    def test_date_range(self) -> None:
        """Date range using AND composition."""
        expr = (F("meta.create_time") >= F.date("2024-05-01")) & (
            F("meta.create_time") < F.date("2024-06-01")
        )
        assert str(expr) == (
            "(meta.create_time >= date(2024-05-01)) "
            "and (meta.create_time < date(2024-06-01))"
        )


# ---------------------------------------------------------------------------
# Composition (AND / OR)
# ---------------------------------------------------------------------------


class TestComposition:
    """Tests for & (AND) and | (OR) composition."""

    def test_and_composition(self) -> None:
        expr = (F("spec.level") == "FINDING_LEVEL_CRITICAL") & (
            F("spec.finding_tags").contains("FINDING_TAGS_REACHABLE_FUNCTION")
        )
        assert str(expr) == (
            "(spec.level == FINDING_LEVEL_CRITICAL) "
            "and (spec.finding_tags contains [FINDING_TAGS_REACHABLE_FUNCTION])"
        )

    def test_or_composition(self) -> None:
        expr = (F("meta.name") == "archived_source_code_repo") | (
            F("meta.name") == "outdated_release"
        )
        assert str(expr) == (
            '(meta.name == "archived_source_code_repo") '
            'or (meta.name == "outdated_release")'
        )

    def test_nested_composition(self) -> None:
        """Complex nesting with parentheses: (A and B) or (C and D)."""
        expr = (
            F("spec.finding_categories").contains("FINDING_CATEGORY_VULNERABILITY")
            & (F("spec.level") == "FINDING_LEVEL_CRITICAL")
        ) | (
            F("spec.finding_categories").contains("FINDING_CATEGORY_SECRETS")
            & F("spec.level").is_in("FINDING_LEVEL_CRITICAL", "FINDING_LEVEL_HIGH")
        )
        result = str(expr)
        assert "FINDING_CATEGORY_VULNERABILITY" in result
        assert "FINDING_CATEGORY_SECRETS" in result
        assert " or " in result
        assert " and " in result

    def test_triple_and(self) -> None:
        """Three clauses chained with &."""
        expr = (
            (F("spec.project_uuid") == "uuid-123")
            & (F("spec.level") == "FINDING_LEVEL_CRITICAL")
            & (F("spec.finding_tags").contains("FINDING_TAGS_FIX_AVAILABLE"))
        )
        result = str(expr)
        assert "uuid-123" in result
        assert "FINDING_LEVEL_CRITICAL" in result
        assert "FINDING_TAGS_FIX_AVAILABLE" in result
        assert result.count(" and ") == 2


# ---------------------------------------------------------------------------
# Value escaping
# ---------------------------------------------------------------------------


class TestValueEscaping:
    """Tests for value escaping in filter strings."""

    def test_string_with_double_quotes_escaped(self) -> None:
        """Double quotes inside string values are escaped."""
        expr = F("meta.name") == 'project "special"'
        result = str(expr)
        assert result == 'meta.name == "project \\"special\\""'

    def test_enum_detection_all_caps_underscore(self) -> None:
        """UPPER_CASE_123 is treated as an enum (unquoted)."""
        expr = F("spec.type") == "POLICY_TYPE_USER_FINDING"
        assert str(expr) == "spec.type == POLICY_TYPE_USER_FINDING"

    def test_mixed_case_is_quoted(self) -> None:
        """Mixed-case values are quoted as strings."""
        expr = F("meta.name") == "MyProject"
        assert str(expr) == 'meta.name == "MyProject"'

    def test_lowercase_is_quoted(self) -> None:
        """Lowercase values are quoted as strings."""
        expr = F("meta.name") == "backend"
        assert str(expr) == 'meta.name == "backend"'

    def test_numeric_string_is_quoted(self) -> None:
        """String of digits is still quoted."""
        expr = F("uuid") == "12345"
        assert str(expr) == 'uuid == "12345"'

    def test_empty_string_is_quoted(self) -> None:
        expr = F("meta.name") == ""
        assert str(expr) == 'meta.name == ""'


# ---------------------------------------------------------------------------
# Type checks
# ---------------------------------------------------------------------------


class TestTypeSystem:
    """Tests for the type hierarchy."""

    def test_clause_is_filter_expression(self) -> None:
        expr = F("meta.name") == "x"
        assert isinstance(expr, FilterExpression)
        assert isinstance(expr, Clause)

    def test_composite_is_filter_expression(self) -> None:
        expr = (F("a") == 1) & (F("b") == 2)
        assert isinstance(expr, FilterExpression)
        assert isinstance(expr, CompositeFilter)

    def test_str_returns_string(self) -> None:
        expr = F("meta.name") == "x"
        assert isinstance(str(expr), str)

    def test_repr_is_useful(self) -> None:
        expr = F("meta.name") == "x"
        assert "meta.name" in repr(expr)


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    """Tests for edge cases and validation."""

    def test_contains_requires_at_least_one_value(self) -> None:
        with pytest.raises(ValueError, match="at least one value"):
            F("spec.tags").contains()

    def test_is_in_requires_at_least_one_value(self) -> None:
        with pytest.raises(ValueError, match="at least one value"):
            F("spec.level").is_in()

    def test_not_contains_requires_at_least_one_value(self) -> None:
        with pytest.raises(ValueError, match="at least one value"):
            F("spec.tags").not_contains()

    def test_not_in_requires_at_least_one_value(self) -> None:
        with pytest.raises(ValueError, match="at least one value"):
            F("spec.level").not_in()

    def test_invert_non_exists_raises(self) -> None:
        """~ only supported on exists clauses."""
        expr = F("meta.name") == "x"
        with pytest.raises(TypeError, match="invert"):
            _ = ~expr
