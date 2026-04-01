#!/usr/bin/env python3
"""Sync Endor Labs PR comment template via PRCommentConfig resource.

Creates or updates a tenant-scoped PRCommentConfig entry for GitHub using a
template file on disk. Designed for CI usage in pull_request workflows.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import endorlabs
from endorlabs.resources.pr_comment_config import (
    CreatePRCommentConfigPayload,
    PRCommentConfigMeta,
    PRCommentConfigSpec,
    PRCommentsTemplate,
    PlatformSource,
)


def _append_github_output(key: str, value: str) -> None:
    output_path = os.environ.get("GITHUB_OUTPUT")
    if not output_path:
        return
    with open(output_path, "a", encoding="utf-8") as fh:
        fh.write(f"{key}={value}\n")


def _load_template(path: Path) -> str:
    content = path.read_text(encoding="utf-8")
    if not content.strip():
        raise ValueError(f"Template file is empty: {path}")
    return content


def _platform_enum(raw: str) -> PlatformSource:
    try:
        return PlatformSource(raw)
    except ValueError as exc:
        allowed = ", ".join(member.value for member in PlatformSource)
        raise ValueError(f"Invalid platform type {raw!r}. Allowed: {allowed}") from exc


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--namespace", required=True, help="Tenant namespace.")
    parser.add_argument(
        "--name",
        default="github-pr-comments-template",
        help="meta.name of PRCommentConfig resource.",
    )
    parser.add_argument(
        "--template-path",
        type=Path,
        required=True,
        help="Path to template text file.",
    )
    parser.add_argument(
        "--platform-type",
        default=PlatformSource.GITHUB.value,
        help="Platform enum value, e.g. PLATFORM_SOURCE_GITHUB.",
    )
    parser.add_argument(
        "--description",
        default="Managed by CI: GitHub PR findings summary template.",
        help="Resource description for managed PRCommentConfig.",
    )
    parser.add_argument(
        "--propagate",
        action="store_true",
        help="Set propagate=true when creating/updating config.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Do not persist updates; report planned action only.",
    )
    args = parser.parse_args(argv)

    try:
        platform = _platform_enum(args.platform_type)
        template_text = _load_template(args.template_path)
    except Exception as exc:
        print(f"Template sync failed during input validation: {exc}", file=sys.stderr)
        _append_github_output("template_sync_status", "error")
        return 1

    client = endorlabs.Client(tenant=args.namespace)

    existing = client.PRCommentConfig.list(name=args.name, max_pages=2)
    if len(existing) > 1:
        print(
            f"Multiple PRCommentConfig resources found for name {args.name!r}; refusing.",
            file=sys.stderr,
        )
        _append_github_output("template_sync_status", "error")
        return 1

    if not existing:
        if args.dry_run:
            print(f"[DRY-RUN] Would create PRCommentConfig {args.name!r}.")
            _append_github_output("template_sync_status", "dry_run_create")
            return 0
        payload = CreatePRCommentConfigPayload(
            meta=PRCommentConfigMeta(
                name=args.name,
                description=args.description,
                tags=["managed-by-ci", "pr-comments-template"],
            ),
            spec=PRCommentConfigSpec(
                platform_type=platform,
                template=PRCommentsTemplate(findings_summary_template=template_text),
            ),
            propagate=args.propagate,
        )
        created = client.PRCommentConfig.create(payload)
        print(f"Created PRCommentConfig {created.uuid} ({args.name}).")
        _append_github_output("template_sync_status", "created")
        _append_github_output("template_sync_uuid", created.uuid)
        return 0

    current = existing[0]
    current_template = (
        current.spec.template.findings_summary_template
        if current.spec and current.spec.template
        else ""
    )
    current_platform = current.spec.platform_type if current.spec else None
    needs_update = (
        current_template != template_text
        or str(current_platform) != platform.value
        or bool(current.propagate) != bool(args.propagate)
    )
    if not needs_update:
        print(f"PRCommentConfig {current.uuid} already matches desired template.")
        _append_github_output("template_sync_status", "unchanged")
        _append_github_output("template_sync_uuid", current.uuid)
        return 0

    if args.dry_run:
        print(f"[DRY-RUN] Would update PRCommentConfig {current.uuid}.")
        _append_github_output("template_sync_status", "dry_run_update")
        _append_github_output("template_sync_uuid", current.uuid)
        return 0

    update_payload = current.model_copy(
        deep=True,
        update={
            "meta": current.meta.model_copy(update={"description": args.description}),
            "spec": current.spec.model_copy(
                update={
                    "platform_type": platform,
                    "template": current.spec.template.model_copy(
                        update={"findings_summary_template": template_text}
                    ),
                }
            ),
            "propagate": args.propagate,
        },
    )
    updated = client.PRCommentConfig.update(
        current.uuid,
        payload=update_payload,
        update_mask=(
            "meta.description,"
            "spec.platform_type,"
            "spec.template.findings_summary_template,"
            "propagate"
        ),
    )
    print(f"Updated PRCommentConfig {updated.uuid}.")
    _append_github_output("template_sync_status", "updated")
    _append_github_output("template_sync_uuid", updated.uuid)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
