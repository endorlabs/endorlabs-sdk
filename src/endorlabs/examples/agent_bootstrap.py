"""Agent bootstrap ladder: discovery map plus optional bounded API smoke test.

Run::

    uv run python -m endorlabs.examples.agent_bootstrap
    uv run python -m endorlabs.examples.agent_bootstrap --dry-run
"""

from __future__ import annotations

import argparse
import sys


def _print_discovery() -> None:
    import endorlabs

    print(endorlabs.discover())


def _run_live_smoke() -> int:
    import endorlabs

    client = endorlabs.Client()
    identity = client.whoami()
    print("whoami:", identity)

    projects = client.Project.list(traverse=True, max_pages=1)
    print(f"projects (max_pages=1, traverse=True): {len(projects)}")

    if projects:
        project = projects[0]
        scans = client.ScanResult.list_by_project(project, limit=1)
        print(f"scan_results for first project: {len(scans)}")
        if scans:
            findings = client.Finding.list_for_context(scans[0], max_pages=1)
            print(f"findings for latest scan: {len(findings)}")
    return 0


def main(argv: list[str] | None = None) -> int:
    """Print ``discover()`` map and optionally run a bounded auth/list smoke test."""
    parser = argparse.ArgumentParser(
        description="Endor Labs SDK agent bootstrap ladder",
    )
    _ = parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print discover() paths only; skip Client() and API calls",
    )
    args = parser.parse_args(argv)

    _print_discovery()
    if args.dry_run:
        print("(dry-run: skipping live API smoke test)")
        return 0

    try:
        return _run_live_smoke()
    except Exception as exc:
        print(f"live smoke test failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
