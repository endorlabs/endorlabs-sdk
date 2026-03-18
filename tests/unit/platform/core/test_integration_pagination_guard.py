"""Guardrails enforcing pagination conventions in integration tests."""

from __future__ import annotations

import ast
from pathlib import Path

INTEGRATION_TESTS_ROOT = Path("tests/integration")


def _is_true_literal(node: ast.AST | None) -> bool:
    return isinstance(node, ast.Constant) and node.value is True


def _is_name(node: ast.AST | None, expected: str) -> bool:
    return isinstance(node, ast.Name) and node.id == expected


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


def test_integration_list_calls_use_bounded_pagination_conventions() -> None:
    """Integration list calls must always be bounded and traverse-aware."""
    violations: list[str] = []

    for py_file in sorted(INTEGRATION_TESTS_ROOT.rglob("*.py")):
        source = py_file.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(py_file))

        for call in _iter_list_calls(tree):
            max_pages = _keyword(call, "max_pages")
            traverse = _keyword(call, "traverse")
            page_size = _keyword(call, "page_size")
            list_params = _list_params_call(_keyword(call, "list_params"))

            location = f"{py_file}:{call.lineno}"

            if max_pages is None:
                violations.append(f"{location}: .list(...) missing max_pages")
                continue

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
                    violations.append(
                        f"{location}: traverse=True must not use TEST_PAGE_SIZE"
                    )

            if list_params is not None:
                lp_traverse = _keyword(list_params, "traverse")
                lp_page_size = _keyword(list_params, "page_size")
                if _is_true_literal(lp_traverse):
                    if not _is_name(max_pages, "TEST_MAX_PAGES_TRAVERSE"):
                        violations.append(
                            f"{location}: traverse list_params must use "
                            "TEST_MAX_PAGES_TRAVERSE"
                        )
                    if _is_name(lp_page_size, "TEST_PAGE_SIZE"):
                        violations.append(
                            f"{location}: traverse list_params must use "
                            "TEST_TRAVERSE_PAGE_SIZE"
                        )

    assert not violations, "Pagination convention violations:\n" + "\n".join(violations)
