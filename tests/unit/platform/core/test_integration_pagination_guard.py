"""Guardrails enforcing pagination conventions in integration tests.

Generic resource lists use TEST_PAGE_SIZE / TEST_MAX_PAGES. Log-style lists
(AuditLog, FindingLog, AuthenticationLog, …) cap max_pages only via
log_list_kwargs() or TEST_LOG_LIST_MAX_PAGES — omit page_size (tiny page sizes
slow log LIST on the backend). See tests/conftest.py and list-query-performance.md.
"""

from __future__ import annotations

import ast
from pathlib import Path

INTEGRATION_TESTS_ROOT = Path("tests/integration")

_LOG_LIST_KWARGS_HELPER = "log_list_kwargs"
_LOG_LIST_MAX_PAGES_NAME = "TEST_LOG_LIST_MAX_PAGES"


def _is_true_literal(node: ast.AST | None) -> bool:
    return isinstance(node, ast.Constant) and node.value is True


def _is_name(node: ast.AST | None, expected: str) -> bool:
    return isinstance(node, ast.Name) and node.id == expected


def _is_helper_call(node: ast.AST | None, helper_name: str) -> bool:
    if not isinstance(node, ast.Call):
        return False
    func = node.func
    return isinstance(func, ast.Name) and func.id == helper_name


def _uses_log_list_kwargs_spread(call: ast.Call) -> bool:
    """True when .list(**log_list_kwargs()) supplies bounded max_pages."""
    for kw in call.keywords:
        if kw.arg is None and _is_helper_call(kw.value, _LOG_LIST_KWARGS_HELPER):
            return True
    return False


def _is_log_list_bounded_call(call: ast.Call, max_pages: ast.AST | None) -> bool:
    """Log-style bounded list: spread helper and/or TEST_LOG_LIST_MAX_PAGES."""
    if _uses_log_list_kwargs_spread(call):
        return True
    return max_pages is not None and _is_name(max_pages, _LOG_LIST_MAX_PAGES_NAME)


def _keyword(call: ast.Call, name: str) -> ast.AST | None:
    for kw in call.keywords:
        if kw.arg == name:
            return kw.value
    return None


def _list_params_call(node: ast.AST | None) -> ast.Call | None:
    if not isinstance(node, ast.Call):
        return None
    func = node.func
    if isinstance(func, ast.Name) and func.id == "ListParameters":
        return node
    return None


def _iter_list_calls(tree: ast.AST) -> list[ast.Call]:
    calls: list[ast.Call] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Attribute) and func.attr == "list":
                calls.append(node)
    return calls


def _pagination_violations_for_list_call(location: str, call: ast.Call) -> list[str]:
    """Return convention violations for one integration .list() call (may be empty)."""
    violations: list[str] = []
    max_pages = _keyword(call, "max_pages")
    traverse = _keyword(call, "traverse")
    page_size = _keyword(call, "page_size")
    list_params = _list_params_call(_keyword(call, "list_params"))

    if _is_log_list_bounded_call(call, max_pages):
        return violations

    if max_pages is None:
        return [f"{location}: .list(...) missing max_pages"]

    if isinstance(max_pages, ast.Constant) and isinstance(max_pages.value, int):
        violations.append(
            f"{location}: max_pages uses numeric literal ({max_pages.value})"
        )

    if _is_true_literal(traverse):
        if not _is_name(max_pages, "TEST_MAX_PAGES_TRAVERSE"):
            violations.append(
                f"{location}: traverse=True must use TEST_MAX_PAGES_TRAVERSE"
            )
        if _is_name(page_size, "TEST_PAGE_SIZE"):
            violations.append(f"{location}: traverse=True must not use TEST_PAGE_SIZE")

    if list_params is not None:
        lp_traverse = _keyword(list_params, "traverse")
        lp_page_size = _keyword(list_params, "page_size")
        if _is_true_literal(lp_traverse):
            if not _is_name(max_pages, "TEST_MAX_PAGES_TRAVERSE"):
                violations.append(
                    f"{location}: traverse list_params must use TEST_MAX_PAGES_TRAVERSE"
                )
            if _is_name(lp_page_size, "TEST_PAGE_SIZE"):
                violations.append(
                    f"{location}: traverse list_params must use TEST_TRAVERSE_PAGE_SIZE"
                )

    return violations


def test_integration_list_calls_use_bounded_pagination_conventions() -> None:
    """Integration list calls must always be bounded and traverse-aware."""
    violations: list[str] = []

    for py_file in sorted(INTEGRATION_TESTS_ROOT.rglob("*.py")):
        source = py_file.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(py_file))

        for call in _iter_list_calls(tree):
            location = f"{py_file}:{call.lineno}"
            violations.extend(_pagination_violations_for_list_call(location, call))

    assert not violations, "Pagination convention violations:\n" + "\n".join(violations)
