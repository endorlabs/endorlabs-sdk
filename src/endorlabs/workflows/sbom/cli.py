"""Console entrypoint: ``endor-sbom``."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import endorlabs
from endorlabs.context.paths import task_activity_dir
from endorlabs.workflows.sbom.coverage import run_coverage
from endorlabs.workflows.sbom.export_sbom import run_sbom_export, run_vex_export
from endorlabs.workflows.sbom.import_sbom import run_import


def _default_output_dir(tenant: str) -> Path:
    return Path(task_activity_dir(tenant, "sbom"))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "SBOM management: import via endorctl, coverage check, list imports, "
            "and SBOM/VEX export via Client facades."
        ),
    )
    sub = parser.add_subparsers(dest="command", required=True)

    cov = sub.add_parser("coverage", help="File components vs project PackageVersions")
    _ = cov.add_argument("-n", "--tenant", required=True, help="Tenant namespace")
    _ = cov.add_argument(
        "--sbom",
        type=Path,
        required=True,
        help="Path to CDX/SPDX file",
    )
    _ = cov.add_argument(
        "--project-uuid",
        required=True,
        help="SBOM project UUID (from import)",
    )
    _ = cov.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Artifact dir (default: .endorlabs/tasks/<slug>-<date>/sbom/)",
    )
    _ = cov.add_argument(
        "--json",
        action="store_true",
        help="Print full JSON to stdout",
    )

    imp = sub.add_parser("import", help="Import SBOM via endorctl sbom import")
    _ = imp.add_argument("-n", "--tenant", required=True, help="Tenant namespace")
    _ = imp.add_argument(
        "--sbom",
        type=Path,
        required=True,
        help="Path to CDX/SPDX file",
    )
    _ = imp.add_argument(
        "--format",
        default=None,
        choices=["cyclonedx", "spdx"],
        help="Override format (default: auto-detect SPDX vs CycloneDX)",
    )
    _ = imp.add_argument(
        "--with-coverage",
        action="store_true",
        help="Run coverage after successful import",
    )
    _ = imp.add_argument("--output-dir", type=Path, default=None)
    _ = imp.add_argument("--json", action="store_true")

    exp = sub.add_parser("export", help="Create SBOMExport or VEXExport")
    _ = exp.add_argument("-n", "--tenant", required=True)
    _ = exp.add_argument(
        "--kind",
        choices=["sbom", "vex"],
        default="sbom",
        help="Export kind (default: sbom)",
    )
    _ = exp.add_argument(
        "--parent-kind",
        required=True,
        choices=["PackageVersion", "RepositoryVersion"],
        help="meta.parent_kind for the export",
    )
    _ = exp.add_argument("--parent-uuid", required=True, help="Parent resource UUID")
    _ = exp.add_argument(
        "--component-type",
        default="COMPONENT_TYPE_APPLICATION",
        help="COMPONENT_TYPE_APPLICATION or COMPONENT_TYPE_LIBRARY",
    )
    _ = exp.add_argument(
        "--sbom-kind",
        default="SBOM_KIND_CYCLONEDX",
        help="SBOM_KIND_CYCLONEDX or SBOM_KIND_SPDX (sbom export only)",
    )
    _ = exp.add_argument(
        "--format",
        default="FORMAT_JSON",
        help="FORMAT_JSON, FORMAT_XML, or FORMAT_TAG_VALUE",
    )
    _ = exp.add_argument("--output-dir", type=Path, default=None)
    _ = exp.add_argument("--json", action="store_true")

    lst = sub.add_parser("list-imports", help="List ImportedSBOM rows")
    _ = lst.add_argument("-n", "--tenant", required=True)
    _ = lst.add_argument(
        "--max-pages",
        type=int,
        default=None,
        help="Optional page cap (default: API/SDK default)",
    )
    _ = lst.add_argument("--output-dir", type=Path, default=None)
    _ = lst.add_argument("--json", action="store_true")

    return parser


def _cmd_coverage(args: argparse.Namespace) -> int:
    tenant = str(args.tenant).strip()
    client = endorlabs.Client(tenant=tenant)
    result = run_coverage(
        client,
        sbom_path=Path(args.sbom),
        project_uuid=str(args.project_uuid).strip(),
    )
    out_dir = Path(args.output_dir) if args.output_dir else _default_output_dir(tenant)
    payload = result.to_dict()
    _write_json(out_dir / "coverage_result.json", payload)
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print(result.message)
        print(f"Wrote {out_dir / 'coverage_result.json'}")
    return 0 if result.status != "error" else 1


def _cmd_import(args: argparse.Namespace) -> int:
    tenant = str(args.tenant).strip()
    client = endorlabs.Client(tenant=tenant) if args.with_coverage else None
    fmt = None if args.format in (None, "cyclonedx") else args.format
    result = run_import(
        namespace=tenant,
        sbom_path=Path(args.sbom),
        sbom_format=fmt,
        client=client,
        run_coverage_after=bool(args.with_coverage),
    )
    out_dir = Path(args.output_dir) if args.output_dir else _default_output_dir(tenant)
    payload = result.to_dict()
    # Drop bulky endorctl streams from artifact unless error
    if result.status != "error":
        payload.pop("stdout", None)
        payload.pop("stderr", None)
    _write_json(out_dir / "import_result.json", payload)
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print(result.message)
        print(f"Wrote {out_dir / 'import_result.json'}")
    return 0 if result.status != "error" else 1


def _cmd_export(args: argparse.Namespace) -> int:
    tenant = str(args.tenant).strip()
    client = endorlabs.Client(tenant=tenant)
    if args.kind == "vex":
        result = run_vex_export(
            client,
            parent_kind=str(args.parent_kind),
            parent_uuid=str(args.parent_uuid),
            component_type=str(args.component_type),
            output_format=str(args.format),
        )
    else:
        result = run_sbom_export(
            client,
            parent_kind=str(args.parent_kind),
            parent_uuid=str(args.parent_uuid),
            component_type=str(args.component_type),
            kind=str(args.sbom_kind),
            output_format=str(args.format),
        )
    out_dir = Path(args.output_dir) if args.output_dir else _default_output_dir(tenant)
    payload = result.to_dict()
    _write_json(out_dir / "export_result.json", payload)
    if result.data:
        suffix = ".xml" if "XML" in str(args.format).upper() else ".json"
        (out_dir / f"export{suffix}").write_text(result.data, encoding="utf-8")
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print(result.message)
        print(f"Wrote {out_dir / 'export_result.json'}")
    return 0 if result.status != "error" else 1


def _cmd_list_imports(args: argparse.Namespace) -> int:
    tenant = str(args.tenant).strip()
    client = endorlabs.Client(tenant=tenant)
    kwargs: dict[str, Any] = {}
    if args.max_pages is not None:
        kwargs["max_pages"] = int(args.max_pages)
    rows = client.ImportedSBOM.list(**kwargs)
    summary: list[dict[str, str | None]] = []
    for row in rows:
        meta = getattr(row, "meta", None)
        name = getattr(meta, "name", None)
        parent = getattr(meta, "parent_uuid", None)
        summary.append(
            {
                "uuid": str(getattr(row, "uuid", None) or "") or None,
                "name": str(name) if name else None,
                "parent_uuid": str(parent) if parent else None,
            }
        )
    payload: dict[str, Any] = {
        "status": "success",
        "message": f"{len(summary)} ImportedSBOM row(s)",
        "count": len(summary),
        "imports": summary,
    }
    out_dir = Path(args.output_dir) if args.output_dir else _default_output_dir(tenant)
    _write_json(out_dir / "list_imports.json", payload)
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print(payload["message"])
        print(f"Wrote {out_dir / 'list_imports.json'}")
    return 0


def main(argv: list[str] | None = None) -> int:
    """Run ``endor-sbom`` subcommands."""
    parser = _build_parser()
    args = parser.parse_args(argv)
    if args.command == "coverage":
        return _cmd_coverage(args)
    if args.command == "import":
        return _cmd_import(args)
    if args.command == "export":
        return _cmd_export(args)
    if args.command == "list-imports":
        return _cmd_list_imports(args)
    parser.error(f"unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    sys.exit(main())
