"""SPDX primary / distribution helpers for PackageLicense and PackageLicenseQuery."""

from __future__ import annotations

from typing import Any, cast

from endorlabs.workflows.wire_access import as_dict

# Registry / declared sources take precedence over code-scan for primary_spdx.
_SOURCE_PRIORITY: tuple[str, ...] = ("package_manager", "declared", "code")

_PACKAGE_LICENSE_BUCKETS: tuple[tuple[str, str], ...] = (
    ("package_manager_licenses", "package_manager"),
    ("declared_code_licenses", "declared"),
    ("code_licenses", "code"),
)


def _norm_spdx(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def spdx_from_license_entry(entry: Any) -> str | None:
    """Prefer ``spdx_id``, then ``spdx_expr``, from a PackageLicense bucket entry."""
    data: dict[str, Any] = (
        as_dict(entry) if not isinstance(entry, dict) else cast("dict[str, Any]", entry)
    )
    return _norm_spdx(data.get("spdx_id")) or _norm_spdx(data.get("spdx_expr"))


def collect_bucket_spdx(
    package_license: dict[str, Any],
) -> dict[str, list[str]]:
    """Map source name → ordered distinct SPDX ids from PackageLicense.spec buckets."""
    spec = as_dict(package_license.get("spec"))
    out: dict[str, list[str]] = {
        "package_manager": [],
        "declared": [],
        "code": [],
    }
    for field_name, source in _PACKAGE_LICENSE_BUCKETS:
        seen: set[str] = set()
        raw_obj: Any = spec.get(field_name)
        raw: list[Any] = cast("list[Any]", raw_obj) if isinstance(raw_obj, list) else []
        for item in raw:
            spdx = spdx_from_license_entry(item)
            if spdx and spdx not in seen:
                seen.add(spdx)
                out[source].append(spdx)
    return out


def single_spdx_consensus(
    package_license: dict[str, Any],
) -> str | None:
    """Return the sole distinct SPDX when all non-empty sources agree (fast path).

    When every populated package_manager / declared / code bucket contributes
    SPDX ids that collapse to exactly one distinct value, PackageLicenseQuery
    is known to resolve the same primary for that PV. Multi-license disagreement
    must use PackageLicenseQuery instead.
    """
    buckets = collect_bucket_spdx(package_license)
    distinct: set[str] = set()
    any_source = False
    for source in _SOURCE_PRIORITY:
        ids = buckets.get(source) or []
        if not ids:
            continue
        any_source = True
        distinct.update(ids)
    if not any_source or len(distinct) != 1:
        return None
    return next(iter(distinct))


def license_resolution_from_package_license(
    package_license: dict[str, Any],
) -> dict[str, Any] | None:
    """Build a cache row when PackageLicense has single-SPDX consensus; else None."""
    primary = single_spdx_consensus(package_license)
    if primary is None:
        return None
    buckets = collect_bucket_spdx(package_license)
    all_ids: list[str] = []
    seen: set[str] = set()
    for source in _SOURCE_PRIORITY:
        for spdx in buckets.get(source) or []:
            if spdx not in seen:
                seen.add(spdx)
                all_ids.append(spdx)
    return {
        "primary_spdx": primary,
        "all_spdx": ";".join(all_ids),
        "source_count": sum(1 for s in _SOURCE_PRIORITY if buckets.get(s)),
        "has_declared": bool(buckets.get("declared")),
        "has_code": bool(buckets.get("code")),
        "has_package_manager": bool(buckets.get("package_manager")),
        "resolution": "package_license_consensus",
    }


def primary_spdx_from_query_licenses(
    licenses: list[Any],
) -> tuple[str, list[str], dict[str, bool]]:
    """Resolve primary + all SPDX from PackageLicenseQuery merged license entries.

    Among selected entries, prefer ``package_manager``, then ``declared``, then
    ``code`` (registry-declared over code-scan).
    """
    selected: list[dict[str, Any]] = []
    for item in licenses:
        data: dict[str, Any] = (
            as_dict(item)
            if not isinstance(item, dict)
            else cast("dict[str, Any]", item)
        )
        if data.get("selected") is False:
            continue
        selected.append(data)

    by_source: dict[str, list[str]] = {
        "package_manager": [],
        "declared": [],
        "code": [],
    }
    all_ids: list[str] = []
    seen: set[str] = set()
    for entry in selected:
        source = str(entry.get("source") or "").strip().lower()
        spdx = _norm_spdx(entry.get("spdx_expr")) or _norm_spdx(entry.get("spdx_id"))
        if not spdx:
            continue
        if spdx not in seen:
            seen.add(spdx)
            all_ids.append(spdx)
        if source in by_source and spdx not in by_source[source]:
            by_source[source].append(spdx)

    primary = ""
    for source in _SOURCE_PRIORITY:
        if by_source[source]:
            primary = by_source[source][0]
            break
    if not primary and all_ids:
        primary = all_ids[0]

    flags = {
        "has_declared": bool(by_source["declared"]),
        "has_code": bool(by_source["code"]),
        "has_package_manager": bool(by_source["package_manager"]),
    }
    return primary, all_ids, flags


def license_resolution_from_query(
    query_body: dict[str, Any],
) -> dict[str, Any]:
    """Build a cache row from a PackageLicenseQuery response body."""
    spec = as_dict(query_body.get("spec"))
    raw_obj: Any = spec.get("licenses")
    raw_licenses: list[Any] = (
        cast("list[Any]", raw_obj) if isinstance(raw_obj, list) else []
    )
    primary, all_ids, flags = primary_spdx_from_query_licenses(raw_licenses)
    return {
        "primary_spdx": primary,
        "all_spdx": ";".join(all_ids),
        "source_count": sum(
            1
            for key in ("has_package_manager", "has_declared", "has_code")
            if flags.get(key)
        ),
        "has_declared": flags["has_declared"],
        "has_code": flags["has_code"],
        "has_package_manager": flags["has_package_manager"],
        "resolution": "package_license_query",
    }


def empty_license_resolution() -> dict[str, Any]:
    """Empty license cache fields when Query/PackageLicense yield nothing."""
    return {
        "primary_spdx": "",
        "all_spdx": "",
        "source_count": 0,
        "has_declared": False,
        "has_code": False,
        "has_package_manager": False,
        "resolution": "none",
    }
