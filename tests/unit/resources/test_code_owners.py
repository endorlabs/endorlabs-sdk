"""Fast unit tests for code_owners resource models."""

from __future__ import annotations

from unittest.mock import patch

from endorlabs.resources.code_owners import CodeOwners, build_create_payload


def test_code_owners_parses_pattern_entries_and_version() -> None:
    model = CodeOwners(
        uuid="co-1",
        meta={"name": "owners"},
        spec={
            "patterns": {"src/**": {"owners": ["team-a"], "paths": ["src/"]}},
            "version": {"ref": "main", "sha": "abc123"},
        },
    )
    assert model.spec is not None
    assert model.spec.version is not None
    assert model.spec.version.ref == "main"
    assert model.spec.patterns is not None
    assert model.spec.patterns["src/**"].owners == ["team-a"]


def test_code_owners_detects_schema_drift_on_unknown_spec_fields() -> None:
    with patch("endorlabs.resources.code_owners.logger.warning") as mock_warning:
        CodeOwners(
            uuid="co-2",
            meta={"name": "owners"},
            spec={"patterns": {}, "unexpected": True},
        )
    mock_warning.assert_called_once()


def test_build_create_payload_returns_typed_model() -> None:
    payload = build_create_payload(
        meta={"name": "owners"},
        spec={"patterns": {"*": {"owners": ["team"]}}},
    )
    assert payload.meta.name == "owners"
    assert "*" in (payload.spec.patterns or {})
