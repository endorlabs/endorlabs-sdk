"""Unit tests for scheduleable full-row log export helpers."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

from endorlabs.workflows.log_export.export import (
    export_logs,
    format_mql_date,
    iter_time_slices,
    parse_iso_utc,
    row_to_dict,
    time_window_filter,
)


def test_parse_iso_utc_z_suffix() -> None:
    assert parse_iso_utc("2026-08-25T12:00:00Z") == datetime(
        2026, 8, 25, 12, 0, 0, tzinfo=UTC
    )


def test_format_mql_date() -> None:
    assert (
        format_mql_date(datetime(2026, 8, 25, 12, 30, 0, tzinfo=UTC))
        == "2026-08-25T12:30:00Z"
    )


def test_iter_time_slices_covers_window() -> None:
    since = datetime(2026, 8, 25, 0, 0, 0, tzinfo=UTC)
    until = datetime(2026, 8, 25, 2, 30, 0, tzinfo=UTC)
    slices = list(iter_time_slices(since, until, slice_hours=1.0))
    assert slices == [
        (since, datetime(2026, 8, 25, 1, 0, 0, tzinfo=UTC)),
        (
            datetime(2026, 8, 25, 1, 0, 0, tzinfo=UTC),
            datetime(2026, 8, 25, 2, 0, 0, tzinfo=UTC),
        ),
        (
            datetime(2026, 8, 25, 2, 0, 0, tzinfo=UTC),
            until,
        ),
    ]


def test_iter_time_slices_rejects_non_positive() -> None:
    since = datetime(2026, 8, 25, 0, 0, 0, tzinfo=UTC)
    until = datetime(2026, 8, 25, 1, 0, 0, tzinfo=UTC)
    with pytest.raises(ValueError, match="slice_hours"):
        list(iter_time_slices(since, until, slice_hours=0))


def test_time_window_filter() -> None:
    since = datetime(2026, 8, 25, 0, 0, 0, tzinfo=UTC)
    until = datetime(2026, 8, 25, 1, 0, 0, tzinfo=UTC)
    assert time_window_filter(since, until) == (
        "meta.create_time >= date(2026-08-25T00:00:00Z) and "
        "meta.create_time < date(2026-08-25T01:00:00Z)"
    )


def test_row_to_dict_passthrough_and_model_dump() -> None:
    assert row_to_dict({"uuid": "a"}) == {"uuid": "a"}
    model = MagicMock()
    model.model_dump.return_value = {"uuid": "b"}
    assert row_to_dict(model) == {"uuid": "b"}
    model.model_dump.assert_called_once_with(mode="json", exclude_none=False)


def test_export_logs_jsonl_writes_full_rows(tmp_path: Path) -> None:
    client = MagicMock()
    client.PackageFirewallLog.list.side_effect = [
        [{"uuid": "1", "spec": {"action": "BLOCK"}}],
        [],
    ]
    out = tmp_path / "out.jsonl"
    since = datetime(2026, 8, 25, 0, 0, 0, tzinfo=UTC)
    until = datetime(2026, 8, 25, 2, 0, 0, tzinfo=UTC)
    result = export_logs(
        client,
        namespace="example-tenant",
        source="package-firewall",
        since=since,
        until=until,
        output_path=out,
        export_format="jsonl",
        slice_hours=1.0,
    )
    assert result.ok
    assert result.row_count == 1
    assert result.slice_count == 2
    lines = out.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    assert '"uuid": "1"' in lines[0]
    assert client.PackageFirewallLog.list.call_count == 2


def test_export_logs_csv_payload_column(tmp_path: Path) -> None:
    client = MagicMock()
    client.PackageFirewallLog.list.return_value = [{"uuid": "row-1"}]
    out = tmp_path / "out.csv"
    since = datetime(2026, 8, 25, 0, 0, 0, tzinfo=UTC)
    until = datetime(2026, 8, 25, 1, 0, 0, tzinfo=UTC)
    result = export_logs(
        client,
        namespace="example-tenant",
        source="package-firewall",
        since=since,
        until=until,
        output_path=out,
        export_format="csv",
        slice_hours=1.0,
    )
    assert result.ok
    text = out.read_text(encoding="utf-8")
    assert text.startswith("payload\n")
    assert "row-1" in text


def test_export_logs_empty_window_creates_artifact(tmp_path: Path) -> None:
    client = MagicMock()
    client.PackageFirewallLog.list.return_value = []
    out = tmp_path / "empty.jsonl"
    since = datetime(2026, 8, 25, 0, 0, 0, tzinfo=UTC)
    until = datetime(2026, 8, 25, 1, 0, 0, tzinfo=UTC)
    result = export_logs(
        client,
        namespace="example-tenant",
        source="package-firewall",
        since=since,
        until=until,
        output_path=out,
        export_format="jsonl",
    )
    assert result.ok
    assert result.row_count == 0
    assert out.exists()
    assert out.read_text(encoding="utf-8") == ""


def test_export_logs_agent_hook_events_uses_raw_api(tmp_path: Path) -> None:
    client = MagicMock()
    api = MagicMock()
    client._client = api
    api.get_all.return_value = iter([{"uuid": "evt-1"}])
    out = tmp_path / "hooks.jsonl"
    since = datetime(2026, 8, 25, 0, 0, 0, tzinfo=UTC)
    until = datetime(2026, 8, 25, 1, 0, 0, tzinfo=UTC)
    result = export_logs(
        client,
        namespace="example-tenant",
        source="agent-hook-events",
        since=since,
        until=until,
        output_path=out,
        export_format="jsonl",
    )
    assert result.ok
    assert result.row_count == 1
    api.get_all.assert_called_once()
    call_args = api.get_all.call_args
    assert call_args.args[0] == "v1/namespaces/example-tenant/agent-hook-events"
    params: dict[str, Any] = call_args.kwargs["params"]
    assert "list_parameters.filter" in params
