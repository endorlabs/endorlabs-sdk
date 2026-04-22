"""List or delete orphaned findings using the Endor Labs SDK.

Default mode is dry-run analysis. Deletion is guarded behind explicit flags and
user confirmation.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any

import endorlabs
from endorlabs.core.types import ListParameters


def _prompt_yes_no(prompt: str) -> bool:
    """Return True only when user explicitly confirms."""
    answer = input(f"{prompt} [y/N]: ").strip().lower()
    return answer in {"y", "yes"}


def _read_attr_path(obj: Any, attr_path: str) -> Any:
    """Resolve dotted attribute path on Pydantic models/dicts safely."""
    current = obj
    for part in attr_path.split("."):
        if current is None:
            return None
        if isinstance(current, dict):
            current = current.get(part)
            continue
        current = getattr(current, part, None)
    return current


def _collect_existing_namespaces(
    *,
    tenant: str,
    namespaces: list[Any],
    namespace_name_attr: str,
) -> set[str]:
    """Build namespace set from tenant root and Namespace resources."""
    existing: set[str] = {tenant}
    for namespace_obj in namespaces:
        value = _read_attr_path(namespace_obj, namespace_name_attr)
        if isinstance(value, str) and value.strip():
            existing.add(value.strip())
    return existing


def _namespace_allowed(
    namespace: str,
    include_prefixes: list[str],
    exclude_prefixes: list[str],
) -> bool:
    """Apply include/exclude prefix filtering for namespaces."""
    if include_prefixes and not any(namespace.startswith(p) for p in include_prefixes):
        return False
    if any(namespace.startswith(p) for p in exclude_prefixes):
        return False
    return True


def _trim_finding(
    finding: Any,
    output_attrs: list[str],
) -> dict[str, Any]:
    """Return selected finding fields by dotted paths."""
    trimmed: dict[str, Any] = {}
    for attr in output_attrs:
        trimmed[attr] = _read_attr_path(finding, attr)
    return trimmed


def _escape_filter_string(value: str) -> str:
    """Escape a string literal for Endor filter expressions."""
    return value.replace("\\", "\\\\").replace('"', '\\"')


def _extract_group_namespace_counts(payload: dict[str, Any]) -> dict[str, int]:
    """Parse group_response into {namespace: count}."""
    group_response = payload.get("group_response")
    if not isinstance(group_response, dict):
        return {}
    groups = group_response.get("groups")
    if not isinstance(groups, dict):
        return {}

    counts: dict[str, int] = {}
    for raw_key, raw_value in groups.items():
        if not isinstance(raw_key, str) or not isinstance(raw_value, dict):
            continue
        try:
            key_items = json.loads(raw_key)
        except json.JSONDecodeError:
            continue
        if not isinstance(key_items, list) or not key_items:
            continue
        first = key_items[0]
        if not isinstance(first, dict):
            continue
        namespace = first.get("value")
        if not isinstance(namespace, str) or not namespace.strip():
            continue

        aggregation_count = raw_value.get("aggregation_count")
        if not isinstance(aggregation_count, dict):
            continue
        count = aggregation_count.get("count")
        if not isinstance(count, int):
            continue

        counts[namespace.strip()] = count
    return counts


def _list_grouped_finding_namespace_counts(
    *,
    client: endorlabs.Client,
    tenant: str,
    finding_filter: str | None,
    finding_namespace_attr: str,
    max_pages: int | None,
) -> tuple[dict[str, int], int]:
    """Run grouped Finding list; fallback to client-side aggregation if needed."""
    api_client = client._client  # noqa: SLF001
    if api_client is None:
        raise RuntimeError("Client is closed.")

    count_params: dict[str, str] = {
        "list_parameters.traverse": "true",
        "list_parameters.count": "true",
    }
    if finding_filter:
        count_params["list_parameters.filter"] = finding_filter

    count_response = api_client.get(
        f"v1/namespaces/{tenant}/findings", params=count_params
    )
    count_payload = count_response.json()
    total_count = 0
    if isinstance(count_payload, dict):
        count_response_obj = count_payload.get("count_response")
        if isinstance(count_response_obj, dict):
            count_value = count_response_obj.get("count")
            if isinstance(count_value, int):
                total_count = count_value

    params: dict[str, str] = {
        "list_parameters.traverse": "true",
        "list_parameters.group_aggregation_paths": finding_namespace_attr,
    }
    if finding_filter:
        params["list_parameters.filter"] = finding_filter

    response = api_client.get(f"v1/namespaces/{tenant}/findings", params=params)
    payload = response.json()
    if isinstance(payload, dict):
        grouped_counts = _extract_group_namespace_counts(payload)
        if grouped_counts:
            if total_count == 0:
                total_count = sum(grouped_counts.values())
            return grouped_counts, total_count

    # Fallback path for environments where grouped responses are not returned.
    fallback_params: dict[str, str] = {
        "list_parameters.traverse": "true",
        "list_parameters.mask": finding_namespace_attr,
    }
    if finding_filter:
        fallback_params["list_parameters.filter"] = finding_filter

    findings = list(
        api_client.get_all(
            f"v1/namespaces/{tenant}/findings",
            params=fallback_params,
            max_pages=max_pages,
        )
    )
    fallback_counts: dict[str, int] = {}
    for finding in findings:
        namespace_value = _read_attr_path(finding, finding_namespace_attr)
        if not isinstance(namespace_value, str) or not namespace_value.strip():
            continue
        namespace = namespace_value.strip()
        fallback_counts[namespace] = fallback_counts.get(namespace, 0) + 1

    if total_count == 0:
        total_count = len(findings)
    return fallback_counts, total_count


def _list_findings_for_namespace(
    *,
    client: endorlabs.Client,
    namespace: str,
    finding_namespace_attr: str,
    finding_filter: str | None,
    output_attrs: list[str],
    max_pages: int | None,
) -> tuple[list[dict[str, Any]], list[Any]]:
    """Return trimmed and raw orphan findings for a namespace."""
    ns_filter = f'{finding_namespace_attr}=="{_escape_filter_string(namespace)}"'
    combined_filter = ns_filter
    if finding_filter:
        combined_filter = f"({finding_filter}) AND ({ns_filter})"

    findings = client.Finding.list(
        list_params=ListParameters(
            traverse=True,
            filter=combined_filter,
        ),
        max_pages=max_pages,
    )
    trimmed = [_trim_finding(finding, output_attrs) for finding in findings]
    return trimmed, list(findings)


def _collect_orphaned_findings(
    *,
    tenant: str,
    finding_filter: str | None,
    finding_namespace_attr: str,
    namespace_name_attr: str,
    include_namespace_prefix: list[str],
    exclude_namespace_prefix: list[str],
    output_attrs: list[str],
    max_pages: int | None,
    dry_run: bool,
) -> tuple[dict[str, Any], list[Any]]:
    """Return result payload and orphan finding resources.

    Search space is discovered from grouped Finding list first, then Namespace
    resources are used only to decide orphan status.
    """
    requested_tenant = tenant
    effective_tenant = tenant
    client = endorlabs.Client(tenant=effective_tenant)
    try:
        observed_namespace_counts, total_findings_scanned = (
            _list_grouped_finding_namespace_counts(
                client=client,
                tenant=effective_tenant,
                finding_filter=finding_filter,
                finding_namespace_attr=finding_namespace_attr,
                max_pages=max_pages,
            )
        )
        if total_findings_scanned == 0 and "." in requested_tenant:
            root_tenant = requested_tenant.split(".", maxsplit=1)[0]
            if root_tenant and root_tenant != requested_tenant:
                client.close()
                effective_tenant = root_tenant
                client = endorlabs.Client(tenant=effective_tenant)
                observed_namespace_counts, total_findings_scanned = (
                    _list_grouped_finding_namespace_counts(
                        client=client,
                        tenant=effective_tenant,
                        finding_filter=finding_filter,
                        finding_namespace_attr=finding_namespace_attr,
                        max_pages=max_pages,
                    )
                )
        namespaces = client.Namespace.list(
            list_params=ListParameters(traverse=True),
            max_pages=max_pages,
        )

        existing_namespaces = _collect_existing_namespaces(
            tenant=effective_tenant,
            namespaces=namespaces,
            namespace_name_attr=namespace_name_attr,
        )

        counts_by_namespace: dict[str, int] = {}
        for namespace, count in observed_namespace_counts.items():
            if not _namespace_allowed(
                namespace,
                include_prefixes=include_namespace_prefix,
                exclude_prefixes=exclude_namespace_prefix,
            ):
                continue
            if namespace in existing_namespaces:
                continue
            counts_by_namespace[namespace] = count

        orphaned_finding_details: list[dict[str, Any]] = []
        orphaned_finding_resources: list[Any] = []
        for orphan_namespace in sorted(counts_by_namespace.keys()):
            details, resources = _list_findings_for_namespace(
                client=client,
                namespace=orphan_namespace,
                finding_namespace_attr=finding_namespace_attr,
                finding_filter=finding_filter,
                output_attrs=output_attrs,
                max_pages=max_pages,
            )
            orphaned_finding_details.extend(details)
            orphaned_finding_resources.extend(resources)
    finally:
        client.close()

    orphan_namespaces = sorted(counts_by_namespace.keys())
    result = {
        "tenant": effective_tenant,
        "config": {
            "requested_tenant": requested_tenant,
            "effective_tenant": effective_tenant,
            "finding_filter": finding_filter,
            "finding_namespace_attr": finding_namespace_attr,
            "namespace_name_attr": namespace_name_attr,
            "include_namespace_prefix": include_namespace_prefix,
            "exclude_namespace_prefix": exclude_namespace_prefix,
            "max_pages": max_pages,
            "dry_run": dry_run,
        },
        "summary": {
            "total_findings_scanned": total_findings_scanned,
            "known_namespaces_count": len(existing_namespaces),
            "observed_finding_namespaces_count": len(observed_namespace_counts),
        },
        "observed_finding_namespaces": [
            {"namespace": ns, "count": observed_namespace_counts[ns]}
            for ns in sorted(observed_namespace_counts.keys())
        ],
        "orphan_namespaces": [
            {"namespace": ns, "count": counts_by_namespace[ns]}
            for ns in orphan_namespaces
        ],
        "orphaned_finding_count": sum(counts_by_namespace.values()),
        "orphaned_findings": orphaned_finding_details,
        "message": ("Dry run analysis complete." if dry_run else "Analysis complete."),
    }
    return result, orphaned_finding_resources


def _delete_orphaned_findings(
    *,
    tenant: str,
    findings: list[Any],
    auto_approve: bool,
) -> dict[str, Any]:
    """Delete orphan finding resources after approval."""
    if not findings:
        return {
            "requested": 0,
            "deleted": 0,
            "failed": 0,
            "errors": [],
            "message": "No orphaned findings to delete.",
        }

    if not auto_approve:
        if not _prompt_yes_no(
            f"Delete {len(findings)} orphaned finding(s) in tenant '{tenant}'?"
        ):
            return {
                "requested": len(findings),
                "deleted": 0,
                "failed": 0,
                "errors": [],
                "message": "Deletion cancelled by user.",
            }

    deleted = 0
    failed = 0
    errors: list[dict[str, Any]] = []

    client = endorlabs.Client(tenant=tenant)
    try:
        for finding in findings:
            finding_uuid = _read_attr_path(finding, "uuid")
            try:
                client.Finding.delete(finding)
                deleted += 1
            except Exception:  # noqa: BLE001
                failed += 1
                errors.append(
                    {
                        "uuid": finding_uuid,
                        "error": "delete_failed",
                    }
                )
    finally:
        client.close()

    return {
        "requested": len(findings),
        "deleted": deleted,
        "failed": failed,
        "errors": errors,
        "message": "Deletion complete.",
    }


def _print_summary(result: dict[str, Any]) -> None:
    """Print a human-readable CLI summary."""
    tenant = result.get("tenant", "?")
    config = result.get("config", {})
    requested_tenant = config.get("requested_tenant")
    effective_tenant = config.get("effective_tenant")
    summary = result.get("summary", {})
    orphan_namespaces = result.get("orphan_namespaces", [])
    observed_namespaces = result.get("observed_finding_namespaces", [])

    print("=== Orphaned Findings Summary ===")
    print(f"Tenant:            {tenant}")
    if requested_tenant and effective_tenant and requested_tenant != effective_tenant:
        print(f"Requested tenant:  {requested_tenant}")
        print(f"Effective tenant:  {effective_tenant}")
    print(f"Mode:              {'dry-run' if config.get('dry_run') else 'apply'}")
    print(f"Finding filter:    {config.get('finding_filter') or '(none)'}")
    print(f"Namespace attr:    {config.get('finding_namespace_attr')}")
    print(f"Namespace name:    {config.get('namespace_name_attr')}")
    print(f"Scanned findings:  {summary.get('total_findings_scanned', 0)}")
    print(f"Known namespaces:  {summary.get('known_namespaces_count', 0)}")
    print(f"Observed ns count: {summary.get('observed_finding_namespaces_count', 0)}")
    print(f"Orphaned findings: {result.get('orphaned_finding_count', 0)}")
    print()

    if observed_namespaces:
        print("Observed finding namespaces:")
        for row in observed_namespaces:
            print(f"  - {row.get('namespace')}: {row.get('count', 0)}")
        print()
    else:
        print("Observed finding namespaces: none")
        print()

    if orphan_namespaces:
        print("Orphan namespaces:")
        for row in orphan_namespaces:
            print(f"  - {row.get('namespace')}: {row.get('count', 0)}")
    else:
        print("Orphan namespaces: none")

    delete_result = result.get("delete_result")
    if isinstance(delete_result, dict):
        print()
        print("Delete step:")
        print(f"  Requested: {delete_result.get('requested', 0)}")
        print(f"  Deleted:   {delete_result.get('deleted', 0)}")
        print(f"  Failed:    {delete_result.get('failed', 0)}")
        message = delete_result.get("message")
        if message:
            print(f"  Message:   {message}")


def main() -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description=(
            "Analyze orphaned findings and optionally delete them. Defaults to dry-run."
        )
    )
    parser.add_argument(
        "--tenant",
        default=os.getenv("ENDOR_NAMESPACE") or os.getenv("ENDOR_TENANT"),
        help="Root tenant namespace (defaults to ENDOR_NAMESPACE then ENDOR_TENANT).",
    )
    parser.add_argument(
        "--finding-filter",
        default=None,
        help=(
            "Optional SDK/API filter expression for findings "
            "(example: spec.level==FINDING_LEVEL_CRITICAL)."
        ),
    )
    parser.add_argument(
        "--finding-namespace-attr",
        default="tenant_meta.namespace",
        help="Dotted attribute path on Finding used as namespace value.",
    )
    parser.add_argument(
        "--namespace-name-attr",
        default="spec.full_name",
        help="Dotted attribute path on Namespace used as canonical namespace name.",
    )
    parser.add_argument(
        "--include-namespace-prefix",
        action="append",
        default=[],
        help="Only evaluate findings whose namespace starts with this prefix (repeatable).",
    )
    parser.add_argument(
        "--exclude-namespace-prefix",
        action="append",
        default=[],
        help="Exclude findings whose namespace starts with this prefix (repeatable).",
    )
    parser.add_argument(
        "--output-attrs",
        default="uuid,meta.name,tenant_meta.namespace,spec.level,spec.project_uuid",
        help="Comma-separated dotted finding attributes to include in output.",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=None,
        help="Max pages per list call (default: all pages).",
    )
    run_mode = parser.add_mutually_exclusive_group()
    run_mode.add_argument(
        "--dry-run",
        dest="dry_run",
        action="store_true",
        help="Analyze only (default).",
    )
    run_mode.add_argument(
        "--apply",
        dest="dry_run",
        action="store_false",
        help="Allow mutating operations when paired with --delete.",
    )
    parser.set_defaults(dry_run=True)
    parser.add_argument(
        "--delete",
        action="store_true",
        help="Delete orphaned findings after analysis (requires --apply).",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Skip interactive delete confirmation prompt.",
    )
    output_mode = parser.add_mutually_exclusive_group()
    output_mode.add_argument(
        "--json",
        action="store_true",
        help="Print compact JSON output.",
    )
    output_mode.add_argument(
        "--pretty-json",
        action="store_true",
        help="Print indented JSON output.",
    )
    args = parser.parse_args()
    output_attrs = [
        attr.strip() for attr in args.output_attrs.split(",") if attr.strip()
    ]
    if not args.tenant:
        print(
            "Error: tenant is required. Pass --tenant or set ENDOR_TENANT.",
            file=sys.stderr,
        )
        return 2
    if not output_attrs:
        print("Error: --output-attrs cannot be empty.", file=sys.stderr)
        return 2

    try:
        result, orphan_resources = _collect_orphaned_findings(
            tenant=args.tenant,
            finding_filter=args.finding_filter,
            finding_namespace_attr=args.finding_namespace_attr,
            namespace_name_attr=args.namespace_name_attr,
            include_namespace_prefix=list(args.include_namespace_prefix),
            exclude_namespace_prefix=list(args.exclude_namespace_prefix),
            output_attrs=output_attrs,
            max_pages=args.max_pages,
            dry_run=args.dry_run,
        )

        if args.delete:
            if args.dry_run:
                result["delete_result"] = {
                    "requested": len(orphan_resources),
                    "deleted": 0,
                    "failed": 0,
                    "errors": [],
                    "message": (
                        "Dry run active. Re-run with --apply --delete to perform deletion."
                    ),
                }
            else:
                result["delete_result"] = _delete_orphaned_findings(
                    tenant=str(result.get("tenant", args.tenant)),
                    findings=orphan_resources,
                    auto_approve=args.yes,
                )
    except Exception:  # pragma: no cover - defensive CLI error guard
        print("Error: operation failed.", file=sys.stderr)
        return 1

    if args.pretty_json:
        print(json.dumps(result, indent=2))
    elif args.json:
        print(json.dumps(result))
    else:
        _print_summary(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
