"""Load Finding dicts for a GitHub PR via Endor API.

Primary flow: Project -> RepositoryVersion -> ScanResult -> Finding.get
"""

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
    from endorlabs.resources.repository_version import RepositoryVersion
    from endorlabs.resources.scan_result import ScanResult, ScanResultSpec

# Poll until ScanResult is ready after the GitHub Action completes.
_DEFAULT_POLL_TIMEOUT_SEC = 120.0
_DEFAULT_POLL_INTERVAL_MAX = 10.0
_DEFAULT_MAX_FINDINGS = 500
_TRAVERSE_PAGE_SIZE = 50
_MAX_SCAN_LIST_PAGES = 5


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


def list_repository_versions_for_project(
    client: endorlabs.Client,
    *,
    project: Project,
    namespace: str | None,
    max_pages: int = 3,
) -> list[RepositoryVersion]:
    """List repository versions for a project, newest first."""
    try:
        rows = client.RepositoryVersion.list(
            parent=project,
            traverse=True,
            page_size=_TRAVERSE_PAGE_SIZE,
            max_pages=max_pages,
            namespace=namespace,
        )
    except Exception:
        # Fallback for environments where parent=project is unavailable.
        rows = client.RepositoryVersion.list(
            list_params=ListParameters(
                filter=f'meta.parent_uuid=="{project.uuid}"',
                traverse=True,
                page_size=_TRAVERSE_PAGE_SIZE,
            ),
            max_pages=max_pages,
            namespace=namespace,
        )
    return _sort_scan_results_newest_first(rows)  # same meta.create_time strategy


def _version_ref(v: RepositoryVersion) -> str:
    spec = getattr(v, "spec", None)
    ver = getattr(spec, "version", None) if spec is not None else None
    ref = getattr(ver, "ref", None) if ver is not None else None
    return str(ref).strip() if isinstance(ref, str) else ""


def _version_sha(v: RepositoryVersion) -> str:
    spec = getattr(v, "spec", None)
    ver = getattr(spec, "version", None) if spec is not None else None
    sha = getattr(ver, "sha", None) if ver is not None else None
    return str(sha).strip() if isinstance(sha, str) else ""


def _match_repository_version_hint(
    versions: list[RepositoryVersion], hint: str
) -> tuple[RepositoryVersion | None, str]:
    for rv in versions:
        rv_uuid = getattr(rv, "uuid", None)
        if isinstance(rv_uuid, str) and rv_uuid.lower() == hint:
            return rv, "hint:uuid"
    for rv in versions:
        if _version_sha(rv).lower() == hint:
            return rv, "hint:sha"
    for rv in versions:
        if _version_ref(rv).lower() == hint:
            return rv, "hint:ref"
    return None, "none"


def _match_repository_version_sha(
    versions: list[RepositoryVersion], want_sha: str
) -> RepositoryVersion | None:
    for rv in versions:
        sha = _version_sha(rv)
        if sha and sha.lower() == want_sha:
            return rv
    return None


def _match_repository_version_ref(
    versions: list[RepositoryVersion], want_ref: str
) -> RepositoryVersion | None:
    for rv in versions:
        if _version_ref(rv) == want_ref:
            return rv
    return None


def resolve_repository_version(
    versions: list[RepositoryVersion],
    *,
    head_sha: str,
    head_ref: str,
    repository_version_hint: str | None,
) -> tuple[RepositoryVersion | None, str]:
    """Resolve repository version by hint, sha, then ref."""
    if not versions:
        return None, "none"
    hint = (repository_version_hint or "").strip().lower()
    want_sha = head_sha.strip().lower()
    want_ref = head_ref.strip()

    if hint:
        rv, strategy = _match_repository_version_hint(versions, hint)
        if rv is not None:
            return rv, strategy

    if want_sha:
        rv = _match_repository_version_sha(versions, want_sha)
        if rv is not None:
            return rv, "sha"

    if want_ref:
        rv = _match_repository_version_ref(versions, want_ref)
        if rv is not None:
            return rv, "ref"

    return versions[0], "newest"


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


