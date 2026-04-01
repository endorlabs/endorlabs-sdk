"""Helpers for finding dicts from the Endor API (file/line for GitHub REST)."""

from __future__ import annotations

import re
from typing import Any


def extract_location(finding: dict[str, Any]) -> dict[str, Any]:
    """Return file path, line, and optional line_end from finding metadata."""
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
        code_snippet.get("file") or metadata.get("file") or metadata.get("file_path")
    )
    line = code_snippet.get("line") or metadata.get("line")
    line_end = code_snippet.get("line_end")

    if (not file_path or not line) and isinstance(metadata.get("location"), str):
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
