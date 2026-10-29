"""Unit tests for PR scan statistics (ScanResult-only, time-sharded)."""

from __future__ import annotations

import datetime as dt
import itertools
import re
from typing import Any
from unittest.mock import MagicMock

import pytest

from endorlabs.workflows.pr_scans import (
    collect_pr_scan_stats,
    is_blocked,
    pr_number,
    project_clauses,
    time_windows,
)
from endorlabs.workflows.pr_scans.collect import shard_filter

UTC = dt.UTC


def _spec(pr_id: str | None = None, **extra: Any) -> dict[str, Any]:
    spec: dict[str, Any] = {
        "status": "STATUS_SUCCESS",
        "type": "TYPE_ALL_SCANS",
        **extra,
    }
    if pr_id is not None:
        spec["environment"] = {"config": {"ScanConfig": {"SCMPRID": pr_id}}}
    return spec


def test_pr_number_from_tag() -> None:
    assert pr_number(["check_run=1", "pr=5178"]) == "5178"


def test_pr_number_falls_back_to_scan_config() -> None:
    assert pr_number([], _spec("42")) == "42"
    assert pr_number(None, _spec("42")) == "42"


def test_merge_to_main_is_not_a_pr() -> None:
    assert (
        pr_number(["check_run=1", "merge-to-main", "scan_request=x"], _spec("")) is None
    )


@pytest.mark.parametrize("tags", [["pr="], ["pr=0"], ["pull=5"], ["xpr=5"]])
def test_empty_zero_or_lookalike_tags_are_not_prs(tags: list[str]) -> None:
    assert pr_number(tags, _spec("0")) is None
    assert pr_number(tags, None) is None


def test_is_blocked_only_for_enforced_outcomes() -> None:
    assert is_blocked({"blocking_findings": ["f1"]})
    assert is_blocked({"exit_code": "ENDORCTL_RC_POLICY_VIOLATION"})
    assert not is_blocked({"exit_code": "ENDORCTL_RC_SUCCESS"})
    assert not is_blocked({})
    assert not is_blocked(None)


def test_time_windows_cover_range_exactly() -> None:
    since = dt.datetime(2026, 10, 7, 0, 0, tzinfo=UTC)
    until = dt.datetime(2026, 10, 28, 18, 0, tzinfo=UTC)
    windows = time_windows(since, until, 12)
    assert windows[0][0] == since
    assert windows[-1][1] == until
    assert all(a[1] == b[0] for a, b in itertools.pairwise(windows))
    assert all(s < e for s, e in windows)
    with pytest.raises(ValueError, match="shard_hours"):
        time_windows(since, until, 0)


def test_project_clauses_chunk_and_dedupe() -> None:
    assert project_clauses(None) == [None]
    uuids = [f"u{i}" for i in range(600)]
    clauses = project_clauses([*uuids, "u0"], chunk=250)
    assert len(clauses) == 3
    assert clauses[0].startswith("meta.parent_uuid in [")
    assert sum(c.count('"u') for c in clauses) == 600
    with pytest.raises(ValueError, match="empty project scope"):
        project_clauses([])


def test_shard_filter_is_half_open_ci_run() -> None:
    a = dt.datetime(2026, 10, 1, 0, 0, tzinfo=UTC)
    f = shard_filter(a, a + dt.timedelta(hours=6), 'meta.parent_uuid in ["p"]')
    assert "meta.create_time>=date(2026-10-01T00:00:00Z)" in f
    assert "meta.create_time<date(2026-10-01T06:00:00Z)" in f
    assert 'context.type=="CONTEXT_TYPE_CI_RUN"' in f
    assert f.endswith('meta.parent_uuid in ["p"]')


def _row(
    uuid: str, when: str, project: str, tags: list[str], spec: dict[str, Any]
) -> dict[str, Any]:
    return {
        "uuid": uuid,
        "meta": {"create_time": when, "parent_uuid": project},
        "context": {"id": f"ctx-{uuid}", "tags": tags},
        "spec": spec,
    }


def _client(rows: list[dict[str, Any]]) -> MagicMock:
    """list_iter returns only rows inside the filter's half-open window."""

    def list_iter(**kw: Any) -> list[dict[str, Any]]:
        lo, hi = re.findall(r"date\(([^)]+)\)", kw["filter"])
        out = [r for r in rows if lo <= r["meta"]["create_time"] < hi]
        clause = re.search(r"meta\.parent_uuid in \[(.*?)\]", kw["filter"])
        if clause:
            allowed = set(re.findall(r'"([^"]+)"', clause.group(1)))
            out = [r for r in out if r["meta"]["parent_uuid"] in allowed]
        return out

    client = MagicMock()
    client.ScanResult.list_iter.side_effect = list_iter
    return client


