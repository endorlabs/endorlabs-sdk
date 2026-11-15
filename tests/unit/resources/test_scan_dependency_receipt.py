"""SDK-001 typed receipt stays unavailable without inventing digests."""

from __future__ import annotations

from endorlabs.resources.scan_dependency_receipt import read_scan_dependency_receipt


def test_receipt_unavailable_has_no_digest() -> None:
    receipt = read_scan_dependency_receipt(
        scan_result_uuid="aaaaaaaaaaaaaaaaaaaaaaaa",
        owner_namespace="example-tenant.child",
        dependency_identity="pypi://requests@2.31.0",
    )
    assert receipt.status == "unavailable"
    assert receipt.digest is None
    assert receipt.algorithm is None
    assert "unresolved" in receipt.detail.lower()
