"""Scan-bound dependency artifact receipt (SDK-001).

Platform does not yet expose a supported read path that attests dependency
bytes used by a *specific scan*. Related kinds (``Artifact`` checksums,
``PackageVersionSourceMetadata`` ecosystem artifact hashes) are package-level
integrity metadata — not scan-bound measured-byte receipts — and must not be
substituted. This module provides a typed status surface so hosts never invent
digests or reuse registry release hashes as scan evidence.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

ReceiptStatus = Literal[
    "unavailable",
    "not_captured",
    "denied",
    "mismatch",
    "ok",
]


def _empty_dict() -> dict[str, Any]:
    return {}


@dataclass(frozen=True, slots=True)
class ScanDependencyReceipt:
    """Typed receipt or explicit non-receipt for one dependency identity."""

    status: ReceiptStatus
    scan_result_uuid: str | None = None
    owner_namespace: str | None = None
    dependency_identity: str | None = None
    algorithm: str | None = None
    digest: str | None = None
    byte_scope: str | None = None
    provenance: dict[str, Any] = field(default_factory=_empty_dict)
    detail: str = ""


def read_scan_dependency_receipt(
    *,
    scan_result_uuid: str,
    owner_namespace: str,
    dependency_identity: str,
) -> ScanDependencyReceipt:
    """Return a typed receipt for scan-bound dependency bytes.

    Until a platform read path exists, always returns ``status="unavailable"``
    with empty digest fields. Callers must treat this as unresolved — never
    invent a digest or substitute a registry release hash.
    """
    return ScanDependencyReceipt(
        status="unavailable",
        scan_result_uuid=scan_result_uuid,
        owner_namespace=owner_namespace,
        dependency_identity=dependency_identity,
        detail=(
            "No supported platform read path for scan-bound dependency digests; "
            "hop remains unresolved."
        ),
    )
