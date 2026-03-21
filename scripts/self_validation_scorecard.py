"""Generate deterministic self-validation scorecards for one repository.

This script is CI/nightly-friendly and produces machine-readable artifacts
that can be compared across runs.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import endorlabs
from endorlabs.tools.dependency_explorer import process_project, slugify
from endorlabs.workflows.diagnostics import (
    build_self_validation_scorecard,
    check_dependency_visibility,
    compare_scan_logs,
    list_project_dependencies,
)
from endorlabs.workflows.session_context import create_session
from endorlabs.workflows.threat_analysis import verify_threat_model_claims


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate SDK self-validation scorecard"
    )
    parser.add_argument(
        "--repository-url",
        required=True,
        help="Repository URL as stored in Project.meta.name",
    )
    parser.add_argument(
        "--tenant",
        default=None,
        help="Tenant namespace (defaults to ENDOR_NAMESPACE env var)",
    )
    parser.add_argument(
        "--output-dir",
        default=".endorlabs-context/self-validation",
        help="Directory where scorecard/session artifacts are written",
    )
    parser.add_argument(
        "--deterministic",
        action="store_true",
        help="Use stable sorting and fixed timestamps for reproducible artifacts",
    )
    parser.add_argument(
        "--strict-threat-claims",
        action="store_true",
        help="Fail if threat-model claims cannot be verified from collected context",
    )
    parser.add_argument(
        "--num-scans",
        type=int,
        default=2,
        help="Number of recent scans to compare for reliability metrics",
    )
    return parser.parse_args()


def _count_findings(ctx: Any) -> tuple[int, int, int]:
    findings_total = int(ctx.total)
    critical = 0
    high = 0
    for category_counts in ctx.by_category.values():
        critical += int(category_counts.get("Critical", 0))
        high += int(category_counts.get("High", 0))
    return findings_total, critical, high


def main() -> int:
    args = _parse_args()
    client = endorlabs.Client(tenant=args.tenant)
    out_root = Path(args.output_dir)
    out_root.mkdir(parents=True, exist_ok=True)

    try:
        project = client.Project.lookup(name=args.repository_url, traverse=True)
    except Exception as exc:
        print(f"Unable to resolve project for {args.repository_url}: {exc}")
        client.close()
        return 2

    project_name = project.meta.name if project.meta else project.uuid
    project_slug = slugify(project_name)
    project_dir = out_root / project_slug
    project_dir.mkdir(parents=True, exist_ok=True)

    session = create_session(client, project, out_root, deterministic=args.deterministic)
    if not session.ok:
        print(f"Session collection failed: {session.message}")
        client.close()
        return 2

    namespace = (
        project.tenant_meta.namespace
        if project.tenant_meta and project.tenant_meta.namespace
        else ""
    )
    findings_total, findings_critical, findings_high = _count_findings(session.findings)

    dep_report = list_project_dependencies(client, namespace=namespace, traverse=True)
    visibility_report = check_dependency_visibility(
        client, namespace=namespace, traverse=True
    )
    scan_comparison = compare_scan_logs(
        client,
        namespace=namespace,
        project_uuid=project.uuid,
        num_scans=max(args.num_scans, 1),
        traverse=False,
    )

    # Produce deterministic dependency/callgraph snapshot bundle.
    api_client = client._client  # noqa: SLF001
    if api_client is None:
        print("Client transport unavailable while creating snapshot bundle.")
        client.close()
        return 2
    dep_out = str(project_dir / "dependencies")
    process_project(
        client,
        api_client,
        namespace,
        project,
        dep_out,
        pv_limit=5,
        dep_metadata_max_pages=10,
        deterministic=args.deterministic,
    )

    generated_at = "1970-01-01T00:00:00Z" if args.deterministic else None
    scorecard = build_self_validation_scorecard(
        repository=project_name,
        namespace=namespace,
        findings_total=findings_total,
        findings_critical=findings_critical,
        findings_high=findings_high,
        policies_total=session.policies.total,
        dependency_report=dep_report,
        visibility_report=visibility_report,
        scan_comparison=scan_comparison,
        generated_at=generated_at,
    )

    if args.strict_threat_claims:
        tm_path = project_dir / "threat-model.md"
        if not tm_path.exists():
            print(
                "Threat-model verification is strict but threat-model.md was not found."
            )
            client.close()
            return 3
        verification = verify_threat_model_claims(
            report=tm_path.read_text(encoding="utf-8"),
            context_markdown=(project_dir / "project-summary.md").read_text(
                encoding="utf-8"
            ),
            strict=True,
        )
        if not verification.ok:
            print("Threat-model verification failed.")
            client.close()
            return 3

    out_path = project_dir / "self_validation_scorecard.json"
    out_path.write_text(
        json.dumps(scorecard.to_dict(), indent=2, sort_keys=True), encoding="utf-8"
    )
    print(f"Self-validation scorecard written: {out_path}")
    client.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
