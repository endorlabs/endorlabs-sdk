"""Pre-commit guardrails: blocked staged paths, changelog reminders, layer bans.

Hook wiring lives in ``.pre-commit-config.yaml`` only. Staged-path listing is
``devtools/precommit/git_staged.py``; path normalization is
``endorlabs.utils.repo_paths``.

Policy: rule ``endor-maintainer-tooling`` (repo / Cursor mirror).
"""

from __future__ import annotations

import ast
import re
import subprocess
import sys
from pathlib import Path, PurePosixPath

from git_staged import diff_added_lines, staged_added_lines, staged_paths

BLOCKED_STAGED_PATHS = frozenset({".env"})
BLOCKED_STAGED_PREFIXES = (".endorlabs-context/",)

CHANGELOG_PATH = "docs/changelog.md"
CHANGELOG_POLICY = "agent-knowledge/rules/endor-changelog.md"

_REPO_ROOT = Path(__file__).resolve().parents[2]

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

_PROJECT_UUID_FILTER = re.compile(r"spec\.(?:importer_data\.)?project_uuid\s*==")

# High-confidence estate literals (fail on staged checked-in text paths).
_HEX_UUID = re.compile(r"\b[0-9a-f]{24}\b", re.IGNORECASE)
_GITHUB_ORG_REPO = re.compile(
    r"https?://github\.com/"
    r"(?P<org>[A-Za-z0-9_.-]+)/(?P<repo>[A-Za-z0-9_.-]+)",
    re.IGNORECASE,
)
_GITHUB_ALLOW_ORGS = frozenset(
    {
        "endorlabs",
        "org",
        "example",
        "your_org",
        "your-org",
        "semgrep",
        "trailofbits",
        "astral-sh",
        "pre-commit",
        "psf",
        "pypa",
        "pytest-dev",
        "python",
        "codespell-project",
        "gitleaks",
        "github",
        "actions",
        "dependabot",
        "openai",
        "anthropics",
        "cursor",
        "modelcontextprotocol",
        "pycqa",
        "pyca",
        "owner",
        "acme",
        "o",
        "a",
        "b",
        "yarpc",
    }
)
# Multi-segment dotted paths that look like Endor namespaces, not public DNS
# or Python import paths (endorlabs.*).
_TENANT_PATH = re.compile(
    r"\b(?!tenant\.namespace\b|tenant\.child\b|tenant\.leaf\b|tenant\.root\b|"
    r"endorlabs\b)"
    r"[a-z][a-z0-9-]{2,}\.[a-z][a-z0-9-]{2,}(?:\.[a-z0-9-]+)+\b"
)
_PUBLIC_DNS_TLDS = frozenset(
    {
        "com",
        "org",
        "net",
        "io",
        "ai",
        "dev",
        "app",
        "cloud",
        "co",
        "uk",
        "us",
        "edu",
        "gov",
        "info",
        "biz",
        "xyz",
    }
)
# Last segment looks like a filename extension, not a namespace leaf.
_FILE_EXT_SEGMENTS = frozenset(
    {
        "json",
        "yml",
        "yaml",
        "md",
        "mdc",
        "py",
        "pyi",
        "toml",
        "txt",
        "lock",
        "svg",
        "png",
        "jpg",
        "jpeg",
        "gif",
        "webp",
        "html",
        "css",
        "js",
        "ts",
        "tsx",
        "sh",
        "ps1",
        "bat",
        "cfg",
        "ini",
        "rst",
        "csv",
        "xml",
        "proto",
        "whl",
        "gz",
        "zip",
    }
)
# Intermediate segments that mark CI / schema / code / API field paths.
_CODE_PATH_SEGMENTS = frozenset(
    {
        "outputs",
        "result",
        "results",
        "changes",
        "steps",
        "needs",
        "inputs",
        "jobs",
        "schema",
        "swagger",
        "workflow",
        "workflows",
        "github",
        "actions",
        "meta",
        "spec",
        "uuid",
        "name",
        "config",
        "environment",
        "parent",
        "mkdir",
        "joinpath",
        "resolve",
        "replace",
        "split",
        "strip",
        "lower",
        "upper",
        "format",
        "encode",
        "decode",
        "palette",
        "foreground",
        "background",
        "stroke",
        "tertiary",
        "theme",
        "args",
        "logging",
        "listen",
        "collect",
        "bounds",
        "rule",
        "output",
        "path",
        "paths",
        "client",
        "request",
        "response",
        "headers",
        "status",
        "error",
        "errors",
        "value",
        "values",
        "items",
        "keys",
        "data",
        "json",
        "text",
        "read",
        "write",
        "open",
        "close",
    }
)
_PORTABLE_ALLOW_MARKERS = (
    "placeholder",
    "<tenant>",
    "<namespace>",
    "<project-uuid>",
    "example.com",
    "example-tenant",
    "tenant.namespace",
    "tenant.child",
    "org/repo",
)
# First segment of dotted tokens that are code/import paths, not namespaces.
_TENANT_PATH_SKIP_ROOTS = frozenset(
    {
        "endorlabs",
        "tests",
        "test",
        "src",
        "docs",
        "devtools",
        "agent",
        "workflows",
        "unit",
        "integration",
        "github",
        "actions",
        "cursor",
        "pre",
        "py",
        "uv",
        "os",
        "sys",
        "typing",
        "collections",
        "concurrent",
        "importlib",
        "pathlib",
        "pydantic",
        "pytest",
        "httpx",
        "urllib",
        "email",
        "steps",
        "needs",
        "skill",
        "changelog",
        "openapiv2",
        "detect",
        "verifytypes",
        "resolve",
        "jobs",
        "inputs",
        "tool",
        "project",
        "hatch",
        "ruff",
        "lint",
    }
)

