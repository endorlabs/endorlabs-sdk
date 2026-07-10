"""Pre-commit guardrails: blocked staged paths, changelog reminders, layer bans.

Hook wiring lives in ``.pre-commit-config.yaml`` only. Staged-path listing is
``devtools/git_staged.py``; path normalization is ``endorlabs.utils.repo_paths``.

Policy: rule ``endor-maintainer-tooling`` (repo / Cursor mirror).
"""

from __future__ import annotations

import ast
import re
import sys
from pathlib import Path, PurePosixPath

from git_staged import staged_paths

BLOCKED_STAGED_PATHS = frozenset({".env"})
BLOCKED_STAGED_PREFIXES = (".endorlabs-context/",)

CHANGELOG_PATH = "docs/changelog.md"
CHANGELOG_POLICY = "agent-knowledge/rules/endor-changelog.md"

_REPO_ROOT = Path(__file__).resolve().parent.parent

_ESTATE_IMPORT_PREFIX = "endorlabs.workflows.estate"
_BOUNDS_SHIM = "endorlabs.workflows.estate.collect.bounds"
_WORKFLOWS_PREFIX = "src/endorlabs/workflows/"
_ESTATE_PREFIX = "src/endorlabs/workflows/estate/"
_TOOLS_PREFIX = "src/endorlabs/tools/"
_UTILS_PREFIX = "src/endorlabs/utils/"
_SRC_PREFIX = "src/endorlabs/"
_CONTEXT_PATHS_MODULE = "src/endorlabs/context/paths.py"
_CONTEXT_ROOT_LITERAL = ".endorlabs-context"

# Known intentional exceptions (path → allowed import prefixes).
_LAYER_ALLOWLIST: dict[str, frozenset[str]] = {
    "src/endorlabs/tools/callgraph_artifacts.py": frozenset(
        {"endorlabs.workflows.callgraph.render"}
    ),
    "src/endorlabs/utils/serialization.py": frozenset(
        {"endorlabs.workflows.wire_access"}
    ),
}

_DEPRECATED_API_PATTERNS = (
    re.compile(r"Project\.resolve\("),
    re.compile(r"\bParentShard\b"),
    re.compile(r"workflows\.findings\.filters"),
    re.compile(r"ScanResult\.list_for_project"),
)

_PROJECT_UUID_FILTER = re.compile(
    r"spec\.(?:importer_data\.)?project_uuid\s*=="
)

# High-confidence estate literals in agent/docs (warning-only).
_HEX_UUID = re.compile(r"\b[0-9a-f]{24}\b", re.IGNORECASE)
_GITHUB_ORG_REPO = re.compile(
    r"https?://github\.com/(?!org(?:/|$)|example(?:/|$)|YOUR_|<)"
    r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+"
)
_TENANT_PATH = re.compile(
    r"\b(?!tenant\.namespace\b|tenant\.child\b|tenant\.leaf\b|tenant\.root\b)"
    r"[a-z][a-z0-9-]{2,}\.[a-z][a-z0-9-]{2,}(?:\.[a-z0-9-]+)+\b"
)
_PORTABLE_ALLOW_MARKERS = (
    "placeholder",
    "<tenant>",
    "<namespace>",
    "<project-uuid>",
    "example.com",
    "tenant.namespace",
    "tenant.child",
    "org/repo",
)


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


def _normalize_path(path: str) -> str:
    return PurePosixPath(path.replace("\\", "/")).as_posix()


def _read_staged_text(path: str) -> str | None:
    full = _REPO_ROOT / path
    if not full.is_file():
        return None
    try:
        return full.read_text(encoding="utf-8")
    except OSError:
        return None


