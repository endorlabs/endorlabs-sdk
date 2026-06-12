"""Fast unit tests for code_owners resource models."""

from __future__ import annotations

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


def test_build_create_payload_returns_typed_model() -> None:
    payload = build_create_payload(
        meta={"name": "owners"},
        spec={"patterns": {"*": {"owners": ["team"]}}},
    )
    assert payload.meta.name == "owners"
    assert "*" in (payload.spec.patterns or {})
