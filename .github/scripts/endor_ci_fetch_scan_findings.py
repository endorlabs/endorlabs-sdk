"""Load Finding dicts for a GitHub PR via Endor API (Project, ScanResult, Finding)."""

from __future__ import annotations

import os
import sys
import time
from typing import TYPE_CHECKING, Any

import endorlabs
from endorlabs.core.types import ListParameters
from endorlabs.resources.scan_result import ScanResultSpecStatus, ScanResultSpecType

if TYPE_CHECKING:
    from endorlabs.resources.project import Project
    from endorlabs.resources.scan_result import ScanResult, ScanResultSpec

# Poll until ScanResult is ready after the GitHub Action completes.
_DEFAULT_POLL_TIMEOUT_SEC = 120.0
_DEFAULT_POLL_INTERVAL_MAX = 10.0
_DEFAULT_MAX_FINDINGS = 500
_TRAVERSE_PAGE_SIZE = 50
_MAX_SCAN_LIST_PAGES = 5
# OpenAPI Finding list max page_size is 500.
_FINDING_LIST_PAGE_SIZE = 500


def github_repo_url_variants(repo: str) -> list[str]:
    """Return canonical https URLs tried for Project.meta.name lookup."""
    repo = repo.strip()
    if not repo or "/" not in repo:
        return []
    base = f"https://github.com/{repo}"
    return list(dict.fromkeys([f"{base}.git", base]))


def _project_namespace(project: Project) -> str | None:
    if project.tenant_meta and getattr(project.tenant_meta, "namespace", None):
        return str(project.tenant_meta.namespace)
    return os.getenv("ENDOR_NAMESPACE")


def find_project_by_repo(
    client: endorlabs.Client, repo: str, *, max_pages: int = 3
) -> Project | None:
    """Return first Project whose meta.name matches a GitHub URL variant."""
    for url in github_repo_url_variants(repo):
        if not url:
            continue
        try:
            projects = client.Project.list(
                list_params=ListParameters(
                    filter=f'meta.name=="{url}"',
                    traverse=True,
                    page_size=_TRAVERSE_PAGE_SIZE,
                ),
                max_pages=max_pages,
            )
        except Exception as exc:
            print(f"Project list failed for {url!r}: {exc}", file=sys.stderr)
            continue
        if projects:
            return projects[0]
    return None


def _scan_result_terminal(spec: ScanResultSpec | None) -> bool:
    if not spec:
        return False
    return spec.status != ScanResultSpecStatus.RUNNING


def pick_scan_result(
    scan_results: list[ScanResult], head_sha: str
) -> ScanResult | None:
    """Pick ScanResult matching head_sha in spec.versions, else newest (first).

    When several results share the same head SHA, prefer
    ``TYPE_PR_SECURITY_REVIEW`` (PR Runs) over generic aggregate scan types.
    """
    if not scan_results:
        return None
    want = head_sha.strip().lower()

    def sha_matches(sr: ScanResult) -> bool:
        if not want:
            return False
        spec = sr.spec
        if not spec or not spec.versions:
            return False
        for ver in spec.versions:
            sha = getattr(ver, "sha", None)
            if isinstance(sha, str) and sha.lower() == want:
                return True
        return False

    if want:
        matches = [sr for sr in scan_results if sha_matches(sr)]
        if matches:
            for sr in matches:
                sp = sr.spec
                if sp and sp.type == ScanResultSpecType.PR_SECURITY_REVIEW:
                    return sr
            return matches[0]
    return scan_results[0]


def extract_ci_run_uuid_from_scan_result(spec: ScanResultSpec | None) -> str | None:
    """Best-effort PR context id for ``Finding.list`` (``list_parameters.ci_run_uuid``).

    Populated from ``spec.environment.config`` (endorctl scan config), e.g.
    ``ExecutionID`` — see platform docs / ScanResult environment model.
    """
    if not spec or not spec.environment:
        return None
    config = spec.environment.config
    if not isinstance(config, dict):
        return None
    for key in (
        "ExecutionID",
        "execution_id",
        "executionId",
        "ci_run_uuid",
        "CiRunUUID",
        "pr_uuid",
    ):
        raw = config.get(key)
        if isinstance(raw, str) and raw.strip():
            return raw.strip()
    return None


