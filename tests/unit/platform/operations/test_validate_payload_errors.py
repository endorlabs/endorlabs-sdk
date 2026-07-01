"""Tests for BaseResourceOperations payload pre-validation errors."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from pydantic import BaseModel, Field

from endorlabs.core.exceptions import ValidationError as EndorValidationError
from endorlabs.operations import BaseResourceOperations


class _Payload(BaseModel):
    name: str = Field(min_length=1)


def test_validate_payload_includes_field_paths() -> None:
    ops = BaseResourceOperations(MagicMock(), "projects", _Payload)
    payload = _Payload.model_construct(name="")

    with pytest.raises(EndorValidationError, match="name") as exc_info:
        ops._validate_payload(payload, "create", "tenant.ns")

    assert "Invalid payload for create operation" in str(exc_info.value)
    assert exc_info.value.__cause__ is not None
