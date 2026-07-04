"""Tests for create() request timeout header alignment."""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

from pydantic import BaseModel

from endorlabs.operations import BaseResourceOperations


class _Payload(BaseModel):
    name: str = "test"


@patch.dict(os.environ, {"ENDOR_CREATE_TIMEOUT": "120"}, clear=False)
def test_create_sets_request_timeout_header_when_env_set() -> None:
    mock_client = MagicMock()
    mock_client.post.return_value.json.return_value = {"uuid": "new-uuid"}
    ops = BaseResourceOperations(mock_client, "projects", _Payload)

    ops.create("tenant.ns", _Payload())

    mock_client.post.assert_called_once()
    call_kwargs = mock_client.post.call_args[1]
    assert call_kwargs["timeout"] == 120.0
    assert call_kwargs["headers"]["Request-timeout"] == "120"
