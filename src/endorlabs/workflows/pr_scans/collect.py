"""Pull-request scan statistics from ``ScanResult`` (time-sharded, parallel).

A **PR scan** is a ``CONTEXT_TYPE_CI_RUN`` scan that carries a pull-request
number: the ``pr=<n>`` context tag or, when a CI setup records no tags, the
scan config's ``ScanConfig.SCMPRID``. Every other CI run (for example a
``merge-to-main`` run) is *not* a PR scan; it is counted separately in
``ci_runs_without_pr`` so the two can never be mixed up.

Only ``ScanResult`` is read. No ``Finding`` rows are listed: on large tenants
CI-run findings number in the millions and the row listing does not finish.
"""

from __future__ import annotations

import datetime as dt
from collections import Counter
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, cast

from endorlabs.tools.list_bounds import resolve_collect_max_workers
from endorlabs.tools.parallel_scopes import parallel_over
from endorlabs.utils.logging_config import get_resource_logger
from endorlabs.workflows.common import WorkflowResult

if TYPE_CHECKING:
    from endorlabs.client_surface import Client

LOGGER = get_resource_logger(__name__)

# ScanResult records carry will_be_deleted_at = create_time + 22 days, so a
# window reaching further back than that cannot be answered from the API.
RETENTION_DAYS = 22
CI_RUN_FILTER = 'context.type=="CONTEXT_TYPE_CI_RUN"'
POLICY_VIOLATION_RC = "ENDORCTL_RC_POLICY_VIOLATION"
SUCCESS_STATUSES = frozenset({"STATUS_SUCCESS", "STATUS_PARTIAL_SUCCESS"})
# Never fetch the whole scan config: it can hold credentials. The mask names
# only SCMPRID.
PR_SCAN_MASK = (
    "uuid,meta.create_time,meta.parent_uuid,context.id,context.tags,"
    "spec.type,spec.status,spec.exit_code,spec.blocking_findings,"
    "spec.environment.config.ScanConfig.SCMPRID"
)
# 250 uuids x ~28 characters is about 7 KB; a filter with thousands of uuids
# fails with "URL component 'query' too long".
PROJECT_CHUNK = 250

PrKey = tuple[str, str]  # (project uuid, PR number)


def _obj(value: object) -> Mapping[str, Any]:
    """*value* when it is a JSON object, else an empty mapping."""
    return cast("Mapping[str, Any]", value) if isinstance(value, Mapping) else {}


def pr_number(
    tags: Sequence[str] | None, spec: Mapping[str, Any] | None = None
) -> str | None:
    """PR number of a CI-run scan, or ``None`` when it is not a PR scan.

    The ``pr=<n>`` context tag wins; otherwise ``ScanConfig.SCMPRID``. An empty
    or ``"0"`` value is not a PR number.
    """
    for tag in tags or ():
        if tag.startswith("pr="):
            value = tag.split("=", 1)[1]
            if value not in ("", "0"):
                return value
    environment = _obj(_obj(spec).get("environment"))
    config = _obj(_obj(environment.get("config")).get("ScanConfig"))
    pr_id: object = config.get("SCMPRID")
    return str(pr_id) if pr_id not in (None, "", "0") else None


def is_blocked(spec: Mapping[str, Any] | None) -> bool:
    """Scan stopped by an enforcing policy.

    The platform records ``blocking_findings`` or the policy-violation exit
    code only for action policies with enforcement ON, so warn-only policies
    never produce a blocked scan.
    """
    body = _obj(spec)
    return (
        bool(body.get("blocking_findings"))
        or body.get("exit_code") == POLICY_VIOLATION_RC
    )


