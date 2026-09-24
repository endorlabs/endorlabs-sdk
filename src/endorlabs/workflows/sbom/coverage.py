"""SBOM file vs Endor project PackageVersion coverage."""

from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from endorlabs.workflows.common import WorkflowResult

# PackageURL types Endor typically maps to OSS ecosystems (not exhaustive).
KNOWN_PURL_TYPES: frozenset[str] = frozenset(
    {
        "npm",
        "gem",
        "maven",
        "pypi",
        "golang",
        "go",
        "cargo",
        "nuget",
        "swift",
        "generic",
        "github",
        "deb",
        "rpm",
        "apk",
        "hex",
        "composer",
        "oci",
        "bitnami",
        "conda",
        "pub",
        "hackage",
        "cran",
    }
)

# Reserved CycloneDX property namespace — unofficial ``cdx:…`` names must not be used.
RESERVED_CDX_PROPERTY_PREFIX = "cdx:"


@dataclass
class FileComponentStats:
    """Parsed component/package counts from a CycloneDX or SPDX document."""

    total: int = 0
    with_purl: int = 0
    odd_purl_types: dict[str, int] = field(default_factory=dict)
    reserved_cdx_properties: list[str] = field(default_factory=list)
    format_kind: str = "unknown"


@dataclass
class CoverageResult(WorkflowResult):
    """Coverage of SBOM file components vs Endor PackageVersion inventory."""

    sbom_path: str = ""
    project_uuid: str = ""
    namespace: str = ""
    file_components: int = 0
    file_with_purl: int = 0
    file_odd_purl_types: dict[str, int] = field(default_factory=dict)
    reserved_cdx_properties: list[str] = field(default_factory=list)
    endor_package_versions: int = 0
    endor_eco_buckets: dict[str, int] = field(default_factory=dict)
    coverage_ratio: float = 0.0
    format_kind: str = "unknown"

    def to_dict(self) -> dict[str, Any]:
        """Serialize for CLI artifacts."""
        return {
            "status": self.status,
            "message": self.message,
            "errors": list(self.errors),
            "sbom_path": self.sbom_path,
            "project_uuid": self.project_uuid,
            "namespace": self.namespace,
            "format_kind": self.format_kind,
            "file_components": self.file_components,
            "file_with_purl": self.file_with_purl,
            "file_odd_purl_types": dict(self.file_odd_purl_types),
            "reserved_cdx_properties": list(self.reserved_cdx_properties),
            "endor_package_versions": self.endor_package_versions,
            "endor_eco_buckets": dict(self.endor_eco_buckets),
            "coverage_ratio": self.coverage_ratio,
        }


def eco_bucket(name: str) -> str:
    """Return Endor ecosystem prefix (``npm``, ``pypi``, ``sbom``, …) from a PV name."""
    if "://" in name:
        return name.split("://", 1)[0]
    return "other"


def classify_purl_type(purl: str) -> str | None:
    """Return the PackageURL type segment, or None when not a ``pkg:`` locator."""
    if not isinstance(purl, str) or not purl.startswith("pkg:"):
        return None
    rest = purl[4:]
    typ = rest.split("/", 1)[0].split("@", 1)[0].strip().lower()
    return typ or None


def is_odd_purl_type(purl_type: str) -> bool:
    """True when the type is not in the known OSS set (often becomes ``sbom://``)."""
    return purl_type not in KNOWN_PURL_TYPES


def scan_reserved_cdx_properties(props: list[Any] | None) -> list[str]:
    """Return unofficial ``cdx:`` property names found on a component."""
    found: list[str] = []
    for prop in props or []:
        if not isinstance(prop, dict):
            continue
        name = prop.get("name")
        if isinstance(name, str) and name.startswith(RESERVED_CDX_PROPERTY_PREFIX):
            found.append(name)
    return found


def _odd_counts(purls: list[str]) -> Counter[str]:
    odd: Counter[str] = Counter()
    for u in purls:
        typ = classify_purl_type(u)
        if typ is not None and is_odd_purl_type(typ):
            odd[typ] += 1
    return odd


def _parse_cyclonedx_xml(text: str) -> FileComponentStats:
    # Local SBOM files from generators; not untrusted network XML.
    root = ET.fromstring(text)  # noqa: S314
    comps = [e for e in root.iter() if e.tag.endswith("component")]
    purls: list[str] = []
    reserved: list[str] = []
    for c in comps:
        for child in c:
            if child.tag.endswith("purl") and child.text:
                purls.append(child.text.strip())
            if child.tag.endswith("property"):
                pname = child.attrib.get("name") or ""
                if pname.startswith(RESERVED_CDX_PROPERTY_PREFIX):
                    reserved.append(pname)
    return FileComponentStats(
        total=len(comps),
        with_purl=sum(1 for u in purls if u.startswith("pkg:")),
        odd_purl_types=dict(_odd_counts(purls)),
        reserved_cdx_properties=sorted(set(reserved)),
        format_kind="cyclonedx-xml",
    )


