"""Resolve project scope: name, UUID, ScanResult, or Endor app URL.

Uses traverse-aware ``ScanResult.get`` from the tenant root when resolving scan UUIDs
so a mistyped namespace in a copy-pasted URL still works.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import endorlabs
from endorlabs.workflows.projects.resolve import (
    resolve_project as canonical_resolve_project,
)
from endorlabs.workflows.projects.resolve import (
    search_projects_by_name_or_uuid,
)

from .common import (
    duplicate_project_decision,
    parse_app_scan_history_url,
    parse_endor_app_url,
    root_tenant,
    write_json,
)


def _dump(obj: Any) -> dict[str, Any]:
    if hasattr(obj, "model_dump"):
        return obj.model_dump(mode="json")
    return {}


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Resolve project(s) for troubleshooting from name, URL, or UUID."
    )
    p.add_argument(
        "--tenant",
        required=True,
        help="Root tenant for Client (first segment; same as ENDOR_* / SDK context).",
    )
    p.add_argument(
        "--namespace",
        default=None,
        help="Optional namespace hint for Project.get when using --project-uuid",
    )
    p.add_argument("--project-name", default=None, help="Substring match (traverse)")
    p.add_argument("--project-uuid", default=None, help="Exact project UUID")
    p.add_argument(
        "--scan-result-url",
        default=None,
        help="App URL .../t/{ns}/scan-history/{scan_result_uuid}",
    )
    p.add_argument(
        "--scan-result-uuid",
        default=None,
        help="ScanResult UUID (traverse get)",
    )
    p.add_argument(
        "--endor-app-url",
        default=None,
        help=(
            "app.endorlabs.com URL: .../scan-history/{uuid} or .../projects/{uuid}/... "
            "(routing only; --tenant still required)"
        ),
    )
    p.add_argument("--output-dir", default=".tmp")
    p.add_argument("--timestamped", action="store_true")
    return p


def _exactly_one(**kwargs: bool) -> None:
    set_flags = [k for k, v in kwargs.items() if v]
    if len(set_flags) != 1:
        raise ValueError(
            "Provide exactly one of: --endor-app-url, --project-name, --project-uuid, "
            "--scan-result-url, --scan-result-uuid"
        )


def _apply_endor_app_url(args: argparse.Namespace) -> None:
    """Apply ``--endor-app-url`` into project or scan-history selectors."""
    if not getattr(args, "endor_app_url", None):
        return
    if any(
        [
            args.project_name,
            args.project_uuid,
            args.scan_result_url,
            args.scan_result_uuid,
        ]
    ):
        raise ValueError(
            "Do not combine --endor-app-url with --project-name, --project-uuid, "
            "--scan-result-url, or --scan-result-uuid"
        )
    info = parse_endor_app_url(args.endor_app_url)
    if info["kind"] == "project":
        args.project_uuid = info["project_uuid"]
        args.namespace = args.namespace or info["namespace"]
    else:
        args.scan_result_url = args.endor_app_url.strip()
    args.endor_app_url = None


def run(args: argparse.Namespace) -> dict[str, Any]:
    _apply_endor_app_url(args)

    _exactly_one(
        project_name=bool(args.project_name),
        project_uuid=bool(args.project_uuid),
        scan_result_url=bool(args.scan_result_url),
        scan_result_uuid=bool(args.scan_result_uuid),
    )

    rt = root_tenant(args.tenant)
    client = endorlabs.Client(tenant=args.tenant)
    warnings: list[str] = []
    projects_out: list[dict[str, Any]] = []
    scan_hint: dict[str, Any] | None = None

    try:
        if args.project_uuid:
            ns = args.namespace or args.tenant
            pr = canonical_resolve_project(client, ns, args.project_uuid, warnings)
            projects_out.append(_dump(pr))

        elif args.project_name:
            matched = search_projects_by_name_or_uuid(
                client, namespace=args.tenant, query=args.project_name
            )

            if not matched:
                raise ValueError(
                    f"No project matched name substring: {args.project_name!r}"
                )

            _, dup_warnings, err = duplicate_project_decision(matched, max_auto=3)
            warnings.extend(dup_warnings)
            if err and err.startswith("too_many"):
                payload = {
                    "root_tenant": rt,
                    "error": err,
                    "match_count": len(matched),
                    "matches_preview": [
                        {"uuid": getattr(p, "uuid", None), "name": _name(p)}
                        for p in matched[:20]
                    ],
                    "hint": (
                        "Narrow --project-name or use --project-uuid / ScanResult URL"
                    ),
                }
                path = write_json(
                    output_dir=Path(args.output_dir),
                    root_tenant_name=rt,
                    object_kind="project_search",
                    object_uuid="too-many",
                    purpose="error",
                    payload=payload,
                    timestamped=args.timestamped,
                )
                return {"artifact": str(path), "exit_code": 2, "payload": payload}

            projects_out.extend(_dump(p) for p in matched)

        elif args.scan_result_url:
            url_ns, su = parse_app_scan_history_url(args.scan_result_url)
            sr = client.ScanResult.get(su, namespace=args.tenant)
            tm = getattr(sr, "tenant_meta", None)
            resolved_ns = getattr(tm, "namespace", None) if tm else None
            scan_hint = {
                "namespace_from_url": url_ns,
                "scan_result_uuid": su,
                "resolved_namespace": resolved_ns,
            }
            projects_out, warnings = _projects_from_scan(client, sr, url_ns, warnings)

        else:
            assert args.scan_result_uuid
            su = args.scan_result_uuid.strip()
            sr = client.ScanResult.get(su, namespace=args.tenant)
            tm = getattr(sr, "tenant_meta", None)
            resolved_ns = getattr(tm, "namespace", None) if tm else None
            scan_hint = {
                "scan_result_uuid": su,
                "resolved_namespace": resolved_ns,
            }
            projects_out, warnings = _projects_from_scan(client, sr, None, warnings)

    finally:
        client.close()

    payload: dict[str, Any] = {
        "root_tenant": rt,
        "query_tenant": args.tenant,
        "warnings": warnings,
        "projects": projects_out,
        "project_count": len(projects_out),
        "scan_result_hint": scan_hint,
    }
    obj_uuid = projects_out[0].get("uuid", "resolved") if projects_out else "none"
    path = write_json(
        output_dir=Path(args.output_dir),
        root_tenant_name=rt,
        object_kind="project_search",
        object_uuid=str(obj_uuid)[:24],
        purpose="candidates",
        payload=payload,
        timestamped=args.timestamped,
    )
    payload["artifact"] = str(path)
    return {"artifact": str(path), "exit_code": 0, "payload": payload}


def _name(project: Any) -> str:
    m = getattr(project, "meta", None)
    return getattr(m, "name", "") or str(getattr(project, "uuid", ""))


def _projects_from_scan(
    client: endorlabs.Client,
    sr: Any,
    url_ns: str | None,
    warnings: list[str],
) -> tuple[list[dict[str, Any]], list[str]]:
    out: list[dict[str, Any]] = []
    tm = getattr(sr, "tenant_meta", None)
    resolved_ns = getattr(tm, "namespace", None) if tm else None
    if url_ns and resolved_ns and url_ns != resolved_ns:
        warnings.append(f"namespace_mismatch:url_had:{url_ns}:resolved:{resolved_ns}")
    meta = getattr(sr, "meta", None)
    parent = getattr(meta, "parent_uuid", None) if meta else None
    if not parent or not resolved_ns:
        raise ValueError("ScanResult missing parent_uuid or namespace")
    pr = client.Project.get(parent, namespace=resolved_ns)
    out.append(_dump(pr))
    return out, warnings


def main() -> int:
    args = _build_parser().parse_args()
    try:
        result = run(args)
    except ValueError as e:
        print(json.dumps({"error": str(e)}), file=sys.stderr)
        return 1
    print(result["artifact"])
    return int(result.get("exit_code", 0))


if __name__ == "__main__":
    raise SystemExit(main())