# --- Security content: emails, non-Endor URLs, namespace CLI flags (added lines) ---

_EMAIL_RE = re.compile(
    r"(?<![A-Za-z0-9._%+\-])"
    r"[A-Za-z0-9._%+\-]+@"
    r"[A-Za-z0-9.\-]+\.[A-Za-z]{2,}"
    r"(?![A-Za-z0-9.\-])"
)
_URL_RE = re.compile(
    r"https?://(?:[A-Za-z0-9\-]+\.)+[A-Za-z]{2,}(?::\d+)?(?:/[^\s<>\"')\]]*)?",
    re.IGNORECASE,
)
_NAMESPACE_FLAG_RE = re.compile(
    r"(?:^|[\s`\"'(=])(?:-n|--namespace|--tenant|--target-tenant)"
    r"(?:[\s=]+|[\s]*=[\s]*)[\"']?"
    r"("
    r"<[^>\s]+>"
    r"|"
    r"\{[A-Za-z_][A-Za-z0-9_]*\}"
    r"|"
    r"\$[A-Za-z_][A-Za-z0-9_]*"
    r"|"
    r"[A-Za-z][A-Za-z0-9_.-]{0,127}"
    r")"
    r"(?![A-Za-z0-9_.-])",
)

# Domains allowed in email addresses (placeholders + Endor Labs).
_EMAIL_ALLOW_DOMAINS = frozenset(
    {
        "example.com",
        "example.org",
        "example.net",
        "endorlabs.com",
        "endor.ai",
    }
)

# Host suffixes owned by Endor Labs (URL allow).
_ENDOR_URL_HOST_SUFFIXES = ("endorlabs.com", "endor.ai")

# Path prefixes on github.com that are Endor-owned.
_ENDOR_GITHUB_PREFIXES = ("endorlabs/",)

# Placeholder / schema-example URL hosts (not customer estate).
_PLACEHOLDER_URL_HOSTS = frozenset(
    {
        "example.com",
        "example.org",
        "example.net",
        "www.example.com",
    }
)
_PLACEHOLDER_GITHUB_PREFIXES = (
    "org/",
    "example/",
    "YOUR_ORG/",
)

