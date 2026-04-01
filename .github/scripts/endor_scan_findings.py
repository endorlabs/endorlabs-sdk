"""Shared helpers to walk Endor scan JSON for findings and file/line locations."""

from __future__ import annotations

import re
from typing import Any


def extract_findings(node: Any) -> list[dict[str, Any]]:
    """Recursively collect finding-like dicts from scan output JSON."""
    findings: list[dict[str, Any]] = []

    def walk(value: Any) -> None:
        if isinstance(value, dict):
            if "uuid" in value and (
                "finding_metadata" in value
                or "security_review_data" in value
                or ("spec" in value and isinstance(value["spec"], dict))
            ):
                findings.append(value)
            for child in value.values():
                walk(child)
        elif isinstance(value, list):
            for item in value:
                walk(item)

    walk(node)
    dedup: dict[str, dict[str, Any]] = {}
    for finding in findings:
        fid = str(finding.get("uuid", ""))
        if fid:
            dedup[fid] = finding
    return list(dedup.values()) if dedup else findings


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
