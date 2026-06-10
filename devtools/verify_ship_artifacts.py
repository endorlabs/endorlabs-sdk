"""Verify committed ship artifacts match model-sync and agent-knowledge outputs.

Run from repo root::

    uv run python devtools/verify_ship_artifacts.py --fetch-spec
    uv run python devtools/verify_ship_artifacts.py --verify-changelog 0.1.2

Used by CI, release, and TestPyPI workflows to ensure published wheels match the
tagged commit (no silent regeneration drift).
"""
# ruff: noqa: D103, S603

from __future__ import annotations

import argparse
import logging
import re
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SPEC_URL = "https://api.endorlabs.com/download/openapiv2.swagger.json"
SPEC_REL = Path(".endorlabs-context/platform/openapi/openapiv2.swagger.json")
CHANGELOG_REL = Path("docs/changelog.md")

SHIP_GIT_PATHS: tuple[str, ...] = (
    "src/endorlabs/generated/registry_contract.py",
    "src/endorlabs/generated/create_convenience.py",
    "src/endorlabs/generated/models",
    "src/endorlabs/client_surface.pyi",
    "docs/generated-reference/resources.md",
    "docs/generated-reference/create-update-payloads.md",
    "docs/generated-reference/api-surfaces.md",
    "docs/generated-reference/coverage.json",
    "docs/generated-reference/resources",
)


def repo_root() -> Path:
    return REPO_ROOT


def ship_git_paths() -> tuple[str, ...]:
    """Relative paths passed to ``git diff --exit-code`` after regeneration."""
    return SHIP_GIT_PATHS


def changelog_has_version(changelog_text: str, version: str) -> bool:
    """Return True when *changelog_text* contains a ``## {version}`` section."""
    pattern = re.compile(rf"^##\s+{re.escape(version)}\s*$", re.MULTILINE)
    return pattern.search(changelog_text) is not None


def verify_changelog_version(version: str, *, root: Path | None = None) -> str | None:
    """Return an error message when the changelog lacks ``## {version}``."""
    base = root or repo_root()
    path = base / CHANGELOG_REL
    if not path.is_file():
        return f"Changelog not found: {path}"
    text = path.read_text(encoding="utf-8")
    if changelog_has_version(text, version):
        return None
    return (
        f"docs/changelog.md missing '## {version}' section "
        "(promote Unreleased before tagging)"
    )


def fetch_openapi_spec(url: str, dest: Path) -> str | None:
    """Download OpenAPI JSON to *dest*. Return error message on failure."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(  # noqa: S310
        url,
        headers={"User-Agent": "endorlabs-verify-ship-artifacts"},
    )
    try:
        with urllib.request.urlopen(request, timeout=120.0) as resp:  # noqa: S310
            dest.write_bytes(resp.read())
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        return f"Failed to download OpenAPI spec from {url}: {exc}"
    return None


def _run(cmd: list[str], *, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=cwd,
        check=False,
        capture_output=True,
        text=True,
    )


def git_diff_dirty(paths: tuple[str, ...], *, root: Path) -> str | None:
    """Return error message when *paths* differ from HEAD after regeneration."""
    result = _run(["git", "diff", "--exit-code", "--", *paths], cwd=root)
    if result.returncode == 0:
        return None
    stat = _run(["git", "diff", "--stat", "--", *paths], cwd=root)
    detail = (stat.stdout or stat.stderr or "").strip()
    return (
        "Committed ship artifacts are out of date after regeneration. "
        "Run: uv run python devtools/model_sync.py --fetch-spec "
        "--generate-stubs --generate-reference-docs\n"
        f"{detail}"
    )


def run_verify(
    *,
    fetch_spec: bool = False,
    spec_url: str = DEFAULT_SPEC_URL,
    verify_changelog: str | None = None,
    root: Path | None = None,
) -> int:
    """Run the full ship-artifact verification pipeline. Return exit code."""
    base = root or repo_root()
    spec_path = base / SPEC_REL

    if verify_changelog:
        changelog_err = verify_changelog_version(verify_changelog, root=base)
        if changelog_err:
            logger.error("%s", changelog_err)
            return 1

    if fetch_spec:
        fetch_err = fetch_openapi_spec(spec_url, spec_path)
        if fetch_err:
            logger.error("%s", fetch_err)
            return 1
    elif not spec_path.is_file():
        logger.error(
            "OpenAPI spec not found at %s. Pass --fetch-spec or bootstrap with "
            "endorlabs.init(include_openapi=True).",
            spec_path,
        )
        return 1

    upstream = _run(
        [sys.executable, "devtools/model_sync.py", "--verify-upstream-only"],
        cwd=base,
    )
    if upstream.returncode != 0:
        msg = (upstream.stdout or upstream.stderr or "").strip()
        logger.error("Upstream OpenAPI verify failed.\n%s", msg)
        return upstream.returncode

    regen = _run(
        [
            sys.executable,
            "devtools/model_sync.py",
            "--generate-stubs",
            "--generate-reference-docs",
        ],
        cwd=base,
    )
    if regen.returncode != 0:
        msg = (regen.stdout or regen.stderr or "").strip()
        logger.error("Model sync regeneration failed.\n%s", msg)
        return regen.returncode

    for rel in (
        "src/endorlabs/generated/registry_contract.py",
        "src/endorlabs/generated/models/__init__.py",
    ):
        if not (base / rel).is_file():
            logger.error("Expected generated file missing: %s", rel)
            return 1

    diff_err = git_diff_dirty(ship_git_paths(), root=base)
    if diff_err:
        logger.error("%s", diff_err)
        return 1

    agents = _run(
        [sys.executable, "devtools/sync_agent_knowledge.py", "--verify"],
        cwd=base,
    )
    if agents.returncode != 0:
        msg = (agents.stdout or agents.stderr or "").strip()
        logger.error("Agent knowledge verify failed.\n%s", msg)
        return agents.returncode

    logger.info(
        "Ship artifacts verified: upstream match, regen clean, agent knowledge OK."
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--fetch-spec",
        action="store_true",
        help="Download OpenAPI spec before verification",
    )
    parser.add_argument(
        "--spec-url",
        default=DEFAULT_SPEC_URL,
        help=f"OpenAPI download URL (default: {DEFAULT_SPEC_URL})",
    )
    parser.add_argument(
        "--verify-changelog",
        metavar="VERSION",
        help="Require docs/changelog.md to contain ## VERSION",
    )
    args = parser.parse_args(argv)
    return run_verify(
        fetch_spec=args.fetch_spec,
        spec_url=args.spec_url,
        verify_changelog=args.verify_changelog,
    )


if __name__ == "__main__":
    raise SystemExit(main())
