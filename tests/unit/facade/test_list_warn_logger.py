"""List-time warnings dual-emit through warnings and the SDK logger."""

from __future__ import annotations

import logging
from unittest.mock import Mock

import pytest

import endorlabs
from endorlabs.api_client import APIClient
from endorlabs.facade import base as facade_base


def test_warn_and_log_emits_warning_and_logger(
    caplog: pytest.LogCaptureFixture,
) -> None:
    with (
        pytest.warns(UserWarning, match="project-namespace"),
        caplog.at_level(logging.WARNING, logger=facade_base._logger.name),
    ):
        facade_base._warn_and_log(
            "Finding.list() returned no rows at project-namespace default",
            category=UserWarning,
            stacklevel=1,
        )
    assert any("project-namespace" in record.message for record in caplog.records)


def test_list_count_true_deprecation_logs(
    caplog: pytest.LogCaptureFixture,
) -> None:
    client = endorlabs.Client(tenant="example-tenant", api_client=Mock(spec=APIClient))
    client.Finding._ops.count = Mock(return_value=0)
    with (
        pytest.warns(DeprecationWarning, match="count"),
        caplog.at_level(logging.WARNING, logger=facade_base._logger.name),
    ):
        result = client.Finding.list(count=True, namespace="example-tenant.child")
    assert result == 0
    assert any("count=True" in record.message for record in caplog.records)