def finding_uuids_from_scan_result(spec: ScanResultSpec | None) -> list[str]:
    """UUIDs from spec.findings, else union of blocking + warning lists."""
    if not spec:
        return []
    out: list[str] = []
    if spec.findings:
        out.extend(spec.findings)
    else:
        if spec.blocking_findings:
            out.extend(spec.blocking_findings)
        if spec.warning_findings:
            out.extend(spec.warning_findings)
    seen: set[str] = set()
    deduped: list[str] = []
    for u in out:
        if u and u not in seen:
            seen.add(u)
            deduped.append(u)
    return deduped


def _sort_scan_results_newest_first(rows: list[ScanResult]) -> list[ScanResult]:
    """Order by meta.create_time descending (ISO timestamps sort lexicographically)."""

    def create_time_key(sr: ScanResult) -> tuple[int, str]:
        meta = getattr(sr, "meta", None)
        ct = getattr(meta, "create_time", None) if meta is not None else None
        if isinstance(ct, str) and ct:
            return (1, ct)
        return (0, "")

    return sorted(rows, key=create_time_key, reverse=True)


def list_scan_results_for_project(
    client: endorlabs.Client,
    project_uuid: str,
    *,
    namespace: str | None,
    max_pages: int = _MAX_SCAN_LIST_PAGES,
) -> list[ScanResult]:
    """List ScanResults for a project, newest first.

    Server-side ``sort`` combined with cursor pagination (``page_id``) returns
    HTTP 400 ("page id cannot be provided with sort method"). We list without
    sort and order client-side.
    """
    list_params = ListParameters(
        filter=f'meta.parent_uuid=="{project_uuid}"',
        traverse=True,
        page_size=_TRAVERSE_PAGE_SIZE,
    )
    rows = client.ScanResult.list(
        list_params=list_params,
        max_pages=max_pages,
        namespace=namespace,
    )
    return _sort_scan_results_newest_first(rows)


def wait_for_scan_result_ready(
    client: endorlabs.Client,
    project_uuid: str,
    head_sha: str,
    *,
    namespace: str | None,
    timeout_sec: float = _DEFAULT_POLL_TIMEOUT_SEC,
    interval_max: float = _DEFAULT_POLL_INTERVAL_MAX,
) -> list[ScanResult]:
    """Poll until picked ScanResult is terminal, or timeout."""
    deadline = time.monotonic() + timeout_sec
    interval = 1.0
    last: list[ScanResult] = []
    while time.monotonic() < deadline:
        try:
            last = list_scan_results_for_project(
                client, project_uuid, namespace=namespace
            )
        except Exception as exc:
            print(f"ScanResult list failed (will retry): {exc}", file=sys.stderr)
            last = []
        if last:
            picked = pick_scan_result(last, head_sha)
            if picked and picked.spec and _scan_result_terminal(picked.spec):
                return last
            if picked and picked.spec is None:
                return last
        sleep_for = min(interval, max(0.0, deadline - time.monotonic()))
        if sleep_for > 0:
            time.sleep(sleep_for)
        interval = min(interval * 2, interval_max)
    return last


def finding_to_github_dict(finding: Any) -> dict[str, Any]:
    """Serialize Finding for extract_location / level helpers used by GitHub scripts."""
    return finding.model_dump(mode="json")


def list_findings_for_ci_run(
    client: endorlabs.Client,
    *,
    ci_run_uuid: str,
    namespace: str | None,
    max_findings: int,
) -> list[dict[str, Any]]:
    """List findings scoped to a PR scan via OpenAPI ``list_parameters.ci_run_uuid``."""
    if not namespace:
        return []
    max_pages = max(
        1,
        (max_findings + _FINDING_LIST_PAGE_SIZE - 1) // _FINDING_LIST_PAGE_SIZE,
    )
    try:
        rows = client.Finding.list(
            list_params=ListParameters(
                ci_run_uuid=ci_run_uuid,
                traverse=True,
                page_size=_FINDING_LIST_PAGE_SIZE,
            ),
            max_pages=max_pages,
            namespace=namespace,
        )
    except Exception as exc:
        print(
            f"Finding.list(ci_run_uuid=...) failed: {exc}; "
            "will fall back to GET by UUID.",
            file=sys.stderr,
        )
        return []
    return [finding_to_github_dict(f) for f in rows[:max_findings]]


