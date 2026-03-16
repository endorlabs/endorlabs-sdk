"""Tests for centralized logging configuration and redaction utilities."""

import logging

import pytest

from endorlabs.utils.logging_config import get_resource_logger
from endorlabs.utils.redaction import (
    JSON_REDACTION_REPLACEMENT,
    RedactingFilter,
    json_redaction_pattern,
    redaction_pattern,
    url_token_redaction_pattern,
    url_token_redaction_replacement,
)


def test_get_resource_logger_returns_logger_with_correct_name() -> None:
    """get_resource_logger returns a logger named after the caller's module."""
    logger = get_resource_logger("endorlabs.resources.project")
    assert logger.name == "endorlabs.resources.project"


def test_get_resource_logger_attaches_redacting_filter() -> None:
    """get_resource_logger attaches exactly one RedactingFilter."""
    name = "endorlabs.resources._test_redact_check"
    logger = get_resource_logger(name)
    redacting_filters = [f for f in logger.filters if isinstance(f, RedactingFilter)]
    assert len(redacting_filters) == 1


def test_get_resource_logger_is_idempotent() -> None:
    """Calling get_resource_logger twice does not duplicate the filter."""
    name = "endorlabs.resources._test_idempotent"
    _ = get_resource_logger(name)
    logger = get_resource_logger(name)
    redacting_filters = [f for f in logger.filters if isinstance(f, RedactingFilter)]
    assert len(redacting_filters) == 1


def test_get_resource_logger_redacts_secrets() -> None:
    """The attached filter redacts sensitive values from log messages."""
    name = "endorlabs.resources._test_redaction"
    logger = get_resource_logger(name)
    record = logging.LogRecord(
        name=name,
        level=logging.DEBUG,
        pathname="",
        lineno=0,
        msg="'secret': 'my-api-secret-value'",
        args=None,
        exc_info=None,
    )
    # Apply all filters (our RedactingFilter should rewrite the message)
    for f in logger.filters:
        if isinstance(f, logging.Filter):
            f.filter(record)
    assert "my-api-secret-value" not in record.msg
    assert "REDACTED" in record.msg


# ---------------------------------------------------------------------------
# RedactingFilter cross-quoting tests
# ---------------------------------------------------------------------------


def _make_filter() -> RedactingFilter:
    """Build a RedactingFilter with the standard SDK pattern set."""
    return RedactingFilter(
        [
            redaction_pattern,
            (json_redaction_pattern, JSON_REDACTION_REPLACEMENT),
            (url_token_redaction_pattern, url_token_redaction_replacement),
        ]
    )


def _apply(rf: RedactingFilter, msg: str) -> str:
    """Run a message through the filter and return the rewritten msg."""
    record = logging.LogRecord(
        name="test",
        level=logging.DEBUG,
        pathname="",
        lineno=0,
        msg=msg,
        args=None,
        exc_info=None,
    )
    rf.filter(record)
    return record.msg


