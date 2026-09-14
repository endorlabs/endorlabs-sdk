"""Console entrypoint: ``endor-config-presence``."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import endorlabs
from endorlabs.context.paths import task_activity_dir

from .config_presence import run_config_presence


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Probe Endor onboarding config presence (boolean / guided matrix). "
            "Read-only; does not mutate tenant state."
        ),
    )
    _ = parser.add_argument(
        "-n",
        "--tenant",
        required=True,
        help="Tenant namespace (auth + tenant-grain probes).",
    )
    _ = parser.add_argument(
        "--project",
        default=None,
        help="Optional project UUID (24-hex) for project-grain checks.",
    )
    _ = parser.add_argument(
        "--lookback-days",
        type=int,
        default=30,
        help="Lookback window for MAIN/CI scan presence (default: 30).",
    )
    _ = parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help=(
            "Directory for presence_result.json (default: "
            ".endorlabs/tasks/<slug>-<date>/onboarding_config_presence/)."
        ),
    )
    _ = parser.add_argument(
        "--json",
        action="store_true",
        help=(
            "Print full result JSON to stdout "
            "(still writes artifact when output-dir set)."
        ),
    )
    return parser


def _default_output_dir(tenant: str) -> Path:
    return Path(task_activity_dir(tenant, "onboarding_config_presence"))


def main(argv: list[str] | None = None) -> int:
    """Run config-presence CLI; write ``presence_result.json`` and exit status."""
    parser = _build_parser()
    args = parser.parse_args(argv)
    tenant = str(args.tenant).strip()
    client = endorlabs.Client(tenant=tenant)
    result = run_config_presence(
        client,
        tenant,
        project_uuid=args.project,
        lookback_days=int(args.lookback_days),
    )
    out_dir = args.output_dir or _default_output_dir(tenant)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "presence_result.json"
    payload = result.to_dict()
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print(result.message)
        print(f"wrote {out_path.resolve()}")
        fails = [c for c in result.checks if c.status == "fail"]
        warns = [c for c in result.checks if c.status == "warn"]
        if fails:
            print("fail:")
            for c in fails[:20]:
                print(f"  - {c.id}")
        if warns:
            print("warn:")
            for c in warns[:20]:
                hint = f" ({c.hint})" if c.hint else ""
                print(f"  - {c.id}{hint}")

    return 0 if result.status == "success" else 1


if __name__ == "__main__":
    sys.exit(main())
