"""Unit tests for installation inventory helpers."""

from __future__ import annotations

from endorlabs.workflows.projects.inventory import (
    build_installation_lookup,
    installation_display_name,
)


def test_build_installation_lookup_maps_external_id() -> None:
    rows = [
        {"spec": {"external_id": "1"}, "uuid": "a"},
        {"spec": {"external_id": "2"}, "uuid": "b"},
        {"spec": {}, "uuid": "c"},
    ]
    lookup = build_installation_lookup(rows)
    assert set(lookup) == {"1", "2"}


def test_installation_display_name_prefers_external_name() -> None:
    row = {
        "meta": {"name": "Installation - tenant"},
        "spec": {"external_name": "Acme GitHub Org", "login": "acme"},
    }
    assert installation_display_name(row) == "Acme GitHub Org"


def test_installation_display_name_includes_login() -> None:
    row = {
        "meta": {"name": "Installation - tenant"},
        "spec": {"login": "dev.azure.com/org"},
    }
    assert installation_display_name(row) == "Installation - tenant (dev.azure.com/org)"