class TestRedactingFilterQuotingCombinations:
    """Verify all four key/value quoting combinations are redacted."""

    @pytest.fixture(autouse=True)
    def _setup(self) -> None:
        self.rf = _make_filter()

    # -- Homogeneous quoting ------------------------------------------------

    def test_single_key_single_value(self) -> None:
        """'key': 'value' -- standard Python repr."""
        result = _apply(self.rf, "'token': 'eyJhbGciOiJSUz'")
        assert "eyJhbGciOiJSUz" not in result
        assert "REDACTED" in result

    def test_double_key_double_value(self) -> None:
        """\"key\": \"value\" -- standard JSON."""
        result = _apply(self.rf, '"token": "eyJhbGciOiJSUz"')
        assert "eyJhbGciOiJSUz" not in result
        assert "REDACTED" in result

    # -- Mixed quoting (the cross-quoting gap) ------------------------------

    def test_single_key_double_value(self) -> None:
        """'key': \"value\" -- repr when value contains a single quote."""
        result = _apply(self.rf, """'token': "O'Reilly-secret"  """)
        assert "O'Reilly-secret" not in result
        assert "REDACTED" in result

    def test_double_key_single_value(self) -> None:
        """\"key\": 'value' -- symmetric mixed case."""
        result = _apply(self.rf, "\"secret\": 'my-api-secret'")
        assert "my-api-secret" not in result
        assert "REDACTED" in result

    # -- All sensitive key names -------------------------------------------

    @pytest.mark.parametrize("key_name", ["authorization", "secret", "token", "key"])
    def test_all_keys_single_key_double_value(self, key_name: str) -> None:
        """Mixed quoting works for every key in REDACTED_KEYS."""
        result = _apply(self.rf, f"'{key_name}': \"sensitive-val'ue\"")
        assert "sensitive-val'ue" not in result
        assert "REDACTED" in result

    @pytest.mark.parametrize("key_name", ["authorization", "secret", "token", "key"])
    def test_all_keys_double_key_single_value(self, key_name: str) -> None:
        """Mixed quoting works for every key in REDACTED_KEYS."""
        result = _apply(self.rf, f"\"{key_name}\": 'sensitive-value'")
        assert "sensitive-value" not in result
        assert "REDACTED" in result

    # -- Case insensitivity ------------------------------------------------

    def test_case_insensitive_key(self) -> None:
        """Key matching is case-insensitive (e.g. 'Authorization')."""
        result = _apply(self.rf, "'Authorization': \"Bearer eyJ...\"")
        assert "Bearer eyJ..." not in result
        assert "REDACTED" in result


class TestRedactingFilterArgsRedaction:
    """Verify tuple and dict record.args are redacted for mixed quoting."""

    @pytest.fixture(autouse=True)
    def _setup(self) -> None:
        self.rf = _make_filter()

    def test_tuple_args_mixed_quoting(self) -> None:
        """Positional args containing mixed-quoted secrets are redacted."""
        record = logging.LogRecord(
            name="test",
            level=logging.DEBUG,
            pathname="",
            lineno=0,
            msg="Header: %s",
            args=("'token': \"secret-val'ue\"",),
            exc_info=None,
        )
        self.rf.filter(record)
        assert isinstance(record.args, tuple)
        assert "secret-val'ue" not in record.args[0]
        assert "REDACTED" in record.args[0]

    def test_dict_args_mixed_quoting(self) -> None:
        """Named args containing mixed-quoted secrets are redacted."""
        record = logging.LogRecord(
            name="test",
            level=logging.DEBUG,
            pathname="",
            lineno=0,
            msg="Header: %(header)s",
            args=None,
            exc_info=None,
        )
        # Set dict args after construction to avoid LogRecord.__init__
        # attempting to index the dict as args[0] (CPython quirk).
        record.args = {"header": "'secret': \"api-key-val'ue\""}
        self.rf.filter(record)
        assert isinstance(record.args, dict)
        assert "api-key-val'ue" not in record.args["header"]
        assert "REDACTED" in record.args["header"]


class TestRedactingFilterReprIntegration:
    """End-to-end test using actual Python repr() output."""

    @pytest.fixture(autouse=True)
    def _setup(self) -> None:
        self.rf = _make_filter()

    def test_repr_with_embedded_single_quote_in_value(self) -> None:
        """repr() of a dict with a single-quote in the value triggers mixed quoting."""
        secret_dict = {"token": "val'ue-with-quote"}
        repr_str = repr(secret_dict)
        result = _apply(self.rf, repr_str)
        assert "val'ue-with-quote" not in result
        assert "REDACTED" in result

    def test_repr_with_normal_value(self) -> None:
        """repr() of a dict with a normal value uses homogeneous single quoting."""
        secret_dict = {"token": "eyJhbGciOiJSUzI1NiJ9"}
        repr_str = repr(secret_dict)
        result = _apply(self.rf, repr_str)
        assert "eyJhbGciOiJSUzI1NiJ9" not in result
        assert "REDACTED" in result
