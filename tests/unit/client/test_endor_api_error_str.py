"""Tests for EndorAPIError string formatting."""

from __future__ import annotations

from typing import TYPE_CHECKING

from endorlabs.core.exceptions import EndorAPIError

if TYPE_CHECKING:
    from endorlabs.core.types import ErrorResponse


def test_endor_api_error_str_includes_details() -> None:
    error_response: ErrorResponse = {
        "error": "invalid_argument",
        "message": "bad request",
        "code": 400,
        "details": "field spec.level is required",
    }
    exc = EndorAPIError(
        "Validation failed",
        status_code=400,
        error_response=error_response,
        operation="create",
        namespace="tenant.ns",
    )

    rendered = str(exc)

    assert "field spec.level is required" in rendered
    assert "Details:" in rendered
    assert "Operation: create" in rendered
