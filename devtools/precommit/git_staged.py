"""Git staged-path helpers for pre-commit and devtools entrypoints.

Policy checks belong in ``pre_commit_guards.py``; this module only lists and
normalizes staged paths. Shared normalization lives in ``endorlabs.utils.repo_paths``.
"""

from __future__ import annotations

import subprocess

from endorlabs.utils.repo_paths import normalize_repo_path

__all__ = [
    "diff_added_lines",
    "normalize_repo_path",
    "parse_unified_diff_added_lines",
    "staged_added_lines",
    "staged_paths",
]


def _git_text(*args: str) -> subprocess.CompletedProcess[str]:
    """Run git with UTF-8 stdout/stderr (Windows-safe for large/binary diffs)."""
    return subprocess.run(  # noqa: S603
        ["git", *args],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def staged_paths(*, diff_filter: str = "ACMR") -> list[str]:
    """Return POSIX paths staged for commit (``git diff --cached --name-only``)."""
    result = _git_text(
        "diff",
        "--cached",
        "--name-only",
        f"--diff-filter={diff_filter}",
    )
    if result.returncode != 0:
        msg = (result.stderr or result.stdout or "").strip()
        raise RuntimeError(f"git diff --cached failed: {msg}")
    paths: list[str] = []
    for line in (result.stdout or "").splitlines():
        normalized = normalize_repo_path(line)
        if normalized is not None:
            paths.append(normalized)
    return paths


def parse_unified_diff_added_lines(diff_text: str | None) -> list[tuple[str, int, str]]:
    """Parse ``(path, new_lineno, text)`` rows from a unified diff (``-U0`` style)."""
    rows: list[tuple[str, int, str]] = []
    path: str | None = None
    new_lineno = 0
    for raw in (diff_text or "").splitlines():
        if raw.startswith("+++ "):
            token = raw[4:].strip()
            if token == "/dev/null":
                path = None
                continue
            if token.startswith("b/"):
                token = token[2:]
            path = normalize_repo_path(token)
            continue
        if raw.startswith("@@ "):
            # @@ -old,count +new,count @@
            plus = raw.split(" ")[2] if len(raw.split(" ")) >= 3 else ""
            if plus.startswith("+"):
                start = plus[1:].split(",")[0]
                try:
                    new_lineno = int(start)
                except ValueError:
                    new_lineno = 0
            continue
        if path is None or not raw.startswith("+") or raw.startswith("+++"):
            continue
        rows.append((path, new_lineno, raw[1:]))
        new_lineno += 1
    return rows


def staged_added_lines() -> list[tuple[str, int, str]]:
    """Return ``(path, new_lineno, text)`` for lines added in the staged diff.

    Uses ``git diff --cached -U0`` so only newly introduced content is scanned
    (existing third-party doc links on untouched lines are not re-flagged).
    """
    result = _git_text(
        "diff",
        "--cached",
        "-U0",
        "--no-color",
        "--diff-filter=ACMR",
    )
    if result.returncode not in (0, 1):
        # git diff returns 1 when differences exist with some configs; treat
        # only hard failures as errors.
        msg = (result.stderr or result.stdout or "").strip()
        if result.returncode > 1:
            raise RuntimeError(f"git diff --cached failed: {msg}")
    return parse_unified_diff_added_lines(result.stdout)


def diff_added_lines(base: str, head: str = "HEAD") -> list[tuple[str, int, str]]:
    """Return added lines for ``git diff -U0 base...head`` (CI / PR scans)."""
    result = _git_text(
        "diff",
        "-U0",
        "--no-color",
        "--diff-filter=ACMR",
        f"{base}...{head}",
    )
    if result.returncode not in (0, 1):
        msg = (result.stderr or result.stdout or "").strip()
        if result.returncode > 1:
            raise RuntimeError(f"git diff {base}...{head} failed: {msg}")
    return parse_unified_diff_added_lines(result.stdout)