# Allowed CLI / kwarg namespace tokens (placeholders + CI defaults).
# Bare customer-looking names are rejected; prefer example-* or <angle> forms.
_NAMESPACE_FLAG_ALLOW = frozenset(
    {
        "example",
        "example-tenant",
        "example-namespace",
        "demo",
        "test",
        "local",
        "oss",
        "endor-admin",
        "auri",
        "your-tenant",
        "your_tenant",
        "YOUR_TENANT",
        "NAMESPACE",
        "NS",
        "namespace",
        "namespace_scope",
        "project-namespace",
        "customer-namespace",
    }
)
# Words that follow ``-n`` / ``--tenant`` in English prose, not namespace values.
_NAMESPACE_FLAG_STOPWORDS = frozenset(
    {
        "or",
        "and",
        "still",
        "for",
        "with",
        "the",
        "a",
        "an",
        "to",
        "in",
        "on",
        "of",
        "is",
        "as",
        "if",
        "when",
        "from",
        "into",
        "via",
        "per",
        "only",
        "also",
        "not",
        "required",
        "optional",
        "default",
        "unset",
        "flag",
        "flags",
        "value",
        "values",
        "here",
        "below",
        "above",
        "see",
        "use",
        "using",
        "pass",
        "set",
        "must",
        "may",
        "can",
        "should",
        "placeholders",
        "placeholder",
    }
)