def _imported_modules(tree: ast.AST) -> set[str]:
    """Return fully-qualified module names referenced by import statements."""
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                names.add(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
            for alias in node.names:
                if alias.name != "*":
                    names.add(f"{node.module}.{alias.name}")
    return names


def _module_matches(modules: set[str], prefix: str) -> bool:
    return any(mod == prefix or mod.startswith(f"{prefix}.") for mod in modules)


def _allowed_import(path: str, module: str) -> bool:
    allowed = _LAYER_ALLOWLIST.get(path)
    if not allowed:
        return False
    return any(
        module == prefix or module.startswith(f"{prefix}.") for prefix in allowed
    )


def _imports_estate(modules: set[str]) -> bool:
    return _module_matches(modules, _ESTATE_IMPORT_PREFIX)


def _imports_bounds_shim(modules: set[str]) -> bool:
    return _module_matches(modules, _BOUNDS_SHIM)


def check_layer_imports(*, paths: list[str] | None = None) -> int:
    """Fail on forbidden cross-layer imports in staged Python files.

    Rules:
    - non-estate ``workflows/`` must not import ``endorlabs.workflows.estate``
    - ``src/endorlabs/**`` must not import ``devtools``
    - ``tools/`` must not import ``endorlabs.workflows`` (allowlisted exceptions)
    - ``utils/`` must not import ``endorlabs.tools`` / ``endorlabs.workflows``
      (allowlisted exceptions)
    """
    candidates = paths if paths is not None else staged_paths()
    violations: list[str] = []
    for path in candidates:
        normalized = _normalize_path(path)
        if not normalized.endswith(".py"):
            continue
        if not normalized.startswith(_SRC_PREFIX):
            continue
        source = _read_staged_text(normalized)
        if source is None:
            continue
        try:
            tree = ast.parse(source, filename=normalized)
        except SyntaxError:
            continue
        modules = _imported_modules(tree)

        if (
            normalized.startswith(_WORKFLOWS_PREFIX)
            and not normalized.startswith(_ESTATE_PREFIX)
            and _imports_estate(modules)
        ):
            violations.append(f"{normalized}: imports workflows.estate")

        if any(
            mod == "devtools" or mod.startswith("devtools.") for mod in modules
        ):
            violations.append(f"{normalized}: imports devtools")

        if normalized.startswith(_TOOLS_PREFIX):
            for mod in modules:
                workflows_hit = _module_matches({mod}, "endorlabs.workflows")
                if workflows_hit and not _allowed_import(normalized, mod):
                    violations.append(f"{normalized}: tools → {mod}")

        if normalized.startswith(_UTILS_PREFIX):
            for mod in modules:
                if _module_matches({mod}, "endorlabs.tools"):
                    violations.append(f"{normalized}: utils → {mod}")
                if _module_matches(
                    {mod}, "endorlabs.workflows"
                ) and not _allowed_import(normalized, mod):
                    violations.append(f"{normalized}: utils → {mod}")

    if not violations:
        return 0
    print(
        "error: forbidden cross-layer imports:\n"
        + "\n".join(f"  - {item}" for item in violations)
        + "\n\nSee endor-workflow-composition / sdk-alignment remediation.",
        file=sys.stderr,
    )
    return 1


def check_bounds_shim(*, paths: list[str] | None = None) -> int:
    """Fail when any src/ or tests/ file imports estate.collect.bounds."""
    candidates = paths if paths is not None else staged_paths()
    violations: list[str] = []
    for path in candidates:
        normalized = _normalize_path(path)
        if not normalized.endswith(".py"):
            continue
        if not (normalized.startswith("src/") or normalized.startswith("tests/")):
            continue
        source = _read_staged_text(normalized)
        if source is None:
            continue
        try:
            tree = ast.parse(source, filename=normalized)
        except SyntaxError:
            continue
        if _imports_bounds_shim(_imported_modules(tree)):
            violations.append(normalized)
    if not violations:
        return 0
    print(
        "error: estate.collect.bounds was removed; use endorlabs.tools.list_bounds:\n"
        + "\n".join(f"  - {path}" for path in violations),
        file=sys.stderr,
    )
    return 1


def _is_deprecated_api_scan_path(path: str) -> bool:
    normalized = _normalize_path(path)
    if normalized == CHANGELOG_PATH:
        return False
    return normalized.startswith(("agent-knowledge/", ".cursor/rules/", "docs/"))


def check_deprecated_api_strings(*, paths: list[str] | None = None) -> int:
    """Fail on staged agent/docs content referencing removed APIs as current usage."""
    candidates = paths if paths is not None else staged_paths()
    violations: list[str] = []
    allow_markers = ("removed", "breaking", "no longer", "deleted", "use `", "use **")
    for path in candidates:
        if not _is_deprecated_api_scan_path(path):
            continue
        source = _read_staged_text(path)
        if source is None:
            continue
        for line_no, line in enumerate(source.splitlines(), start=1):
            lower = line.lower()
            if any(marker in lower for marker in allow_markers):
                continue
            for pattern in _DEPRECATED_API_PATTERNS:
                if pattern.search(line):
                    violations.append(f"{path}:{line_no} ({pattern.pattern})")
                    break
    if not violations:
        return 0
    print(
        "error: deprecated API strings in agent/docs content:\n"
        + "\n".join(f"  - {item}" for item in violations)
        + "\n\nUse resolve_project_candidate / ProjectShard / endorlabs.filters / "
        "list_by_project. Historical notes belong only in docs/changelog.md Breaking.",
        file=sys.stderr,
    )
    return 1


def check_accessor_nudge(
    *,
    paths: list[str] | None = None,
    fail: bool = False,
) -> int:
    """Warn (or fail) on hand-built project_uuid filters in workflows."""
    candidates = paths if paths is not None else staged_paths()
    hits: list[str] = []
    for path in candidates:
        normalized = _normalize_path(path)
        if not normalized.endswith(".py"):
            continue
        if not normalized.startswith(_WORKFLOWS_PREFIX):
            continue
        source = _read_staged_text(normalized)
        if source is None:
            continue
        if not _PROJECT_UUID_FILTER.search(source):
            continue
        try:
            tree = ast.parse(source, filename=normalized)
        except SyntaxError:
            continue
        modules = _imported_modules(tree)
        if "endorlabs" in source and (
            "Client" in source or "list_by_project" in source or modules
        ):
            hits.append(normalized)
    if not hits:
        return 0
    label = "error" if fail else "warning"
    print(
        f"{label}: hand-built project_uuid filters in workflows "
        "(prefer list_by_project / list_for_context when equivalent):\n"
        + "\n".join(f"  - {path}" for path in hits),
        file=sys.stderr,
    )
    return 1 if fail else 0


def check_portable_examples(*, paths: list[str] | None = None) -> int:
    """Warn on high-confidence estate literals in staged agent/docs content."""
    candidates = paths if paths is not None else staged_paths()
    hits: list[str] = []
    for path in candidates:
        if not _is_deprecated_api_scan_path(path):
            continue
        source = _read_staged_text(path)
        if source is None:
            continue
        for line_no, line in enumerate(source.splitlines(), start=1):
            lower = line.lower()
            if any(marker in lower for marker in _PORTABLE_ALLOW_MARKERS):
                continue
            if (
                _HEX_UUID.search(line)
                or _GITHUB_ORG_REPO.search(line)
                or _TENANT_PATH.search(line)
            ):
                hits.append(f"{path}:{line_no}")
    if not hits:
        return 0
    print(
        "warning: possible estate identifiers in portable agent/docs content:\n"
        + "\n".join(f"  - {item}" for item in hits[:20])
        + (f"\n  - … and {len(hits) - 20} more" if len(hits) > 20 else "")
        + "\n\nPrefer placeholders (<tenant>, <project-uuid>, "
        "https://github.com/org/repo). See endor-portable-examples.",
        file=sys.stderr,
    )
    return 0


def check_agent_knowledge_sync(*, paths: list[str] | None = None) -> int:
    """Remind when agent-knowledge authoring is staged without shipped mirror."""
    candidates = paths if paths is not None else staged_paths()
    authoring = [
        p
        for p in candidates
        if _normalize_path(p).startswith("agent-knowledge/")
        and not _normalize_path(p).startswith("agent-knowledge/schema/")
    ]
    if not authoring:
        return 0
    shipped = any(
        _normalize_path(p).startswith("src/endorlabs/agent_knowledge/")
        for p in candidates
    )
    if shipped:
        return 0
    print(
        "reminder: staged agent-knowledge/ without src/endorlabs/agent_knowledge/:\n"
        + "\n".join(f"  - {path}" for path in authoring[:12])
        + "\n\nRun: uv run python devtools/sync_agent_knowledge.py\n"
        "Then stage the shipped mirror (or rely on the refresh hook).",
        file=sys.stderr,
    )
    return 0


def _is_context_root_scan_path(path: str) -> bool:
    """Python under src/endorlabs or agent-knowledge skill scripts (not paths.py)."""
    normalized = _normalize_path(path)
    if not normalized.endswith(".py"):
        return False
    if normalized == _CONTEXT_PATHS_MODULE:
        return False
    if "/generated/" in normalized:
        return False
    if normalized.startswith(_SRC_PREFIX):
        return True
    if normalized.startswith("agent-knowledge/") and "/scripts/" in normalized:
        return True
    return False


def _is_context_root_literal(value: object) -> bool:
    if not isinstance(value, str):
        return False
    if value == _CONTEXT_ROOT_LITERAL:
        return True
    return value.startswith(f"{_CONTEXT_ROOT_LITERAL}/") or value.startswith(
        f"{_CONTEXT_ROOT_LITERAL}\\"
    )


def check_context_root_literals(*, paths: list[str] | None = None) -> int:
    """Fail on hard-coded ``.endorlabs-context`` path constants outside paths.py.

    Catches ``Path(".endorlabs-context")``, default-arg strings, and similar AST
    string constants. Prose that only *mentions* the directory inside a longer
    string is allowed. Use ``DEFAULT_CONTEXT_DIR``, ``default_context_dir()``,
    ``default_runs_dir()``, or ``workspace_dir_for()`` instead.
    """
    candidates = paths if paths is not None else staged_paths()
    violations: list[str] = []
    for path in candidates:
        if not _is_context_root_scan_path(path):
            continue
        normalized = _normalize_path(path)
        source = _read_staged_text(normalized)
        if source is None:
            continue
        try:
            tree = ast.parse(source, filename=normalized)
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and _is_context_root_literal(node.value):
                violations.append(f"{normalized}:{node.lineno}")
    if not violations:
        return 0
    print(
        "error: hard-coded .endorlabs-context path constant(s):\n"
        + "\n".join(f"  - {item}" for item in violations)
        + "\n\nImport from endorlabs.context.paths "
        "(DEFAULT_CONTEXT_DIR, default_context_dir, default_runs_dir, "
        "workspace_dir_for). Only context/paths.py may define the literal.",
        file=sys.stderr,
    )
    return 1


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    usage = (
        "usage: pre_commit_guards.py "
        "{blocked-paths|changelog-reminder|layer-imports|bounds-shim|"
        "deprecated-api-strings|accessor-nudge|portable-examples|"
        "agent-knowledge-sync|context-root-literals}"
    )
    if not args or args[0] in {"-h", "--help"}:
        print(usage, file=sys.stderr)
        return 0 if args and args[0] in {"-h", "--help"} else 2
    command = args[0]
    if command == "blocked-paths":
        return check_blocked_staged_paths()
    if command == "changelog-reminder":
        return check_changelog_reminder()
    if command == "layer-imports":
        return check_layer_imports()
    if command == "bounds-shim":
        return check_bounds_shim()
    if command == "deprecated-api-strings":
        return check_deprecated_api_strings()
    if command == "accessor-nudge":
        fail = "--fail" in args[1:]
        return check_accessor_nudge(fail=fail)
    if command == "portable-examples":
        return check_portable_examples()
    if command == "agent-knowledge-sync":
        return check_agent_knowledge_sync()
    if command == "context-root-literals":
        return check_context_root_literals()
    print(f"error: unknown command {command!r}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
