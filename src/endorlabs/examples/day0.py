"""Day-0 bounded probe ladder for consumer agents (Tier 0 → 2).

Run::

    uv run python -m endorlabs.examples.day0
    uv run python -m endorlabs.examples.day0 --dry-run
"""

from __future__ import annotations

import argparse
import sys


def _print_discovery() -> None:
    import endorlabs

    d = endorlabs.discover()
    print(f"endorlabs {d.version}")
    print(f"index: {d.index}")
    print(f"agents_guide: {d.agents_guide}")
    print(f"stub: {d.stub}")
    if d.resource_routes is not None:
        print(f"resource_routes: {d.resource_routes}")
    print("bootstrap_paths:")
    for path in d.bootstrap_paths:
        print(f"  - {path}")
    if d.entry_points:
        print("entry_points:", ", ".join(d.entry_points[:8]), end="")
        if len(d.entry_points) > 8:
            print(f", ... (+{len(d.entry_points) - 8} more)")
        else:
            print()


def _run_live_probe() -> int:
    import endorlabs

    client = endorlabs.Client()
    identity = client.whoami()
    print("whoami:", identity)

    projects = client.Project.list(traverse=True, max_pages=1)
    print(f"projects (max_pages=1, traverse=True): {len(projects)}")

    if projects:
        project = projects[0]
        scans = client.ScanResult.list_by_project(project, limit=1)
        scan_values = scans.values or []
        print(f"scan_results for first project: {len(scan_values)}")
        if scan_values:
            findings = client.Finding.list_for_context(scan_values[0], max_pages=1)
            finding_values = findings.values or []
            print(f"findings for latest scan: {len(finding_values)}")
    return 0


def main(argv: list[str] | None = None) -> int:
    """Run the day-0 discovery ladder (or ``--dry-run`` paths only)."""
    parser = argparse.ArgumentParser(
        description="Endor Labs SDK day-0 discovery ladder",
    )
    _ = parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print discover() paths only; skip Client() and API calls",
    )
    args = parser.parse_args(argv)

    _print_discovery()
    if args.dry_run:
        print("(dry-run: skipping live API probe)")
        return 0

    try:
        return _run_live_probe()
    except Exception as exc:
        print(f"live probe failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
