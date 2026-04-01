"""Helpers for finding dicts from the Endor API (file/line for GitHub REST)."""

from __future__ import annotations

import re
from typing import Any


def _coerce_positive_int(value: Any) -> int | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        n = int(value)
    except (TypeError, ValueError):
        return None
    return n if n > 0 else None


def _location_from_custom(
    custom: Any, *, depth: int = 0
) -> tuple[str | None, int | None, int | None]:
    """Best-effort path/lines from finding_metadata.custom (Semgrep/OpenGrep)."""
    if depth > 14 or not isinstance(custom, dict):
        return None, None, None

    path = custom.get("path") or custom.get("file") or custom.get("filepath")
    if isinstance(path, str) and path.strip():
        start = custom.get("start")
        line: int | None = None
        if isinstance(start, dict):
            line = _coerce_positive_int(start.get("line"))
        if line is None:
            line = _coerce_positive_int(
                custom.get("line") or custom.get("line_number") or custom.get("lineno")
            )
        end_ln: int | None = None
        end = custom.get("end")
        if isinstance(end, dict):
            end_ln = _coerce_positive_int(end.get("line"))
        if line is not None:
            return path.strip(), line, end_ln

    for key in ("results", "matches", "data", "findings"):
        arr = custom.get(key)
        if isinstance(arr, list) and arr:
            first = arr[0]
            if isinstance(first, dict):
                p, ln, el = _location_from_custom(first, depth=depth + 1)
                if p and ln is not None:
                    return p, ln, el

    for val in custom.values():
        p, ln, el = _location_from_custom(val, depth=depth + 1)
        if p and ln is not None:
            return p, ln, el

    return None, None, None


def _line_after_path_in_text(text: str, path: str) -> int | None:
    """If ``text`` contains ``path``, try to read a line number immediately after it."""
    if not text or not path:
        return None
    i = text.find(path)
    if i < 0:
        return None
    tail = text[i + len(path) : i + len(path) + 48]
    m = re.match(r"[^0-9#:L]*[#:L]?(\d+)", tail)
    if m:
        return _coerce_positive_int(m.group(1))
    return None


def extract_location(finding: dict[str, Any]) -> dict[str, Any]:
    """Return file path, line, and optional line_end from finding metadata and spec."""
    spec = finding.get("spec", {}) if isinstance(finding.get("spec"), dict) else {}
    metadata = spec.get("finding_metadata", {})
    if not isinstance(metadata, dict):
        metadata = {}
    sec_review = metadata.get("security_review_data", {})
    if not isinstance(sec_review, dict):
        sec_review = {}
    code_snippet = sec_review.get("code_snippet", {})
    if not isinstance(code_snippet, dict):
        code_snippet = {}

    file_path = (
        code_snippet.get("file")
        or code_snippet.get("path")
        or code_snippet.get("filepath")
        or metadata.get("file_path")
        or metadata.get("file")
        or metadata.get("filepath")
    )
    line: Any = (
        code_snippet.get("line")
        or code_snippet.get("line_number")
        or code_snippet.get("lineno")
        or metadata.get("line_number")
        or metadata.get("line")
    )
    line_end = code_snippet.get("line_end")
    if isinstance(line_end, dict) and "line" in line_end:
        line_end = line_end.get("line")

    if (not file_path or line is None) and isinstance(metadata.get("custom"), dict):
        cp, cln, cend = _location_from_custom(metadata["custom"])
        if cp:
            file_path = file_path or cp
        if cln is not None:
            line = cln
        if cend is not None:
            line_end = line_end or cend

    if not file_path or line is None:
        deps = spec.get("dependency_file_paths")
        if isinstance(deps, list) and deps:
            p0 = deps[0] if isinstance(deps[0], str) else None
            if p0:
                file_path = file_path or p0
                if line is None and isinstance(metadata.get("custom"), dict):
                    _cp, cln, _ce = _location_from_custom(metadata["custom"])
                    if cln is not None:
                        line = cln
                if line is None:
                    summary = spec.get("summary")
                    if isinstance(summary, str):
                        ln2 = _line_after_path_in_text(summary, p0)
                        if ln2 is not None:
                            line = ln2

    if (not file_path or line is None) and isinstance(metadata.get("location"), str):
        m = re.match(r"^(?P<file>.+?):(?P<line>\d+)$", metadata["location"])
        if m:
            file_path = file_path or m.group("file")
            line = line or int(m.group("line"))

    return {"file": file_path, "line": line, "line_end": line_end}


def normalize_pr_path(path: str) -> str:
    """Strip diff prefixes a/ b/ from paths."""
    if path.startswith(("a/", "b/")):
        return path[2:]
    return path


def summarize_location_coverage(findings: list[dict[str, Any]]) -> dict[str, int]:
    """Count how many findings expose file+line for GitHub (tests / validation CLI)."""
    located = 0
    for f in findings:
        loc = extract_location(f)
        if loc.get("file") and loc.get("line") is not None:
            located += 1
    return {
        "total": len(findings),
        "with_file_and_line": located,
        "without_location": len(findings) - located,
    }