SINCE = dt.datetime(2026, 10, 20, 0, 0, tzinfo=UTC)
UNTIL = dt.datetime(2026, 10, 22, 0, 0, tzinfo=UTC)

ROWS = [
    # PR 1 in proj A scanned twice (tag), second scan blocked.
    _row("s1", "2026-10-20T00:00:00Z", "A", ["pr=1"], _spec()),
    _row(
        "s2",
        "2026-10-20T12:00:00Z",
        "A",
        ["pr=1"],
        _spec(exit_code="ENDORCTL_RC_POLICY_VIOLATION"),
    ),
    # PR 2 in proj A, no tags: only SCMPRID.
    _row("s3", "2026-10-21T05:00:00Z", "A", [], _spec("2")),
    # PR 1 in proj B is a different PR from PR 1 in proj A.
    _row("s4", "2026-10-21T23:59:59Z", "B", ["pr=1"], _spec(status="STATUS_FAILURE")),
    # CI runs that are NOT pull requests.
    _row(
        "s5", "2026-10-20T12:00:00Z", "A", ["merge-to-main", "check_run=9"], _spec("")
    ),
    _row(
        "s6",
        "2026-10-21T00:00:00Z",
        "B",
        ["merge-to-main"],
        _spec("0", blocking_findings=["f9"]),
    ),
    # Outside the window (exclusive end) must not count.
    _row("s7", "2026-10-22T00:00:00Z", "A", ["pr=77"], _spec()),
]


@pytest.mark.parametrize("shard_hours", [1, 5, 12, 24, 48])
def test_collect_counts_only_pr_scans_for_any_sharding(shard_hours: int) -> None:
    stats = collect_pr_scan_stats(
        _client(ROWS),
        namespace="t",
        since=SINCE,
        until=UNTIL,
        shard_hours=shard_hours,
        max_workers=4,
    )
    assert stats.pr_scans == 4
    assert stats.distinct_prs == 3
    assert stats.pr_scans_ok == 3
    assert stats.blocked_prs == 1
    assert stats.blocked_pr_scans == 1
    assert stats.ci_runs_without_pr == 2
    assert stats.blocked_ci_runs == 1
    assert stats.non_pr_tag_counts == {"merge-to-main": 2}
    assert stats.pr_scans_by_type == {"TYPE_ALL_SCANS": 4}
    assert stats.pr_keys == {("A", "1"), ("A", "2"), ("B", "1")}


def test_daily_series_counts_prs_on_first_scan_day() -> None:
    stats = collect_pr_scan_stats(
        _client(ROWS), namespace="t", since=SINCE, until=UNTIL
    )
    by_day = {d["date"]: d["prs"] for d in stats.daily}
    assert by_day["2026-10-20"] == 1  # PR A/1 (first scanned the 20th)
    assert by_day["2026-10-21"] == 2  # PR A/2 and PR B/1
    assert stats.active_days == 2


def test_project_scope_limits_counts() -> None:
    stats = collect_pr_scan_stats(
        _client(ROWS), namespace="t", since=SINCE, until=UNTIL, project_uuids=["A"]
    )
    assert stats.pr_scans == 3
    assert stats.distinct_prs == 2
    assert stats.ci_runs_without_pr == 1


def test_window_longer_than_retention_is_rejected() -> None:
    with pytest.raises(ValueError, match="22 days"):
        collect_pr_scan_stats(
            MagicMock(), namespace="t", since=UNTIL - dt.timedelta(days=30), until=UNTIL
        )


def test_window_floored_to_midnight_of_21_days_ago_is_accepted() -> None:
    until = dt.datetime(2026, 10, 28, 18, 0, tzinfo=UTC)
    since = (until - dt.timedelta(days=21)).replace(hour=0)
    stats = collect_pr_scan_stats(_client([]), namespace="t", since=since, until=until)
    assert stats.pr_scans == 0
    assert stats.window_days == 21


def test_naive_datetimes_are_rejected() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        collect_pr_scan_stats(
            MagicMock(),
            namespace="t",
            since=dt.datetime(2026, 10, 1),
            until=dt.datetime(2026, 10, 2),
        )
