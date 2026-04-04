"""Helpers for finding dicts from the Endor API (file/line for GitHub REST)."""

from __future__ import annotations

import re
from collections.abc import Iterator
from typing import Any
from urllib.parse import unquote

# github.com/org/repo/blob/<sha>/path?...#L123 (plain=1 optional)
_GITHUB_BLOB_LINE_RE = re.compile(
    r"github\.com/[^/]+/[^/]+/blob/[a-fA-F0-9]+/([^?#\s]+)(?:\?[^#]*)?#L(\d+)",
    re.IGNORECASE,
)


def is_valid_annotation_path(path: str) -> bool:
    """Reject empty, ``.``, ``..``, and slash-only paths for GitHub annotations."""
    p = path.strip().replace("\\", "/")
    if not p or p in (".", ".."):
        return False
    return not (p == "/" or all(part in ("", ".") for part in p.split("/")))


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


def _github_blob_hits_in_text(text: str) -> list[tuple[str, int]]:
    """Path and 1-based line for each ``blob/.../path...#Ln`` in ``text``."""
    out: list[tuple[str, int]] = []
    for m in _GITHUB_BLOB_LINE_RE.finditer(text):
        up = unquote(m.group(1)).replace("\\", "/").lstrip("./")
        ul = int(m.group(2))
        out.append((up, ul))
    return out


def _iter_metadata_strings_with_blob(obj: Any, depth: int = 0) -> Iterator[str]:
    """Yield string values that may contain GitHub blob URLs (nested metadata)."""
    if depth > 14:
        return
    if isinstance(obj, str) and "github.com" in obj and "/blob/" in obj:
        yield obj
    elif isinstance(obj, dict):
        for v in obj.values():
            yield from _iter_metadata_strings_with_blob(v, depth + 1)
    elif isinstance(obj, list):
        for item in obj:
            yield from _iter_metadata_strings_with_blob(item, depth + 1)


def _choose_blob_path_line(
    hits: list[tuple[str, int]],
    norm_fp: str | None,
) -> tuple[str | None, int | None]:
    """Pick a single anchor; for the same file, prefer the highest line (secret row).

    Policy findings may embed multiple ``#L`` references (e.g. docstring vs match).
    The canonical ``Secret Location`` URL is usually the deepest line in the file.
    """
    if not hits:
        return None, None
    if not norm_fp:
        return hits[0][0], hits[0][1]
    want_base = norm_fp.split("/")[-1]
    matching = [
        (up, ul)
        for up, ul in hits
        if up.rstrip("/") == norm_fp.rstrip("/")
        or up.endswith("/" + norm_fp)
        or up.split("/")[-1] == want_base
    ]
    if not matching:
        return None, None
    best_up, best_ln = max(matching, key=lambda t: t[1])
    return best_up, best_ln


def _merge_github_blob_url_location(
    spec: dict[str, Any],
    file_path: str | None,
    line: Any,
    metadata: dict[str, Any] | None = None,
) -> tuple[str | None, Any]:
    """Prefer path+line from ``blob/...#L`` links in spec text and nested metadata."""
    norm_fp: str | None = None
    if isinstance(file_path, str) and file_path.strip():
        norm_fp = normalize_pr_path(file_path).replace("\\", "/").lstrip("./")

    hits: list[tuple[str, int]] = []
    for key in ("summary", "explanation", "remediation", "description"):
        text = spec.get(key)
        if isinstance(text, str):
            hits.extend(_github_blob_hits_in_text(text))
    if isinstance(metadata, dict):
        for blob_text in _iter_metadata_strings_with_blob(metadata):
            hits.extend(_github_blob_hits_in_text(blob_text))

    picked_p, picked_ln = _choose_blob_path_line(hits, norm_fp)
    if picked_ln is not None and picked_p:
        return picked_p, picked_ln
    return file_path, line


def _line_after_path_in_text(text: str, path: str) -> int | None:
    """If ``text`` contains ``path``, read a line after it (``#L`` / ``:`` forms).

    GitHub blob URLs use ``?plain=1#L219``; naive digit parsing would treat
    ``plain=1`` as line ``1`` instead of ``219``.
    """
    if not text or not path:
        return None
    i = text.find(path)
    if i < 0:
        return None
    tail = text[i + len(path) : i + len(path) + 512]
    m = re.search(r"#L(\d+)\b", tail, re.IGNORECASE)
    if m:
        return _coerce_positive_int(m.group(1))
    m = re.search(r"#(\d+)\b", tail)
    if m:
        return _coerce_positive_int(m.group(1))
    m = re.match(r"^\s*:\s*(\d+)", tail)
    if m:
        return _coerce_positive_int(m.group(1))
    m = re.match(r"[^0-9#:L]*[#:L](\d+)", tail)
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

    prev_line = line
    file_path, line = _merge_github_blob_url_location(spec, file_path, line, metadata)
    pl = _coerce_positive_int(prev_line)
    nl = _coerce_positive_int(line)
    if nl is not None and (
        (pl is not None and nl != pl) or (pl is None and line_end is not None)
    ):
        line_end = None

    if not isinstance(file_path, str) or not is_valid_annotation_path(file_path):
        return {"file": None, "line": None, "line_end": None}
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