def _parse_spdx_json(data: dict[str, Any]) -> FileComponentStats:
    pkgs = data.get("packages") or []
    purls: list[str] = []
    for pkg in pkgs:
        if not isinstance(pkg, dict):
            continue
        refs = [
            str(ref["referenceLocator"])
            for ref in (pkg.get("externalRefs") or [])
            if (
                isinstance(ref, dict)
                and ref.get("referenceType") == "purl"
                and ref.get("referenceLocator")
            )
        ]
        purls.extend(refs)
    return FileComponentStats(
        total=len(pkgs),
        with_purl=sum(1 for u in purls if u.startswith("pkg:")),
        odd_purl_types=dict(_odd_counts(purls)),
        reserved_cdx_properties=[],
        format_kind="spdx-json",
    )


def _parse_cyclonedx_json(data: dict[str, Any]) -> FileComponentStats:
    comps_list = list(data.get("components") or [])
    meta = (data.get("metadata") or {}).get("component")
    if isinstance(meta, dict) and (meta.get("purl") or meta.get("name")):
        comps_list = [meta, *comps_list]
    purls: list[str] = []
    reserved: list[str] = []
    for c in comps_list:
        if not isinstance(c, dict):
            continue
        purl = c.get("purl")
        if isinstance(purl, str) and purl:
            purls.append(purl)
        reserved.extend(scan_reserved_cdx_properties(c.get("properties")))
    return FileComponentStats(
        total=len(comps_list),
        with_purl=sum(1 for u in purls if u.startswith("pkg:")),
        odd_purl_types=dict(_odd_counts(purls)),
        reserved_cdx_properties=sorted(set(reserved)),
        format_kind="cyclonedx-json",
    )


def parse_sbom_file(path: Path) -> FileComponentStats:
    """Parse CycloneDX JSON/XML or SPDX JSON and return component/purl stats."""
    text = path.read_text(encoding="utf-8", errors="replace")
    if path.suffix.lower() == ".xml":
        return _parse_cyclonedx_xml(text)
    data = json.loads(text)
    if "spdxVersion" in data or data.get("SPDXID"):
        return _parse_spdx_json(data)
    return _parse_cyclonedx_json(data)


def _unwrap(value: Any) -> Any:
    return getattr(value, "value", value)


def _pv_name(pv: Any) -> str | None:
    if isinstance(pv, dict):
        meta = pv.get("meta") or {}
        name = meta.get("name") if isinstance(meta, dict) else None
        return str(name) if name else None
    meta = getattr(pv, "meta", None)
    name = getattr(meta, "name", None) if meta is not None else None
    name = _unwrap(name)
    return str(name) if name else None


def run_coverage(
    client: Any,
    *,
    sbom_path: Path,
    project_uuid: str,
) -> CoverageResult:
    """Compare SBOM file components to PackageVersions on the linked project.

    Endor inventory is counted as unique ``PackageVersion.meta.name`` rows from
    ``list_by_project`` (sibling PVs created by SBOM ingest). Resolved-dependency
    nested lists on the root PV are often empty and are not used.
    """
    path = Path(sbom_path)
    if not path.is_file():
        return CoverageResult(
            status="error",
            message=f"SBOM file not found: {path}",
            errors=[f"missing file: {path}"],
            sbom_path=str(path),
            project_uuid=project_uuid,
        )

    try:
        stats = parse_sbom_file(path)
    except (OSError, json.JSONDecodeError, ET.ParseError, ValueError) as exc:
        return CoverageResult(
            status="error",
            message=f"Failed to parse SBOM: {exc}",
            errors=[str(exc)],
            sbom_path=str(path),
            project_uuid=project_uuid,
        )

    project = client.Project.get(project_uuid)
    ns = _unwrap(getattr(getattr(project, "tenant_meta", None), "namespace", None))
    namespace = str(ns) if ns else ""
    pvs = client.PackageVersion.list_by_project(project)
    names = {n for pv in pvs if (n := _pv_name(pv))}
    buckets = Counter(eco_bucket(n) for n in names)
    ratio = (len(names) / stats.total) if stats.total else 0.0

    warns: list[str] = []
    if stats.odd_purl_types:
        warns.append(f"odd purl types: {dict(stats.odd_purl_types)}")
    if stats.reserved_cdx_properties:
        warns.append(f"reserved cdx: properties: {stats.reserved_cdx_properties}")

    status = "success"
    if stats.odd_purl_types or stats.reserved_cdx_properties:
        status = "partial"
    message = (
        f"{len(names)}/{stats.total} PackageVersions vs file components "
        f"(ratio={ratio:.2f})"
    )
    if warns:
        message = f"{message}; " + "; ".join(warns)

    return CoverageResult(
        status=status,
        message=message,
        errors=[],
        sbom_path=str(path),
        project_uuid=project_uuid,
        namespace=namespace,
        file_components=stats.total,
        file_with_purl=stats.with_purl,
        file_odd_purl_types=dict(stats.odd_purl_types),
        reserved_cdx_properties=list(stats.reserved_cdx_properties),
        endor_package_versions=len(names),
        endor_eco_buckets=dict(buckets),
        coverage_ratio=ratio,
        format_kind=stats.format_kind,
    )
