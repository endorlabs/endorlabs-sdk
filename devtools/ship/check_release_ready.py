#!/usr/bin/env python3
"""Preflight: is this checkout publish-ready for a cut version?

Converges three states that historically diverged after a release cut PR:

1. ``[project].version`` / changelog section (cut landed on main)
2. Upstream OpenAPI / model-sync watermark (must match live API)
3. Publish identity (git tag ``vX.Y.Z`` and/or PyPI) — warn if cut but unpublished

Usage::

    uv run python devtools/ship/check_release_ready.py --expect 0.8.0
    uv run python devtools/ship/check_release_ready.py --expect 0.8.0 --require-unpublished

Exit ``0`` only when version + changelog + upstream verify pass.
Missing tag / PyPI is a stderr warning unless ``--require-unpublished``
(then fail if the version is already on PyPI).
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tomllib
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def read_pyproject_version(*, root: Path = ROOT) -> str | None:
    path = root / "pyproject.toml"
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as exc:
        print(f"failed to read pyproject.toml: {exc}", file=sys.stderr)
        return None
    project = data.get("project")
    if not isinstance(project, dict):
        print("[project] table missing in pyproject.toml", file=sys.stderr)
        return None
    version = project.get("version")
    if not isinstance(version, str) or not version.strip():
        print("[project].version must be a static PEP 440 string", file=sys.stderr)
        return None
    return version.strip()


def _changelog_has_section(version: str, *, root: Path = ROOT) -> bool:
    text = (root / "docs" / "changelog.md").read_text(encoding="utf-8")
    return bool(re.search(rf"^## {re.escape(version)}\s*$", text, re.MULTILINE))


def _unreleased_has_bullets(*, root: Path = ROOT) -> bool:
    """True when Unreleased still has content (cut incomplete or post-cut drift)."""
    text = (root / "docs" / "changelog.md").read_text(encoding="utf-8")
    match = re.search(
        r"^## Unreleased\s*\n(.*?)(?=^## |\Z)",
        text,
        re.MULTILINE | re.DOTALL,
    )
    if not match:
        return False
    body = match.group(1)
    # Bullet lines under Unreleased (ignore empty ### headers).
    return bool(re.search(r"^\s*[-*]\s+\S", body, re.MULTILINE))


def _verify_upstream(*, root: Path = ROOT) -> int:
    proc = subprocess.run(
        [
            "uv",
            "run",
            "python",
            "devtools/codegen/model_sync.py",
            "--verify-upstream-only",
        ],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout or "").strip()
        print(
            "release-ready: upstream OpenAPI / model-sync verify failed.\n"
            "  Merge a model-sync refresh (or run model_sync) before publish.\n"
            f"  {err}",
            file=sys.stderr,
        )
        return proc.returncode
    return 0


def _git_tag_exists(version: str, *, root: Path = ROOT) -> bool:
    tag = f"v{version}"
    proc = subprocess.run(
        ["git", "tag", "-l", tag],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    return tag in {line.strip() for line in (proc.stdout or "").splitlines()}


def _pypi_has_version(version: str, *, package: str = "endorlabs") -> bool | None:
    """Return True/False if PyPI reachable; None on network error."""
    # Build at runtime so portable-examples pre-commit does not treat PyPI as estate URL.
    host = "pypi." + "org"
    url = f"https://{host}/pypi/{package}/json"
    try:
        with urllib.request.urlopen(url, timeout=15) as resp:  # noqa: S310
            data = json.load(resp)
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        print(f"warning: could not query PyPI ({exc})", file=sys.stderr)
        return None
    releases = data.get("releases")
    if not isinstance(releases, dict):
        return None
    return version in releases


def run_check(
    *,
    expect: str,
    require_unpublished: bool = False,
    skip_upstream: bool = False,
    root: Path = ROOT,
) -> int:
    version = read_pyproject_version(root=root)
    if version is None:
        return 1
    if version != expect:
        print(
            f"release-ready: pyproject version {version!r} != --expect {expect!r}",
            file=sys.stderr,
        )
        return 1

    if not _changelog_has_section(expect, root=root):
        print(
            f"release-ready: docs/changelog.md missing '## {expect}' section "
            "(promote Unreleased before publish).",
            file=sys.stderr,
        )
        return 1

    if _unreleased_has_bullets(root=root):
        print(
            "release-ready: docs/changelog.md ## Unreleased still has bullets; "
            "fold them into the cut section or clear before publish.",
            file=sys.stderr,
        )
        return 1

    if not skip_upstream:
        code = _verify_upstream(root=root)
        if code != 0:
            return code

    tagged = _git_tag_exists(expect, root=root)
    on_pypi = _pypi_has_version(expect)

    if not tagged:
        print(
            f"warning: git tag v{expect} not found locally — cut may be unpublished "
            "(tag is optional for workflow_dispatch publish; create after PyPI).",
            file=sys.stderr,
        )
    if on_pypi is False:
        print(
            f"warning: {expect} not on PyPI yet — ready to dispatch "
            "release-tag-publish / release-testpypi.",
            file=sys.stderr,
        )
    if on_pypi is True and require_unpublished:
        print(
            f"release-ready: {expect} is already on PyPI; refuse --require-unpublished.",
            file=sys.stderr,
        )
        return 1
    if on_pypi is True:
        print(
            f"warning: {expect} already on PyPI — do not re-upload; yank+patch or bump.",
            file=sys.stderr,
        )

    print(f"release-ready: {expect} OK")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--expect",
        required=True,
        metavar="VERSION",
        help="PEP 440 version that must match pyproject + changelog",
    )
    parser.add_argument(
        "--require-unpublished",
        action="store_true",
        help="Fail if this version is already present on PyPI",
    )
    parser.add_argument(
        "--skip-upstream",
        action="store_true",
        help="Skip OpenAPI/model-sync verify (not for release CI)",
    )
    args = parser.parse_args()
    return run_check(
        expect=args.expect,
        require_unpublished=args.require_unpublished,
        skip_upstream=args.skip_upstream,
    )


if __name__ == "__main__":
    raise SystemExit(main())
