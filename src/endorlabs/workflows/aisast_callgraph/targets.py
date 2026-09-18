"""Derive Call Graph ``path-to`` patterns from vulnerability Findings.

CVE/GHSA ids are **Finding filters only** — never used as Call Graph URI
substrings. CG walks target the vulnerable **package token** (and optional
symbol), then callers correlate back to the Finding row separately.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, cast

from endorlabs.filters.finding_categories import VULNERABILITY_CATEGORY
from endorlabs.filters.main_context import main_context_filter

# Reject GHSA/CVE-shaped strings as CG URI patterns (Finding plane only).
_VULN_ID_SHAPE = re.compile(
    r"^(?:GHSA-[a-z0-9]{4}-[a-z0-9]{4}-[a-z0-9]{4}|"
    r"CVE-\d{4}-\d{4,}|"
    r"ENDOR-[A-Z0-9-]+)$",
    re.IGNORECASE,
)

_DEFAULT_MAX_FINDINGS = 40


def _empty_str_list() -> list[str]:
    return []


def is_vuln_id_shaped(token: str) -> bool:
    """Return True when *token* looks like a GHSA/CVE/ENDOR advisory id."""
    return bool(_VULN_ID_SHAPE.match((token or "").strip()))


def package_token_from_coordinate(coordinate: str | None) -> str | None:
    """Extract a CG-friendly package token from a Finding coordinate.

    Examples::

        npm://jsonwebtoken@0.4.0 → jsonwebtoken
        maven://org.apache:log4j-core@2.14.1 → log4j-core
        pypi://requests@2.28.0 → requests
    """
    raw = (coordinate or "").strip()
    if not raw:
        return None
    s = raw
    if "://" in s:
        s = s.split("://", 1)[1]
    if "@" in s:
        s = s.rsplit("@", 1)[0]
    if ":" in s:
        # Maven group:artifact (keep artifact)
        s = s.rsplit(":", 1)[-1]
    if "/" in s:
        s = s.rstrip("/").rsplit("/", 1)[-1]
    s = s.strip()
    if not s or is_vuln_id_shaped(s):
        return None
    return s


def path_patterns_for_package(
    package_token: str,
    *,
    symbol: str | None = None,
) -> list[str]:
    """Build AND-ed ``path-to`` patterns; never includes advisory ids."""
    token = (package_token or "").strip()
    if not token or is_vuln_id_shaped(token):
        return []
    patterns = [token]
    sym = (symbol or "").strip()
    if sym and not is_vuln_id_shaped(sym) and sym.lower() != token.lower():
        patterns.append(sym)
    return patterns


@dataclass
class VulnWalkTarget:
    """One Finding-derived CG walk target (package plane, not advisory URI)."""

    finding_uuid: str | None = None
    extra_key: str | None = None
    vuln_name: str | None = None
    package_coordinate: str | None = None
    package_token: str | None = None
    path_to_patterns: list[str] = field(default_factory=_empty_str_list)
    finding_tags: list[str] = field(default_factory=_empty_str_list)
    level: str | None = None

    def as_dict(self) -> dict[str, Any]:
        """JSON-serializable target row for bridge artifacts."""
        return {
            "finding_uuid": self.finding_uuid,
            "extra_key": self.extra_key,
            "vuln_name": self.vuln_name,
            "package_coordinate": self.package_coordinate,
            "package_token": self.package_token,
            "path_to_patterns": list(self.path_to_patterns),
            "finding_tags": list(self.finding_tags),
            "level": self.level,
            # Explicit: CG walk must not be read as Finding reachability.
            "cg_path_is_not_finding_reachability": True,
        }


def _finding_fields(finding: Any) -> dict[str, Any]:
    if isinstance(finding, dict):
        finding_d = cast("dict[str, Any]", finding)
        meta_raw = finding_d.get("meta")
        spec_raw = finding_d.get("spec")
        meta: dict[str, Any] = (
            cast("dict[str, Any]", meta_raw) if isinstance(meta_raw, dict) else {}
        )
        spec: dict[str, Any] = (
            cast("dict[str, Any]", spec_raw) if isinstance(spec_raw, dict) else {}
        )
        tags_raw = spec.get("finding_tags")
        tags: list[str] = (
            [str(t) for t in cast("list[Any]", tags_raw)]
            if isinstance(tags_raw, list)
            else []
        )
        return {
            "uuid": finding_d.get("uuid") or meta.get("uuid"),
            "name": meta.get("name"),
            "extra_key": spec.get("extra_key"),
            "package": spec.get("target_dependency_package_name"),
            "tags": tags,
            "level": spec.get("level"),
        }
    meta_obj = getattr(finding, "meta", None)
    spec_obj = getattr(finding, "spec", None)
    tags_attr = (
        getattr(spec_obj, "finding_tags", None) if spec_obj is not None else None
    )
    tags_out: list[str] = (
        [str(t) for t in cast("list[Any]", tags_attr)]
        if isinstance(tags_attr, list)
        else []
    )
    return {
        "uuid": getattr(finding, "uuid", None),
        "name": getattr(meta_obj, "name", None) if meta_obj is not None else None,
        "extra_key": (
            getattr(spec_obj, "extra_key", None) if spec_obj is not None else None
        ),
        "package": (
            getattr(spec_obj, "target_dependency_package_name", None)
            if spec_obj is not None
            else None
        ),
        "tags": tags_out,
        "level": getattr(spec_obj, "level", None) if spec_obj is not None else None,
    }


def _matches_vuln_filter(fields: dict[str, Any], vuln_id: str) -> bool:
    needle = vuln_id.strip().lower()
    if not needle:
        return True
    for key in ("extra_key", "name"):
        val = fields.get(key)
        if val is not None and needle in str(val).lower():
            return True
    pkg = fields.get("package")
    return pkg is not None and needle in str(pkg).lower()


def resolve_vuln_walk_targets(
    client: Any,
    project: Any,
    *,
    namespace: str,
    vuln_id: str | None = None,
    package_substring: str | None = None,
    symbol: str | None = None,
    max_findings: int = _DEFAULT_MAX_FINDINGS,
    max_pages: int = 1,
) -> list[VulnWalkTarget]:
    """List MAIN vulnerability Findings and map them to CG ``path-to`` patterns.

    *vuln_id* filters Finding ``extra_key`` / ``meta.name`` / package (e.g.
    ``GHSA-…``). It is **not** appended to CG patterns.
    """
    filt = main_context_filter(VULNERABILITY_CATEGORY)

    findings = client.Finding.list_by_project(
        project,
        namespace=namespace,
        filter=filt,
        max_pages=max(1, max_pages),
    )
    vuln_filter = (vuln_id or "").strip() or None
    pkg_filter = (package_substring or "").strip().lower() or None

    targets: list[VulnWalkTarget] = []
    seen_tokens: set[str] = set()
    for finding in findings:
        fields = _finding_fields(finding)
        if vuln_filter and not _matches_vuln_filter(fields, vuln_filter):
            continue
        coord = fields.get("package")
        if pkg_filter and (coord is None or pkg_filter not in str(coord).lower()):
            continue
        token = package_token_from_coordinate(str(coord) if coord is not None else None)
        if not token:
            continue
        patterns = path_patterns_for_package(token, symbol=symbol)
        if not patterns:
            continue
        # Deduplicate by package token (+ symbol patterns)
        dedupe_key = "|".join(patterns)
        if dedupe_key in seen_tokens:
            continue
        seen_tokens.add(dedupe_key)
        targets.append(
            VulnWalkTarget(
                finding_uuid=str(fields["uuid"]) if fields.get("uuid") else None,
                extra_key=str(fields["extra_key"])
                if fields.get("extra_key") is not None
                else None,
                vuln_name=str(fields["name"]) if fields.get("name") else None,
                package_coordinate=str(coord) if coord is not None else None,
                package_token=token,
                path_to_patterns=patterns,
                finding_tags=(
                    [str(t) for t in cast("list[Any]", fields["tags"])]
                    if isinstance(fields.get("tags"), list)
                    else []
                ),
                level=str(fields["level"]) if fields.get("level") is not None else None,
            )
        )
        if len(targets) >= max(1, max_findings):
            break
    return targets
