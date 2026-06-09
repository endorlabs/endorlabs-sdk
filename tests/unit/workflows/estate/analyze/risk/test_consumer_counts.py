"""Tests for consumer count helpers."""

from __future__ import annotations

from endorlabs.workflows.estate.analyze.risk.consumer_counts import (
    merge_version_usage_and_consumers,
)


def test_merge_version_usage_and_consumers_sorts_by_consumer() -> None:
    rows = merge_version_usage_and_consumers(
        {"1.0": 10, "2.0": 3},
        {"1.0": 2, "2.0": 9},
    )
    assert rows[0]["version"] == "2.0"
    assert rows[0]["consumer_count"] == 9
