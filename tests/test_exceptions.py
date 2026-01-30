"""Test cases for Endor Cockpit SDK exception classes.

Tests construction, __str__ formatting, and map_status_code_to_exception
for stable public API behavior.
"""

import pytest

from endor_cockpit.exceptions import (
    ConflictError,
    EndorAPIError,
    NotFoundError,
    PermissionDeniedError,
    RateLimitError,
    ServerError,
    UnauthorizedError,
    ValidationError,
    map_status_code_to_exception,
)


class TestEndorAPIError:
    """Tests for EndorAPIError base class."""

    def test_construction_minimal(self) -> None:
        err = EndorAPIError("test message")
        assert err.args[0] == "test message"
        assert err.message == "test message"
        assert err.status_code is None
        assert err.operation is None
        assert err.resource_uuid is None
        assert err.namespace is None

    def test_construction_full(self) -> None:
        err = EndorAPIError(
            "msg",
            status_code=404,
            operation="get",
            resource_uuid="abc123",
            namespace="tenant.ns",
        )
        assert err.message == "msg"
        assert err.status_code == 404
        assert err.operation == "get"
        assert err.resource_uuid == "abc123"
        assert err.namespace == "tenant.ns"

    def test_str_includes_context(self) -> None:
        err = EndorAPIError(
            "msg",
            status_code=404,
            operation="get",
            resource_uuid="abc",
            namespace="t.n",
        )
        s = str(err)
        assert "msg" in s
        assert "404" in s
        assert "get" in s
        assert "abc" in s
        assert "t.n" in s


@pytest.mark.parametrize(
    "exc_class,expected_status",
    [
        (NotFoundError, 404),
        (ValidationError, 400),
        (PermissionDeniedError, 403),
        (UnauthorizedError, 401),
        (ConflictError, 409),
        (RateLimitError, 429),
        (ServerError, 500),
    ],
)
def test_exception_subclass_construction(
    exc_class: type[EndorAPIError], expected_status: int
) -> None:
    err = exc_class("custom msg", operation="update", namespace="t.n")
    assert err.message == "custom msg"
    assert err.status_code == expected_status
    assert err.operation == "update"
    assert err.namespace == "t.n"
    s = str(err)
    assert "custom msg" in s
    assert str(expected_status) in s


def test_server_error_accepts_status_code() -> None:
    err = ServerError("err", status_code=503)
    assert err.status_code == 503


def test_map_status_code_to_exception_404() -> None:
    exc = map_status_code_to_exception(404)
    assert isinstance(exc, NotFoundError)
    assert exc.status_code == 404


def test_map_status_code_to_exception_400() -> None:
    exc = map_status_code_to_exception(400)
    assert isinstance(exc, ValidationError)
    assert exc.status_code == 400


def test_map_status_code_to_exception_401() -> None:
    exc = map_status_code_to_exception(401)
    assert isinstance(exc, UnauthorizedError)


def test_map_status_code_to_exception_403() -> None:
    exc = map_status_code_to_exception(403)
    assert isinstance(exc, PermissionDeniedError)


def test_map_status_code_to_exception_409() -> None:
    exc = map_status_code_to_exception(409)
    assert isinstance(exc, ConflictError)


def test_map_status_code_to_exception_429() -> None:
    exc = map_status_code_to_exception(429)
    assert isinstance(exc, RateLimitError)


def test_map_status_code_to_exception_501() -> None:
    from endor_cockpit.exceptions import NotImplementedError

    exc = map_status_code_to_exception(501)
    assert isinstance(exc, NotImplementedError)


@pytest.mark.parametrize("code", [500, 502, 503, 504])
def test_map_status_code_to_exception_5xx(code: int) -> None:
    exc = map_status_code_to_exception(code)
    assert isinstance(exc, ServerError)
    assert exc.status_code == code


def test_map_status_code_to_exception_unknown_returns_base() -> None:
    exc = map_status_code_to_exception(418)
    assert isinstance(exc, EndorAPIError)
    assert not isinstance(exc, NotFoundError)
    assert exc.status_code == 418
    assert "418" in str(exc)


def test_map_status_code_to_exception_passes_message() -> None:
    exc = map_status_code_to_exception(404, message="Not found: xyz")
    assert exc.message == "Not found: xyz"


def test_map_status_code_to_exception_passes_kwargs() -> None:
    exc = map_status_code_to_exception(404, resource_uuid="uuid123")
    assert exc.resource_uuid == "uuid123"