# Skip generated / binary-ish paths for security content scans.
_SECURITY_SKIP_PREFIXES = (
    "src/endorlabs/generated/",
    # Mirrored; authoring under agent-knowledge/ is scanned for added lines.
    "src/endorlabs/agent_knowledge/",
)
_SECURITY_SKIP_SUFFIXES = (
    ".lock",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".webp",
    ".ico",
    ".pdf",
    ".zip",
    ".whl",
    ".pyc",
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
    except (OSError, UnicodeDecodeError):
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

        if any(mod == "devtools" or mod.startswith("devtools.") for mod in modules):
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


def _is_security_scan_path(path: str) -> bool:
    """True for checked-in text paths subject to PII / estate guards."""
    normalized = _normalize_path(path)
    if any(normalized.startswith(prefix) for prefix in _SECURITY_SKIP_PREFIXES):
        return False
    lower = normalized.lower()
    if any(lower.endswith(suffix) for suffix in _SECURITY_SKIP_SUFFIXES):
        return False
    return True


def _is_estate_literal_scan_path(path: str) -> bool:
    """Staged text paths where dotted tenant / customer GitHub URLs must fail."""
    if not _is_security_scan_path(path):
        return False
    normalized = _normalize_path(path)
    if normalized == CHANGELOG_PATH:
        # Historical release notes may mention withdrawn versions; still scan
        # for new estate literals on added lines via external-pii-urls.
        return True
    return True


def _looks_like_public_dns(token: str) -> bool:
    """Return True when a dotted token ends in a common public DNS TLD."""
    last = token.rsplit(".", 1)[-1].lower()
    return last in _PUBLIC_DNS_TLDS


def _looks_like_code_or_file_token(token: str) -> bool:
    """Return True when a dotted token is a filename, CI/schema, or code/API path."""
    segments = token.lower().split(".")
    last = segments[-1]
    if last in _FILE_EXT_SEGMENTS or last in _PUBLIC_DNS_TLDS:
        return True
    if any(seg in _CODE_PATH_SEGMENTS for seg in segments):
        return True
    # Real estate namespaces almost always include a hyphenated segment
    # (e.g. example-tenant.example-github-team). Pure dotted ids are code/API.
    return "-" not in token


def _is_disallowed_github_url(line: str) -> bool:
    """Return True when *line* contains a non-allowlisted github.com org/repo URL."""
    for match in _GITHUB_ORG_REPO.finditer(line):
        org = match.group("org").lower()
        if org.startswith("your_"):
            continue
        if org in _GITHUB_ALLOW_ORGS:
            continue
        return True
    return False


def _is_docs_or_agent_path(path: str) -> bool:
    normalized = _normalize_path(path)
    return normalized.startswith(
        ("agent-knowledge/", ".cursor/rules/", "docs/", "AGENTS.md", "CONTRIBUTORS.md")
    )


def check_portable_examples(*, paths: list[str] | None = None) -> int:
    """Fail on high-confidence estate literals in staged checked-in content.

    Scans all staged text paths (not only agent/docs). UUID literals are only
    enforced under docs/agent-knowledge (unit fixtures use opaque 24-hex ids).
    """
    candidates = paths if paths is not None else staged_paths()
    hits: list[str] = []
    for path in candidates:
        if not _is_estate_literal_scan_path(path):
            continue
        # Guard unit tests intentionally embed disallowed literals.
        if path.endswith("test_pre_commit_guards.py"):
            continue
        source = _read_staged_text(path)
        if source is None:
            continue
        scan_uuid = _is_docs_or_agent_path(path)
        for line_no, line in enumerate(source.splitlines(), start=1):
            lower = line.lower()
            if any(marker in lower for marker in _PORTABLE_ALLOW_MARKERS):
                continue
            if _is_disallowed_github_url(line):
                hits.append(f"{path}:{line_no}: github-url")
                continue
            for match in _TENANT_PATH.finditer(line):
                token = match.group(0)
                if _looks_like_public_dns(token) or _looks_like_code_or_file_token(
                    token
                ):
                    continue
                if token.startswith("example-tenant."):
                    continue
                root = token.split(".", 1)[0].lower()
                if root in _TENANT_PATH_SKIP_ROOTS:
                    continue
                hits.append(f"{path}:{line_no}: tenant-path {token}")
            if scan_uuid and _HEX_UUID.search(line):
                hits.append(f"{path}:{line_no}: uuid")
    if not hits:
        return 0
    print(
        "error: possible estate identifiers in staged checked-in content:\n"
        + "\n".join(f"  - {item}" for item in hits[:30])
        + (f"\n  - … and {len(hits) - 30} more" if len(hits) > 30 else "")
        + "\n\nPrefer placeholders (<tenant>, example-tenant.child, "
        "https://github.com/org/repo, user@endor.ai). "
        "See endor-portable-examples.",
        file=sys.stderr,
    )
    return 1


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
        + "\n\nRun: uv run python devtools/codegen/sync_agent_knowledge.py\n"
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


def _email_domain(address: str) -> str:
    return address.rsplit("@", 1)[-1].lower()


def is_allowed_email(address: str) -> bool:
    """Return True when *address* is a placeholder or Endor Labs mailbox."""
    return _email_domain(address) in _EMAIL_ALLOW_DOMAINS


def _url_host_and_path(url: str) -> tuple[str, str]:
    """Best-effort host + path from an http(s) URL (no full URL parse dep)."""
    rest = re.sub(r"^https?://", "", url.strip(), count=1, flags=re.IGNORECASE)
    rest = rest.split("#", 1)[0].split("?", 1)[0]
    host, _, path = rest.partition("/")
    host = host.split("@")[-1].split(":")[0].lower().rstrip(".")
    return host, path


def is_endorlabs_owned_url(url: str) -> bool:
    """Return True when *url* targets an Endor Labs property."""
    host, path = _url_host_and_path(url)
    if any(host == s or host.endswith(f".{s}") for s in _ENDOR_URL_HOST_SUFFIXES):
        return True
    if host in {"github.com", "www.github.com", "raw.githubusercontent.com"}:
        return any(path.startswith(prefix) for prefix in _ENDOR_GITHUB_PREFIXES)
    return False


def is_allowed_url(url: str) -> bool:
    """Return True when *url* is Endor-owned or an explicit placeholder."""
    if is_endorlabs_owned_url(url):
        return True
    host, path = _url_host_and_path(url)
    if host in _PLACEHOLDER_URL_HOSTS:
        return True
    if host in {"github.com", "www.github.com"}:
        return any(path.startswith(prefix) for prefix in _PLACEHOLDER_GITHUB_PREFIXES)
    return False


def is_allowed_namespace_token(token: str) -> bool:
    """Return True when a ``-n`` / ``--namespace`` value is an approved placeholder."""
    if token.startswith("<") and token.endswith(">"):
        return True
    if token.startswith("{") and token.endswith("}"):
        return True  # f-string / format field (runtime value)
    if token.startswith("$"):
        return True  # shell env var
    if token.lower() in _NAMESPACE_FLAG_STOPWORDS:
        return True  # English prose after the flag (not a value)
    if token in _NAMESPACE_FLAG_ALLOW:
        return True
    if token.upper().startswith("YOUR_"):
        return True
    lower = token.lower()
    if lower.startswith("example"):
        return True
    # Angle-style words used as bare placeholders in docs (legacy).
    if lower in {"tenant", "namespace", "namespace_scope", "project-namespace"}:
        return True
    # Short ALLCAPS schema placeholders (``--namespace NS``).
    if token.isupper() and 1 <= len(token) <= 16 and token.isalpha():
        return True
    return False


def iter_namespace_flag_hits(path: str, text: str) -> list[str]:
    """Return ``path:lineno: namespace-flag token`` hits for disallowed values."""
    hits: list[str] = []
    for line_no, line in enumerate(text.splitlines(), start=1):
        for match in _NAMESPACE_FLAG_RE.finditer(line):
            token = match.group(1)
            if not is_allowed_namespace_token(token):
                hits.append(f"{path}:{line_no}: namespace-flag {token}")
    return hits


def find_external_pii_url_hits(
    lines: list[tuple[str, int, str]],
) -> list[str]:
    """Return ``path:lineno: kind match`` hits for disallowed emails/URLs/flags."""
    hits: list[str] = []
    for path, line_no, text in lines:
        if not _is_security_scan_path(path):
            continue
        # Guard unit tests intentionally embed disallowed literals.
        if path.endswith("test_pre_commit_guards.py"):
            continue
        for match in _EMAIL_RE.finditer(text):
            addr = match.group(0)
            if not is_allowed_email(addr):
                hits.append(f"{path}:{line_no}: email {addr}")
        for match in _URL_RE.finditer(text):
            url = match.group(0).rstrip(".,;:")
            if not is_allowed_url(url):
                hits.append(f"{path}:{line_no}: url {url}")
        for match in _NAMESPACE_FLAG_RE.finditer(text):
            token = match.group(1)
            if not is_allowed_namespace_token(token):
                hits.append(f"{path}:{line_no}: namespace-flag {token}")
    return hits


def check_shipped_namespace_flags(*, root: Path | None = None) -> int:
    """Fail when shipped ``src/endorlabs`` content has non-placeholder ``-n`` values.

    Scans the full tree (not only staged diffs). Generated models are skipped.
    Authoring under ``agent-knowledge/`` is covered by staged ``external-pii-urls``.
    """
    base = root or _REPO_ROOT
    shipped = base / "src" / "endorlabs"
    if not shipped.is_dir():
        return 0
    hits: list[str] = []
    for path in sorted(shipped.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(base).as_posix()
        if "/generated/" in rel:
            continue
        lower = rel.lower()
        if any(lower.endswith(suffix) for suffix in _SECURITY_SKIP_SUFFIXES):
            continue
        source = path.read_text(encoding="utf-8", errors="replace")
        hits.extend(iter_namespace_flag_hits(rel, source))
    if not hits:
        return 0
    print(
        "error: shipped src/endorlabs has non-placeholder -n/--namespace/--tenant:\n"
        + "\n".join(f"  - {item}" for item in hits[:40])
        + (f"\n  - … and {len(hits) - 40} more" if len(hits) > 40 else "")
        + "\n\nUse placeholders only (-n example-tenant, -n <tenant>, "
        "-n {tenant}, -n $ENDOR_NAMESPACE). See endor-portable-examples.",
        file=sys.stderr,
    )
    return 1


def _has_git_head() -> bool:
    """Return True when HEAD resolves (false on an unborn/orphan branch)."""
    result = subprocess.run(
        ["git", "rev-parse", "-q", "--verify", "HEAD"],
        check=False,
        capture_output=True,
        cwd=_REPO_ROOT,
    )
    return result.returncode == 0


def check_external_pii_urls(
    *,
    lines: list[tuple[str, int, str]] | None = None,
) -> int:
    """Fail when staged *added* lines introduce emails, non-Endor URLs, or estate flags.

    Allowed emails: ``@example.*`` / ``@endorlabs.com`` / ``@endor.ai``.
    Allowed URLs: ``*.endorlabs.com``, ``*.endor.ai``, ``github.com/endorlabs/…``,
    and placeholder hosts. Namespace CLI tokens must be placeholders
    (``example-tenant``, ``<tenant>``, ``auri``, ``oss``, …). Applies to all
    checked-in paths (skips generated / binary). Added lines only so untouched
    historical third-party links are not re-flagged; editing those lines
    re-checks them.

    On an unborn/orphan branch (no ``HEAD`` yet), skip the added-line email/URL
    scan — every file looks newly added and third-party docs links would false
    fail. Always still runs :func:`check_shipped_namespace_flags`.
    """
    rc = 0
    scan_added = lines is not None or _has_git_head()
    if scan_added:
        candidates = lines if lines is not None else staged_added_lines()
        hits = find_external_pii_url_hits(candidates)
        if hits:
            print(
                "error: staged added lines introduce email, non-Endor URL, "
                "or estate namespace flag:\n"
                + "\n".join(f"  - {item}" for item in hits[:30])
                + (f"\n  - … and {len(hits) - 30} more" if len(hits) > 30 else "")
                + "\n\nUse placeholders (user@endor.ai, user@example.com, "
                "https://example.com, "
                "https://github.com/org/repo, -n example-tenant) or Endor Labs "
                "URLs (*.endorlabs.com, *.endor.ai, github.com/endorlabs/…). "
                "Do not commit customer emails, estate URLs, or customer "
                "``-n`` tenants.",
                file=sys.stderr,
            )
            rc = 1
    return check_shipped_namespace_flags() or rc


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


def check_security_content_diff(base: str, head: str = "HEAD") -> int:
    """CI entry: scan added lines + estate literals on paths touched since *base*."""
    lines = diff_added_lines(base, head)
    rc = check_external_pii_urls(lines=lines)
    paths = sorted({path for path, _, _ in lines})
    if paths:
        rc = check_portable_examples(paths=paths) or rc
    return rc


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    usage = (
        "usage: pre_commit_guards.py "
        "{blocked-paths|changelog-reminder|layer-imports|bounds-shim|"
        "deprecated-api-strings|accessor-nudge|portable-examples|"
        "agent-knowledge-sync|context-root-literals|external-pii-urls|"
        "shipped-namespace-flags|security-content-diff <base> [head]}"
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
    if command == "external-pii-urls":
        return check_external_pii_urls()
    if command == "shipped-namespace-flags":
        return check_shipped_namespace_flags()
    if command == "security-content-diff":
        if len(args) < 2:
            print(usage, file=sys.stderr)
            return 2
        head = args[2] if len(args) > 2 else "HEAD"
        return check_security_content_diff(args[1], head)
    print(f"error: unknown command {command!r}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
