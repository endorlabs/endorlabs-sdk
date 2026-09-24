"""Unit tests for SBOM coverage classifier and create payloads."""

from __future__ import annotations

from pathlib import Path

import pytest

from endorlabs.resources.imported_sbom import (
    CreateImportedSBOMPayload,
)
from endorlabs.resources.imported_sbom import (
    build_create_payload as build_imported_payload,
)
from endorlabs.resources.sbom_export import (
    CreateSBOMExportPayload,
)
from endorlabs.resources.sbom_export import (
    build_create_payload as build_export_payload,
)
from endorlabs.workflows.sbom.coverage import (
    classify_purl_type,
    eco_bucket,
    is_odd_purl_type,
    parse_sbom_file,
)
from endorlabs.workflows.sbom.import_sbom import parse_import_output

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def test_parse_good_cyclonedx_counts_metadata_and_components() -> None:
    stats = parse_sbom_file(FIXTURES / "good_cyclonedx.json")
    assert stats.format_kind == "cyclonedx-json"
    assert stats.total == 3
    assert stats.with_purl == 3
    assert stats.odd_purl_types == {}
    assert stats.reserved_cdx_properties == []


def test_parse_bad_purls_and_reserved_cdx_properties() -> None:
    stats = parse_sbom_file(FIXTURES / "bad_purls_cyclonedx.json")
    assert stats.total == 4  # metadata + 3 components
    assert "javascript" in stats.odd_purl_types
    assert "swif" in stats.odd_purl_types
    # pkg:gem:rails is malformed (colon vs slash) — type becomes "gem:rails@7.0.0" or "gem"
    assert stats.odd_purl_types  # at least one odd type
    assert "cdx:vcs:hash" in stats.reserved_cdx_properties


def test_parse_good_spdx() -> None:
    stats = parse_sbom_file(FIXTURES / "good_spdx.json")
    assert stats.format_kind == "spdx-json"
    assert stats.total == 2
    assert stats.with_purl == 2
    assert stats.odd_purl_types == {}


def test_classify_purl_types() -> None:
    assert classify_purl_type("pkg:pypi/requests@2.0") == "pypi"
    assert classify_purl_type("pkg:javascript/left-pad@1") == "javascript"
    assert classify_purl_type("not-a-purl") is None
    assert is_odd_purl_type("javascript") is True
    assert is_odd_purl_type("pypi") is False
    assert eco_bucket("pypi://requests@2.0") == "pypi"
    assert eco_bucket("sbom://pkg") == "sbom"


def test_parse_import_output_project_and_name() -> None:
    log = (
        "INFO: Scanning Project UUID: abcdef0123456789abcdef01 Tenant: example-tenant\n"
        "INFO: SBOM import complete for project: 'abcdef0123456789abcdef01', "
        "SBOM name: 'urn:uuid:00000000-0000-4000-8000-0000000000aa', supplier name: ''\n"
    )
    project_uuid, sbom_name = parse_import_output(log)
    assert project_uuid == "abcdef0123456789abcdef01"
    assert sbom_name == "urn:uuid:00000000-0000-4000-8000-0000000000aa"


def test_build_imported_sbom_create_payload() -> None:
    payload = build_imported_payload(
        meta={"name": "example-import"},
        spec={
            "kind": "SBOM_KIND_CYCLONEDX",
            "cyclone_dx": '{"bomFormat":"CycloneDX"}',
        },
        context={"type": "CONTEXT_TYPE_MAIN", "id": "default"},
    )
    assert isinstance(payload, CreateImportedSBOMPayload)
    assert isinstance(payload.meta, dict)
    assert isinstance(payload.spec, dict)
    assert payload.meta["name"] == "example-import"
    assert payload.spec["kind"] == "SBOM_KIND_CYCLONEDX"


def test_build_sbom_export_create_payload() -> None:
    payload = build_export_payload(
        meta={
            "name": "export-1",
            "parent_kind": "PackageVersion",
            "parent_uuid": "000000000000000000000001",
        },
        spec={
            "component_type": "COMPONENT_TYPE_APPLICATION",
            "kind": "SBOM_KIND_CYCLONEDX",
            "format": "FORMAT_JSON",
        },
    )
    assert isinstance(payload, CreateSBOMExportPayload)
    assert isinstance(payload.spec, dict)
    assert payload.spec["component_type"] == "COMPONENT_TYPE_APPLICATION"


def test_build_imported_rejects_unknown_kwargs() -> None:
    with pytest.raises(TypeError, match="Invalid create kwargs"):
        build_imported_payload(not_a_field=True)
