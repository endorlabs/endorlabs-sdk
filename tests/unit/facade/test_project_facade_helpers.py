"""Unit tests for ProjectFacade inventory boolean helpers."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from endorlabs.facade.specialized import ProjectFacade
from endorlabs.registry import RESOURCE_REGISTRY
from endorlabs.resources.project import (
    is_app_project_row,
    is_cli_project_row,
    is_sbom_project_row,
)


@pytest.fixture
def facade() -> ProjectFacade:
    entry = next(e for e in RESOURCE_REGISTRY if e.attr_name == "Project")
    return ProjectFacade(MagicMock(), "tenant.root", entry)


def test_is_sbom_dict_row() -> None:
    sbom = {"spec": {"sbom": {"format": "cyclonedx"}}}
    regular = {"spec": {"git": {}}}

    assert is_sbom_project_row(sbom) is True
    assert is_sbom_project_row(regular) is False


def test_is_app_and_cli_dict_rows() -> None:
    app = {"spec": {"git": {"external_installation_id": "123"}}}
    cli = {"spec": {"git": {}}}

    assert is_app_project_row(app) is True
    assert is_cli_project_row(app) is False
    assert is_app_project_row(cli) is False
    assert is_cli_project_row(cli) is True


def test_facade_delegates_to_row_helpers(facade: ProjectFacade) -> None:
    app = {"spec": {"git": {"external_installation_id": "99"}}}
    cli = {"spec": {"git": {}}}
    sbom = {"spec": {"sbom": {}}}

    assert facade.is_app(app) is True
    assert facade.is_cli(cli) is True
    assert facade.is_sbom(sbom) is True