def hydrate_findings(
    client: endorlabs.Client,
    uuids: list[str],
    *,
    namespace: str | None,
    max_findings: int,
) -> list[dict[str, Any]]:
    """GET each Finding by UUID (cap max_findings)."""
    if not uuids or not namespace:
        return []
    out: list[dict[str, Any]] = []
    for uid in uuids[:max_findings]:
        try:
            got = client.Finding.get(uid, namespace=namespace)
        except Exception as exc:
            print(f"Finding.get {uid!r} failed: {exc}", file=sys.stderr)
            continue
        if got is not None:
            out.append(finding_to_github_dict(got))
    return out


def load_findings_dicts_for_pr(
    *,
    repo: str,
    head_sha: str,
    tenant: str | None = None,
    poll_timeout_sec: float = _DEFAULT_POLL_TIMEOUT_SEC,
    max_findings: int = _DEFAULT_MAX_FINDINGS,
) -> list[dict[str, Any]]:
    """Resolve Project → ScanResult → findings for the PR head commit.

    Prefer ``Finding.list(ci_run_uuid=...)`` when ``ExecutionID`` (or similar)
    is present on the picked ScanResult's environment config (PR Runs scope).
    Otherwise hydrate from ``spec.findings`` / blocking+warning UUID lists.

    Fail-open: logs to stderr and returns [] on missing project, API errors, or timeout.
    """
    ns = tenant or os.getenv("ENDOR_NAMESPACE")
    if not ns:
        print(
            "ENDOR_NAMESPACE is not set; cannot fetch findings via API.",
            file=sys.stderr,
        )
        return []
    try:
        with endorlabs.Client(tenant=ns) as client:
            project = find_project_by_repo(client, repo)
            if not project or not project.uuid:
                print(
                    f"No Endor Project found for GitHub repo {repo!r} "
                    f"(tried meta.name URL variants).",
                    file=sys.stderr,
                )
                return []
            p_ns = _project_namespace(project)
            proj_uuid = project.uuid
            scan_rows = wait_for_scan_result_ready(
                client,
                proj_uuid,
                head_sha,
                namespace=p_ns,
                timeout_sec=poll_timeout_sec,
            )
            if not scan_rows:
                print(
                    f"No ScanResult rows for project {proj_uuid}; "
                    "skipping API findings.",
                    file=sys.stderr,
                )
                return []
            picked = pick_scan_result(scan_rows, head_sha)
            if not picked:
                return []
            scan_uuid = getattr(picked, "uuid", None) or "unknown"
            ci_run = extract_ci_run_uuid_from_scan_result(picked.spec)
            if ci_run:
                print(
                    f"ScanResult {scan_uuid}: using Finding.list scoped to "
                    f"ci_run_uuid (PR context).",
                    file=sys.stderr,
                )
                listed = list_findings_for_ci_run(
                    client,
                    ci_run_uuid=ci_run,
                    namespace=p_ns,
                    max_findings=max_findings,
                )
                if listed:
                    return listed
                print(
                    "Finding.list returned no rows; falling back to "
                    "ScanResult finding UUIDs + Finding.get.",
                    file=sys.stderr,
                )
            else:
                print(
                    f"ScanResult {scan_uuid}: no ci_run_uuid in environment.config; "
                    "using ScanResult finding UUIDs + Finding.get.",
                    file=sys.stderr,
                )

            uuids = finding_uuids_from_scan_result(picked.spec)
            if not uuids:
                print(
                    "Selected ScanResult has no finding UUIDs in spec; "
                    "nothing to hydrate.",
                    file=sys.stderr,
                )
                return []
            n_hydrate = min(len(uuids), max_findings)
            print(
                f"Hydrating {n_hydrate} finding(s) via Finding.get.",
                file=sys.stderr,
            )
            return hydrate_findings(
                client,
                uuids,
                namespace=p_ns,
                max_findings=max_findings,
            )
    except Exception as exc:
        print(f"load_findings_dicts_for_pr failed: {exc}", file=sys.stderr)
        return []