def _iso(when: dt.datetime) -> str:
    return when.astimezone(dt.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def time_windows(
    since: dt.datetime, until: dt.datetime, shard_hours: int
) -> list[tuple[dt.datetime, dt.datetime]]:
    """Half-open ``[start, end)`` windows covering ``[since, until)`` exactly."""
    if shard_hours < 1:
        raise ValueError("shard_hours must be >= 1")
    step = dt.timedelta(hours=shard_hours)
    out: list[tuple[dt.datetime, dt.datetime]] = []
    start = since
    while start < until:
        end = min(start + step, until)
        out.append((start, end))
        start = end
    return out


def project_clauses(
    project_uuids: Sequence[str] | None, chunk: int = PROJECT_CHUNK
) -> list[str | None]:
    """``meta.parent_uuid in [...]`` clauses (a ScanResult's parent is its project).

    ``None`` entries mean "no project restriction". Chunks are disjoint, so
    results from different chunks never overlap.
    """
    if project_uuids is None:
        return [None]
    uuids = list(dict.fromkeys(project_uuids))
    if not uuids:
        raise ValueError("empty project scope: no project uuids given")
    return [
        "meta.parent_uuid in ["
        + ", ".join(f'"{u}"' for u in uuids[i : i + chunk])
        + "]"
        for i in range(0, len(uuids), chunk)
    ]


def shard_filter(
    start: dt.datetime, end: dt.datetime, project_clause: str | None
) -> str:
    """ScanResult filter for one half-open window of CI-run scans."""
    base = (
        f"meta.create_time>=date({_iso(start)}) and "
        f"meta.create_time<date({_iso(end)}) and {CI_RUN_FILTER}"
    )
    return f"{base} and {project_clause}" if project_clause else base


@dataclass(frozen=True, slots=True)
class _Scan:
    """The few fields of one PR scan that the statistics need."""

    pr: PrKey
    date: str
    ok: bool
    blocked: bool
    type: str


@dataclass
class _ShardOut:
    """What one time-window shard contributes; merged on the calling thread."""

    scans: dict[str, _Scan] = field(default_factory=dict[str, _Scan])
    ci_without_pr: int = 0
    blocked_ci_runs: int = 0
    non_pr_tags: Counter[str] = field(default_factory=Counter[str])
    blocked_finding_ids: set[str] = field(default_factory=set[str])


@dataclass
class PrScanStats(WorkflowResult):
    """Pull-request scan statistics for a window.

    ``pr_scans`` counts scans that carry a PR number; ``distinct_prs`` counts
    ``(project, PR number)`` pairs, which is lower whenever a PR is scanned more
    than once. ``ci_runs_without_pr`` are CI runs with no PR number.
    """

    namespace: str = ""
    since: str = ""
    until: str = ""
    window_days: int = 0
    shards: int = 0
    pr_scans: int = 0
    pr_scans_ok: int = 0
    distinct_prs: int = 0
    active_days: int = 0
    blocked_prs: int = 0
    blocked_pr_scans: int = 0
    blocked_findings: int = 0
    ci_runs_without_pr: int = 0
    blocked_ci_runs: int = 0
    pr_scans_by_type: dict[str, int] = field(default_factory=dict[str, int])
    non_pr_tag_counts: dict[str, int] = field(default_factory=dict[str, int])
    daily: list[dict[str, Any]] = field(default_factory=list[dict[str, Any]])
    # Distinct PRs by key, for callers that join further data to PRs.
    pr_keys: set[PrKey] = field(default_factory=set[PrKey])


def _scan_shard(
    client: Client,
    namespace: str,
    start: dt.datetime,
    end: dt.datetime,
    clause: str | None,
) -> _ShardOut:
    out = _ShardOut()
    rows = client.ScanResult.list_iter(
        namespace=namespace,
        traverse=True,
        filter=shard_filter(start, end, clause),
        mask=PR_SCAN_MASK,
    )
    for row in rows:
        row_map = _obj(row)
        meta = _obj(row_map.get("meta"))
        spec = _obj(row_map.get("spec"))
        raw_tags = _obj(row_map.get("context")).get("tags")
        tags = (
            [str(t) for t in cast("list[object]", raw_tags)]
            if isinstance(raw_tags, list)
            else []
        )
        blocked = is_blocked(spec)
        pr = pr_number(tags, spec)
        blocking = spec.get("blocking_findings")
        if pr is None:
            out.ci_without_pr += 1
            out.blocked_ci_runs += blocked
            # Bare tags (no "=") name the CI trigger, for example "merge-to-main".
            out.non_pr_tags.update(t for t in tags if "=" not in t)
            continue
        if isinstance(blocking, list):
            out.blocked_finding_ids.update(
                str(f) for f in cast("list[object]", blocking)
            )
        out.scans[str(row_map.get("uuid"))] = _Scan(
            pr=(str(meta.get("parent_uuid") or ""), pr),
            date=str(meta.get("create_time") or "")[:10],
            ok=spec.get("status") in SUCCESS_STATUSES,
            blocked=blocked,
            type=str(spec.get("type") or "TYPE_UNSPECIFIED"),
        )
    return out


def _day_range(since: dt.datetime, until: dt.datetime) -> Iterator[str]:
    day = since.astimezone(dt.UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    while day <= until:
        yield day.strftime("%Y-%m-%d")
        day += dt.timedelta(days=1)


def collect_pr_scan_stats(
    client: Client,
    *,
    namespace: str,
    since: dt.datetime,
    until: dt.datetime,
    project_uuids: Sequence[str] | None = None,
    shard_hours: int = 12,
    max_workers: int | None = None,
) -> PrScanStats:
    """PR scan statistics for ``[since, until)`` from ``ScanResult`` only.

    ``namespace`` is listed with ``traverse=True``. ``project_uuids`` limits the
    count to those projects (server-side, in chunks). The window is split into
    ``shard_hours`` windows that run in parallel (``max_workers`` threads);
    windows are half-open, so a scan is counted in exactly one of them.
    """
    if until.tzinfo is None or since.tzinfo is None:
        raise ValueError("since and until must be timezone-aware")
    if until - since > dt.timedelta(days=RETENTION_DAYS):
        raise ValueError(
            f"window exceeds {RETENTION_DAYS} days: ScanResult records are deleted "
            f"{RETENTION_DAYS} days after creation"
        )
    windows = time_windows(since, until, shard_hours)
    clauses = project_clauses(project_uuids)
    shards = [(s, e, c) for (s, e) in windows for c in clauses]
    workers = resolve_collect_max_workers(max_workers)
    LOGGER.info(
        "pr scans: %d shards (%d windows x %d project chunks), %d workers",
        len(shards),
        len(windows),
        len(clauses),
        workers,
    )

    scans: dict[str, _Scan] = {}
    blocked_findings: set[str] = set()
    result = PrScanStats(
        namespace=namespace,
        since=_iso(since),
        until=_iso(until),
        window_days=(until - since).days,
        shards=len(shards),
    )
    non_pr_tags: Counter[str] = Counter()
    for shard in parallel_over(
        shards,
        lambda s: _scan_shard(client, namespace, s[0], s[1], s[2]),
        max_workers=workers,
    ):
        scans.update(shard.scans)
        blocked_findings |= shard.blocked_finding_ids
        non_pr_tags.update(shard.non_pr_tags)
        result.ci_runs_without_pr += shard.ci_without_pr
        result.blocked_ci_runs += shard.blocked_ci_runs

    first_day: dict[PrKey, str] = {}
    blocked_prs: set[PrKey] = set()
    types: Counter[str] = Counter()
    for scan in scans.values():
        pr = scan.pr
        first_day[pr] = min(first_day.get(pr, scan.date), scan.date)
        types[scan.type] += 1
        if scan.blocked:
            blocked_prs.add(pr)
    per_day = Counter(first_day.values())

    result.pr_scans = len(scans)
    result.pr_scans_ok = sum(1 for s in scans.values() if s.ok)
    result.pr_keys = set(first_day)
    result.distinct_prs = len(first_day)
    result.blocked_prs = len(blocked_prs)
    result.blocked_pr_scans = sum(1 for s in scans.values() if s.blocked)
    result.blocked_findings = len(blocked_findings)
    result.pr_scans_by_type = dict(types)
    result.non_pr_tag_counts = dict(non_pr_tags.most_common(10))
    result.daily = [
        {"date": d, "prs": per_day.get(d, 0)} for d in _day_range(since, until)
    ]
    result.active_days = sum(1 for d in result.daily if d["prs"])
    result.message = (
        f"{result.pr_scans} PR scans / {result.distinct_prs} distinct PRs; "
        f"{result.ci_runs_without_pr} CI runs without a PR number excluded"
    )
    return result