def pick_scan_result_for_repository_version(
    scan_results: list[ScanResult],
    *,
    repository_version: RepositoryVersion | None,
    head_sha: str,
    head_ref: str,
) -> ScanResult | None:
    """Pick terminal scan result that best matches repository version identity."""
    if not scan_results:
        return None
    if repository_version is None:
        return pick_scan_result(scan_results, head_sha)

    rv_sha = _version_sha(repository_version).lower()
    rv_ref = _version_ref(repository_version)
    want_sha = head_sha.strip().lower()
    want_ref = head_ref.strip()

    matches = [
        sr
        for sr in scan_results
        if _scan_result_matches_identity(
            sr,
            rv_sha=rv_sha,
            rv_ref=rv_ref,
            want_sha=want_sha,
            want_ref=want_ref,
        )
    ]
    if not matches:
        return pick_scan_result(scan_results, head_sha)
    for sr in matches:
        sp = sr.spec
        if sp and sp.type == ScanResultSpecType.PR_SECURITY_REVIEW:
            return sr
    return matches[0]


def _sort_scan_results_newest_first(rows: list[ScanResult]) -> list[ScanResult]:
    """Order by meta.create_time descending (ISO timestamps sort lexicographically)."""

    def create_time_key(sr: ScanResult) -> tuple[int, str]:
        meta = getattr(sr, "meta", None)
        ct = getattr(meta, "create_time", None) if meta is not None else None
        if isinstance(ct, str) and ct:
            return (1, ct)
        return (0, "")

    return sorted(rows, key=create_time_key, reverse=True)


def _scan_version_pairs(sr: ScanResult) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    spec = sr.spec
    if not spec or not spec.versions:
        return out
    for ver in spec.versions:
        sha = getattr(ver, "sha", None)
        ref = getattr(ver, "ref", None)
        out.append(
            (
                str(sha).strip().lower() if isinstance(sha, str) else "",
                str(ref).strip() if isinstance(ref, str) else "",
            )
        )
    return out


def _scan_result_matches_identity(
    sr: ScanResult,
    *,
    rv_sha: str,
    rv_ref: str,
    want_sha: str,
    want_ref: str,
) -> bool:
    for sha, ref in _scan_version_pairs(sr):
        if rv_sha and sha and sha == rv_sha:
            return True
        if rv_ref and ref and ref == rv_ref:
            return True
        if want_sha and sha and sha == want_sha:
            return True
        if want_ref and ref and ref == want_ref:
            return True
    return False


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
    head_ref: str = "",
    repository_version_hint: str | None = None,
    tenant: str | None = None,
    poll_timeout_sec: float = _DEFAULT_POLL_TIMEOUT_SEC,
    max_findings: int = _DEFAULT_MAX_FINDINGS,
) -> list[dict[str, Any]]:
    """Resolve Project -> RepositoryVersion -> ScanResult -> Finding.get for PR head."""
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
            versions = list_repository_versions_for_project(
                client, project=project, namespace=p_ns
            )
            repo_version, match_strategy = resolve_repository_version(
                versions,
                head_sha=head_sha,
                head_ref=head_ref,
                repository_version_hint=repository_version_hint,
            )
            if repo_version is not None:
                rv_uuid = getattr(repo_version, "uuid", None) or "unknown"
                rv_ref = _version_ref(repo_version) or "unknown"
                rv_sha = _version_sha(repo_version) or "unknown"
                print(
                    "RepositoryVersion resolved: "
                    f"uuid={rv_uuid}, ref={rv_ref}, sha={rv_sha}, "
                    f"strategy={match_strategy}",
                    file=sys.stderr,
                )
            else:
                print(
                    "No RepositoryVersion rows found; falling back to "
                    "ScanResult matching only.",
                    file=sys.stderr,
                )
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
            picked = pick_scan_result_for_repository_version(
                scan_rows,
                repository_version=repo_version,
                head_sha=head_sha,
                head_ref=head_ref,
            )
            if not picked:
                return []
            scan_uuid = getattr(picked, "uuid", None) or "unknown"
            print(
                f"ScanResult {scan_uuid}: using "
                "ScanResult finding UUIDs + Finding.get.",
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
