"""Tests for collect benchmark helpers."""

from __future__ import annotations

from unittest.mock import MagicMock

from endorlabs.core.whoami import WhoamiResult
from endorlabs.workflows.estate.collect import benchmark


def test_session_user_slug_from_whoami_result() -> None:
    client = MagicMock()
    client.whoami.return_value = WhoamiResult(identity="User.Name@corp.com")
    assert benchmark._session_user_slug(client) == "user.name"
