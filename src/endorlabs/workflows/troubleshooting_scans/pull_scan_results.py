"""List ScanResults for a project with a bounded create-time window (default 7 days).

Uses ``ScanResult.list_by_project`` with ``from_date`` / ``to_date`` for server-side
filtering instead of unbounded lists.
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any

import endorlabs
from endorlabs.core.types import ListParameters
from endorlabs.tools.list_bounds import (
    is_list_truncated,
    resolve_max_pages,
)
from endorlabs.utils.namespace import resource_namespace

from .common import (
    date_window_from_bounds,
    object_to_dict,
    resolve_troubleshooting_output_dir,
    root_tenant,
    scan_result_extended_summary,
    write_json,
)
from .manifest_extract import (
    app_project_url,
    app_scan_history_url,
    extract_project_profile_refs,
    select_latest_scan_pair_by_type,
)


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Pull ScanResults for a project in a date window"
    )
    p.add_argument(
        "--tenant", required=True, help="Root tenant namespace (Client tenant)"
    )
    p.add_argument(
        "--project-uuid", required=True, help="Project UUID from search_projects"
    )
    p.add_argument(
        "--namespace",
        default=None,
        help="Namespace for Project.get / list (default: --tenant)",
    )
    p.add_argument(
        "--days",
        type=int,
        default=7,
        help="Lookback days when from/to not set (default 7)",
    )
    p.add_argument(
        "--from-date", default=None, help="ISO8601 lower bound (meta.create_time)"
    )
    p.add_argument("--to-date", default=None, help="ISO8601 upper bound")
    p.add_argument(
        "--max-pages",
        type=int,
        default=0,
        help="Max pages for ScanResult list (0 = unlimited within date window).",
    )
    p.add_argument("--page-size", type=int, default=100)
    p.add_argument(
        "--output-dir",
        default=None,
        help=(
            "Directory for generated artifacts (default: "
            ".endorlabs/tasks/<slug>-<YYYY-MM-DD>/troubleshooting/)."
        ),
    )
    p.add_argument("--timestamped", action="store_true")
    return p


def run(args: argparse.Namespace) -> dict[str, Any]:
    """Execute workflow from parsed CLI args."""
    rt = root_tenant(args.tenant)
    ns = args.namespace or args.tenant
    from_d, to_d = date_window_from_bounds(
        from_date=args.from_date,
        to_date=args.to_date,
        days=args.days,
    )

    client = endorlabs.Client(tenant=args.tenant)
    try:
        project = client.Project.get(args.project_uuid, namespace=ns)
        list_ns = resource_namespace(project) or ns

        lp = ListParameters(
            from_date=from_d,
            to_date=to_d,
            sort_by="meta.create_time",
            desc=True,
            page_size=args.page_size,
        )
        list_max_pages = resolve_max_pages(args.max_pages)
        scans = client.ScanResult.list_by_project(
            project,
            namespace=list_ns,
            list_params=lp,
            max_pages=list_max_pages,
        )
    finally:
        client.close()

    raw_list = [object_to_dict(s) for s in scans]
    list_truncated = is_list_truncated(
        len(raw_list),
        max_pages=list_max_pages,
        page_size=args.page_size,
    )
    summaries = [scan_result_extended_summary(d) for d in raw_list]
    project_profiles = extract_project_profile_refs(object_to_dict(project))
    dual = select_latest_scan_pair_by_type(raw_list)
    # Drop full scan bodies from dual pair; keep UUIDs + summary pointers
    dual_compact: dict[str, Any] = {
        "citation_priority": dual["citation_priority"],
        "analytics_uuid": dual["analytics_uuid"],
        "analytics_type": dual["analytics_type"],
        "full_sca_uuid": dual["full_sca_uuid"],
        "full_sca_type": dual["full_sca_type"],
    }
    ns_for_urls = str(project_profiles.get("namespace") or list_ns)
    if dual["analytics_uuid"]:
        dual_compact["analytics_app_url"] = app_scan_history_url(
            namespace=ns_for_urls, scan_result_uuid=str(dual["analytics_uuid"])
        )
    if dual["full_sca_uuid"]:
        dual_compact["full_sca_app_url"] = app_scan_history_url(
            namespace=ns_for_urls, scan_result_uuid=str(dual["full_sca_uuid"])
        )
    # Attach discovered_manifests from matching summaries
    summary_by_uuid = {
        str(s.get("uuid")): s for s in summaries if s.get("uuid") is not None
    }
    for role, uuid_key in (
        ("analytics", "analytics_uuid"),
        ("full_sca", "full_sca_uuid"),
    ):
        uid = dual_compact.get(uuid_key)
        if not uid:
            continue
        summary = summary_by_uuid.get(str(uid))
        if summary:
            dual_compact[f"{role}_discovered_manifests"] = summary.get(
                "discovered_manifests"
            )
            dual_compact[f"{role}_config_allowlist"] = summary.get("config_allowlist")
            dual_compact[f"{role}_toolchains"] = summary.get("toolchains")

    payload: dict[str, Any] = {
        "root_tenant": rt,
        "query_tenant": args.tenant,
        "list_namespace": list_ns,
        "project_uuid": args.project_uuid,
        "project_app_url": app_project_url(
            namespace=ns_for_urls, project_uuid=str(args.project_uuid)
        ),
        "project_profile_refs": project_profiles,
        "dual_scan_pair": dual_compact,
        "window": {"from_date": from_d, "to_date": to_d},
        "scan_result_count": len(raw_list),
        "list_truncated": list_truncated,
        "list_max_pages": args.max_pages,
        "scan_results": raw_list,
        "scan_results_summary": summaries,
    }
    path = write_json(
        output_dir=resolve_troubleshooting_output_dir(
            args.tenant or args.namespace, args.output_dir
        ),
        root_tenant_name=rt,
        object_kind="scan_results",
        object_uuid=args.project_uuid,
        purpose="windowed",
        payload=payload,
        timestamped=args.timestamped,
    )
    payload["artifact"] = str(path)
    return payload


def main() -> int:
    """Run the module CLI and return exit code."""
    args = _build_parser().parse_args()
    try:
        result = run(args)
    except ValueError as e:
        print(json.dumps({"error": str(e)}), file=sys.stderr)
        return 1
    print(result["artifact"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
