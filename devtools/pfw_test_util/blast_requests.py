"""PFW test util — blast known-blocked package requests against Package Firewall.

Env-scoped maintainer helper (not shipped in the wheel). Uses ``ENDOR_NAMESPACE``
and firewall basic-auth credentials from the environment / dotenv.

Expected outcome for ``endor-firewall-test@1.0.0`` is HTTP 403 (policy BLOCK).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import quote

import httpx

FACTORY_BASE = "https://factory.endorlabs.com/v1/namespaces"
DEFAULT_PACKAGE = "endor-firewall-test"
DEFAULT_VERSION = "1.0.0"

# Credential env keys (first match wins).
_USER_KEYS = (
    "UV_INDEX_ENDOR_FIREWALL_USERNAME",
    "ENDOR_FIREWALL_USERNAME",
    "ENDOR_FIREWALL_USER",
)
_PASSWORD_KEYS = (
    "UV_INDEX_ENDOR_FIREWALL_PASSWORD",
    "ENDOR_FIREWALL_PASSWORD",
    "ENDOR_FIREWALL_TOKEN",
)


@dataclass(frozen=True)
class BlastTarget:
    """One factory URL to GET."""

    ecosystem: str
    label: str
    url: str
    expect_block: bool = False


@dataclass
class BlastResult:
    """Outcome of a single GET."""

    ecosystem: str
    label: str
    url: str
    status_code: int | None
    error: str | None
    expected_block: bool

    @property
    def ok(self) -> bool:
        """True when asserted probes match; informational probes only need a response."""
        if self.error:
            return False
        if self.expected_block:
            return self.status_code == 403
        if "control" in self.label.lower():
            return self.status_code is not None and 200 <= self.status_code < 400
        # Observational probe: any HTTP response is success for exit scoring.
        return self.status_code is not None


def _first_env(*keys: str) -> str | None:
    for key in keys:
        value = os.getenv(key)
        if value and value.strip():
            return value.strip()
    return None


def resolve_namespace(explicit: str | None = None) -> str:
    """Resolve namespace from CLI or ``ENDOR_NAMESPACE``."""
    ns = (explicit or os.getenv("ENDOR_NAMESPACE") or "").strip()
    if not ns:
        raise SystemExit(
            "Namespace required: pass -n/--namespace or set ENDOR_NAMESPACE."
        )
    return ns


def resolve_credentials() -> tuple[str, str]:
    """Resolve Package Firewall basic-auth username/password from the environment."""
    user = _first_env(*_USER_KEYS)
    password = _first_env(*_PASSWORD_KEYS)
    if not user or not password:
        raise SystemExit(
            "Firewall credentials required. Set "
            "UV_INDEX_ENDOR_FIREWALL_USERNAME / UV_INDEX_ENDOR_FIREWALL_PASSWORD "
            "(or ENDOR_FIREWALL_USERNAME / ENDOR_FIREWALL_PASSWORD)."
        )
    return user, password


def build_targets(
    namespace: str,
    *,
    package: str = DEFAULT_PACKAGE,
    version: str = DEFAULT_VERSION,
    include_controls: bool = False,
) -> list[BlastTarget]:
    """Build npm + PyPI factory URLs for the test package (optional benign controls)."""
    base = f"{FACTORY_BASE}/{quote(namespace, safe='')}/firewall"
    pkg = quote(package, safe="")
    ver = quote(version, safe="")
    targets = [
        BlastTarget(
            "npm",
            f"{package}@{version} metadata",
            f"{base}/npm/{pkg}",
            expect_block=False,
        ),
        BlastTarget(
            "npm",
            f"{package}@{version} version",
            f"{base}/npm/{pkg}/{ver}",
            expect_block=True,
        ),
        BlastTarget(
            "pypi",
            f"{package} simple index",
            f"{base}/pypi/simple/{pkg}/",
            expect_block=False,
        ),
        BlastTarget(
            "pypi",
            f"{package}@{version} json",
            f"{base}/pypi/json/{pkg}/{ver}",
            expect_block=False,
        ),
    ]
    if include_controls:
        targets.extend(
            [
                BlastTarget(
                    "pypi",
                    "boto3 simple (control)",
                    f"{base}/pypi/simple/boto3/",
                    expect_block=False,
                ),
                BlastTarget(
                    "npm",
                    "lodash metadata (control)",
                    f"{base}/npm/lodash",
                    expect_block=False,
                ),
            ]
        )
    return targets


def blast_requests(
    targets: list[BlastTarget],
    *,
    username: str,
    password: str,
    timeout: float = 30.0,
) -> list[BlastResult]:
    """GET each target with basic auth; return per-URL results."""
    results: list[BlastResult] = []
    with httpx.Client(
        timeout=timeout,
        follow_redirects=False,
        auth=(username, password),
    ) as client:
        for target in targets:
            try:
                response = client.get(target.url)
                results.append(
                    BlastResult(
                        ecosystem=target.ecosystem,
                        label=target.label,
                        url=target.url,
                        status_code=response.status_code,
                        error=None,
                        expected_block=target.expect_block,
                    )
                )
            except Exception as exc:
                results.append(
                    BlastResult(
                        ecosystem=target.ecosystem,
                        label=target.label,
                        url=target.url,
                        status_code=None,
                        error=f"{type(exc).__name__}: {exc}",
                        expected_block=target.expect_block,
                    )
                )
    return results


def _default_report_path(namespace: str) -> Path:
    # Lazy import so unit-style imports of helpers stay light if paths missing.
    from endorlabs.context.paths import default_runs_dir, sanitize_path_segment

    runs = default_runs_dir("pfw-test-util")
    runs.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(tz=UTC).strftime("%Y%m%dT%H%M%SZ")
    slug = sanitize_path_segment(namespace)
    return runs / f"{slug}-blast-{stamp}.json"


def write_report(path: Path, *, namespace: str, results: list[BlastResult]) -> None:
    """Write a JSON summary suitable for pairing with ``endor-log-export``."""
    path.parent.mkdir(parents=True, exist_ok=True)
    payload: dict[str, Any] = {
        "namespace": namespace,
        "generated_at": datetime.now(tz=UTC).isoformat(),
        "package": DEFAULT_PACKAGE,
        "version": DEFAULT_VERSION,
        "results": [asdict(r) for r in results],
        "ok_count": sum(1 for r in results if r.ok),
        "total": len(results),
    }
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "PFW test util: GET Package Firewall factory URLs for "
            f"{DEFAULT_PACKAGE}@{DEFAULT_VERSION} (expect 403 BLOCK)."
        ),
    )
    _ = parser.add_argument(
        "-n",
        "--namespace",
        default=None,
        help="Tenant/namespace path (default: ENDOR_NAMESPACE).",
    )
    _ = parser.add_argument(
        "--include-controls",
        action="store_true",
        help="Also request benign control packages (expect non-403).",
    )
    _ = parser.add_argument(
        "--report",
        type=Path,
        default=None,
        help="Write JSON summary path (default under workspace/runs/pfw-test-util/).",
    )
    _ = parser.add_argument(
        "--timeout",
        type=float,
        default=30.0,
        help="HTTP timeout seconds (default: 30).",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI entry for ``uv run python devtools/pfw_test_util/blast_requests.py``."""
    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        namespace = resolve_namespace(args.namespace)
        username, password = resolve_credentials()
    except SystemExit as exc:
        print(str(exc), file=sys.stderr)
        return 2

    targets = build_targets(
        namespace,
        include_controls=bool(args.include_controls),
    )
    results = blast_requests(
        targets,
        username=username,
        password=password,
        timeout=float(args.timeout),
    )
    report = args.report or _default_report_path(namespace)
    write_report(report, namespace=namespace, results=results)

    for row in results:
        status = row.status_code if row.status_code is not None else "ERR"
        mark = "OK" if row.ok else "FAIL"
        detail = row.error or ""
        print(f"[{mark}] {status} {row.ecosystem} {row.label} {detail}".rstrip())
    print(f"Report: {report}")

    return 0 if all(r.ok for r in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
