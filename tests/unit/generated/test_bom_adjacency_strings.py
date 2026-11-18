"""SDK-005: BOM dependency_graph adjacency accepts coordinate strings."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from endorlabs.generated.models.package_version_service import V1Bom


def test_v1bom_accepts_string_adjacency_entries() -> None:
    bom = V1Bom.model_validate(
        {
            "resolution_timestamp": "2024-01-01T00:00:00Z",
            "dependency_graph": {
                "mvn://MVN_CENTRAL/foo:bar@1.0": [
                    "mvn://MVN_CENTRAL/foo:dep@2.0",
                    {"name": "object-also-ok"},
                ]
            },
        }
    )
    assert bom.dependency_graph is not None
    entries = bom.dependency_graph["mvn://MVN_CENTRAL/foo:bar@1.0"]
    assert entries[0] == "mvn://MVN_CENTRAL/foo:dep@2.0"
    assert entries[1] == {"name": "object-also-ok"}


def test_v1bom_rejects_non_string_non_object_adjacency() -> None:
    with pytest.raises(ValidationError):
        V1Bom.model_validate(
            {
                "resolution_timestamp": "2024-01-01T00:00:00Z",
                "dependency_graph": {"k": [123]},
            }
        )
