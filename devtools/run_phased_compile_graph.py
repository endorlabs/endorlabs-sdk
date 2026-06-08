#!/usr/bin/env python3
"""Run endor-compile-dependency-graph phases sequentially with auth preflight.

Customer estates (e.g. cross-tenant reads) require a valid **ENDOR_TOKEN** from
admin SSO — API keys alone often 403 on list operations. Refresh first:

  uv run python devtools/refresh_token_to_dotenv.py --admin --timeout 600

Does not print secrets.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
_PHASES = (
    "discover_projects",
    "filter_git_repositories",
    "build_publisher_index",
    "collect_dependencies",
    "build_graph",
    "enrich_graph",
    "graph_analytics",
    "partition_graph",
)


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--tenant", required=True, help="Client tenant for endorlabs.Client")
    p.add_argument("--namespace", required=True, help="Estate namespace root")
    p.add_argument(
        "--from-phase",
        choices=_PHASES,
        default=_PHASES[0],
        help="First phase to run (default: discover_projects)",
    )
    p.add_argument(
        "--to-phase",
        choices=_PHASES,
        default=_PHASES[-1],
        help="Last phase to run (default: partition_graph)",
    )
    p.add_argument("--env-file", type=Path, default=Path(".env"))
    p.add_argument("--max-workers", type=int, default=16)
    p.add_argument(
        "--request-timeout",
        type=int,
        default=None,
        help="Set ENDOR_REQUEST_TIMEOUT for the child process (seconds).",
    )
    p.add_argument(
        "--summarize",
        action="store_true",
        help="Run endor-graph-summarize --json after the last phase succeeds.",
    )
    return p.parse_args()


def _phase_slice(start: str, end: str) -> list[str]:
    names = list(_PHASES)
    i0 = names.index(start)
    i1 = names.index(end)
    if i0 > i1:
        raise SystemExit("--from-phase must not be after --to-phase")
    return names[i0 : i1 + 1]


def _env_file_for_uv(env_file: Path) -> str:
    return env_file.resolve().as_posix()


def _auth_ok(tenant: str, env_file: Path) -> bool:
    env = os.environ.copy()
    code = subprocess.call(
        [
            "uv",
            "run",
            "--env-file",
            _env_file_for_uv(env_file),
            "python",
            "-c",
            (
                "import endorlabs; "
                f"c=endorlabs.Client(tenant={tenant!r}); "
                "ok=bool(c.whoami()); c.close(); "
                "raise SystemExit(0 if ok else 1)"
            ),
        ],
        cwd=_REPO,
        env=env,
    )
    return code == 0


def _validation_ok(session_dir: Path, phase: str) -> bool | None:
    path = session_dir / f"phase_{phase}_validation.json"
    if not path.is_file():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    return bool(data.get("ok"))


def _run_phase(
    *,
    tenant: str,
    namespace: str,
    phase: str,
    env_file: Path,
    max_workers: int,
    request_timeout: int | None,
) -> int:
    cmd = [
        "uv",
        "run",
        "--env-file",
        _env_file_for_uv(env_file),
        "endor-compile-dependency-graph",
        "--tenant",
        tenant,
        "--namespace",
        namespace,
        "--phase",
        phase,
        "--max-workers",
        str(max_workers),
    ]
    env = os.environ.copy()
    if request_timeout is not None:
        env["ENDOR_REQUEST_TIMEOUT"] = str(request_timeout)
    return subprocess.call(cmd, cwd=_REPO, env=env)


def main() -> int:
    args = _parse_args()
    phases = _phase_slice(args.from_phase, args.to_phase)
    env_file = args.env_file.resolve()
    if not env_file.is_file():
        print(f"Missing env file: {env_file}", file=sys.stderr)
        return 1

    if not _auth_ok(args.tenant, env_file):
        print(
            "Auth preflight failed (whoami). For customer tenants refresh admin SSO:\n"
            "  uv run python devtools/refresh_token_to_dotenv.py --admin --timeout 600\n"
            "Complete the browser callback on localhost:30000, then re-run this script.",
            file=sys.stderr,
        )
        return 1

    slug = args.namespace.strip().rstrip(".").replace(".", "_") or "unknown"
    session_dir = _REPO / ".endorlabs-context" / "session" / slug

    for phase in phases:
        workers = args.max_workers
        print(f"=== phase {phase} (max_workers={workers}) ===", flush=True)
        t0 = time.monotonic()
        rc = _run_phase(
            tenant=args.tenant,
            namespace=args.namespace,
            phase=phase,
            env_file=env_file,
            max_workers=workers,
            request_timeout=args.request_timeout,
        )
        elapsed = time.monotonic() - t0
        val = _validation_ok(session_dir, phase)
        print(
            f"phase {phase}: exit={rc} elapsed={elapsed:.0f}s validation={val}",
            flush=True,
        )
        if rc != 0 or val is False:
            return 1

    if args.summarize:
        rc = subprocess.call(
            [
                "uv",
                "run",
                "--env-file",
                _env_file_for_uv(env_file),
                "endor-graph-summarize",
                "--namespace",
                args.namespace,
                "--json",
            ],
            cwd=_REPO,
        )
        if rc != 0:
            return rc

    print(f"Session: {session_dir}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
