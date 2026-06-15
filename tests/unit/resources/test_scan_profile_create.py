"""Unit tests for ScanProfile create payload promotion."""

from __future__ import annotations

import pytest

from endorlabs.resources.scan_profile import (
    CreateScanProfilePayload,
    ScanProfileMetaCreate,
    ScanProfileSpecCreate,
    build_create_payload,
)


def test_build_create_payload_promotes_name_and_description() -> None:
    payload = build_create_payload(
        name="profile-a",
        description="desc",
        is_default=False,
        propagate=False,
    )
    assert isinstance(payload, CreateScanProfilePayload)
    assert payload.meta.name == "profile-a"
    assert payload.meta.description == "desc"
    assert payload.spec.is_default is False
    assert payload.propagate is False


def test_build_create_payload_requires_name() -> None:
    with pytest.raises(TypeError, match="requires name"):
        build_create_payload(description="only-desc", is_default=False)


def test_build_create_payload_accepts_nested_meta() -> None:
    payload = build_create_payload(
        meta=ScanProfileMetaCreate(name="nested", description="d"),
        spec=ScanProfileSpecCreate(is_default=True),
    )
    assert payload.meta.name == "nested"
