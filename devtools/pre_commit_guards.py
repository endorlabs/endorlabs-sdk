"""Pre-commit guardrails: blocked staged paths and changelog reminders.

Hook wiring lives in ``.pre-commit-config.yaml`` only. Staged-path listing is
``devtools/git_staged.py``; path normalization is ``endorlabs.utils.repo_paths``.

Policy: rule ``endor-maintainer-tooling`` (repo / Cursor mirror).
"""

from __future__ import annotations

import sys
from pathlib import PurePosixPath

from git_staged import staged_paths

BLOCKED_STAGED_PATHS = frozenset({".env"})
BLOCKED_STAGED_PREFIXES = (".endorlabs-context/",)

CHANGELOG_PATH = "docs/changelog.md"
CHANGELOG_POLICY = "agent-knowledge/rules/endor-changelog.md"


def is_blocked_staged_path(path: str) -> bool:
    normalized = PurePosixPath(path.replace("\\", "/")).as_posix()
    if normalized in BLOCKED_STAGED_PATHS:
        return True
    return any(normalized.startswith(prefix) for prefix in BLOCKED_STAGED_PREFIXES)


def check_blocked_staged_paths() -> int:
    """Fail when gitignored runtime paths are staged (``git add -f`` accidents)."""
    blocked = [path for path in staged_paths() if is_blocked_staged_path(path)]
    if not blocked:
        return 0
    print(
        "error: refuse to commit gitignored runtime paths:\n"
        + "\n".join(f"  - {path}" for path in blocked)
        + "\n\nUnstage them (e.g. git restore --staged <path>). "
        "Keep secrets and session output in .env / .endorlabs-context/ only.",
        file=sys.stderr,
    )
    return 1


def is_user_facing_staged_path(path: str) -> bool:
    """Heuristic for product-facing changes needing a changelog Unreleased line."""
    normalized = PurePosixPath(path.replace("\\", "/")).as_posix()
    if normalized == CHANGELOG_PATH:
        return False
    if normalized.startswith(
        (
            "tests/",
            "devtools/",
            ".github/",
            ".cursor/",
            "CONTRIBUTORS.md",
            "AGENTS.md",
        )
    ):
        return False
    if normalized.startswith("docs/generated-reference/"):
        return False
    if normalized.startswith("src/endorlabs/generated/"):
        return False
    if normalized == "README.md":
        return True
    if normalized.startswith("agent-knowledge/"):
        return True
    if normalized.startswith("src/endorlabs/"):
        return True
    if normalized.startswith("docs/"):
        return True
    return False


def check_changelog_reminder() -> int:
    """Print a reminder (exit 0) when user-facing files omit docs/changelog.md."""
    paths = staged_paths()
    if not paths:
        return 0
    user_facing = [path for path in paths if is_user_facing_staged_path(path)]
    if not user_facing:
        return 0
    if CHANGELOG_PATH in paths:
        return 0
    print(
        "reminder: staged user-facing paths without docs/changelog.md:\n"
        + "\n".join(f"  - {path}" for path in user_facing[:12])
        + (f"\n  - … and {len(user_facing) - 12} more" if len(user_facing) > 12 else "")
        + f"\n\nIf the change is user-visible, add a bullet under "
        f"**Unreleased** in {CHANGELOG_PATH} "
        f"(see {CHANGELOG_POLICY} and .github/pull_request_template.md). "
        "If not user-facing, no action needed.",
        file=sys.stderr,
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    if not args or args[0] in {"-h", "--help"}:
        print(
            "usage: pre_commit_guards.py {blocked-paths|changelog-reminder}",
            file=sys.stderr,
        )
        return 0 if args and args[0] in {"-h", "--help"} else 2
    command = args[0]
    if command == "blocked-paths":
        return check_blocked_staged_paths()
    if command == "changelog-reminder":
        return check_changelog_reminder()
    print(f"error: unknown command {command!r}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
