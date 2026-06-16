"""Unit tests for client stub generation validation guards."""
# pyright: reportMissingImports=false

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[4]
_DEVTOOLS_DIR = str(_REPO_ROOT / "devtools")
if _DEVTOOLS_DIR not in sys.path:
    sys.path.insert(0, _DEVTOOLS_DIR)

import generate_client_stub as stubgen
from sync.policy import (
    MODEL_SYNC_ENTITY_ALIASES_BY_MODEL,
    model_sync_entity_for_model,
)


def test_validate_descriptions_fails_when_registry_description_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Validation should fail when RESOURCE_DESCRIPTIONS misses a registry key."""
    first_attr = stubgen.RESOURCE_REGISTRY[0].attr_name
    patched = {first_attr: ""}
    monkeypatch.setattr(stubgen, "RESOURCE_DESCRIPTIONS", patched)
    contract = {
        entry.attr_name: {
            "attr_name": entry.attr_name,
            "supported_ops": sorted(entry.supported_ops),
            "canonical_entities": sorted(
                model_sync_entity_for_model(entry.model_class)
            ),
        }
        for entry in stubgen.RESOURCE_REGISTRY
    }
    monkeypatch.setattr(stubgen, "_load_facade_contract_resources", lambda: contract)
    monkeypatch.setattr(stubgen, "_load_model_sync_entities", lambda: set())

    with pytest.raises(RuntimeError, match="Missing RESOURCE_DESCRIPTIONS"):
        stubgen._validate_descriptions_and_model_sync()


def test_validate_model_sync_fails_when_registry_entity_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Validation should fail when a registry model has no accepted sync entity."""
    names = set()
    for entry in stubgen.RESOURCE_REGISTRY:
        names.update(model_sync_entity_for_model(entry.model_class))

    missing_model = stubgen.RESOURCE_REGISTRY[0].model_class
    names -= model_sync_entity_for_model(missing_model)
    contract = {
        entry.attr_name: {
            "attr_name": entry.attr_name,
            "supported_ops": sorted(entry.supported_ops),
            "canonical_entities": sorted(
                model_sync_entity_for_model(entry.model_class) & names
            ),
        }
        for entry in stubgen.RESOURCE_REGISTRY
    }
    monkeypatch.setattr(stubgen, "_load_facade_contract_resources", lambda: contract)
    monkeypatch.setattr(stubgen, "_load_model_sync_entities", lambda: set())

    with pytest.raises(RuntimeError, match="Model-sync mapping missing canonical"):
        stubgen._validate_descriptions_and_model_sync()


def test_validate_model_sync_accepts_alias_entities(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Alias entities should satisfy validation for legacy model names."""
    names = set()
    contract = {}
    for entry in stubgen.RESOURCE_REGISTRY:
        accepted = model_sync_entity_for_model(entry.model_class)
        # Simulate alias-only coverage for known compatibility exceptions.
        alias = MODEL_SYNC_ENTITY_ALIASES_BY_MODEL.get(entry.model_class.__name__)
        if alias is not None:
            accepted = {alias}
        names.update(accepted)
        contract[entry.attr_name] = {
            "attr_name": entry.attr_name,
            "supported_ops": sorted(entry.supported_ops),
            "canonical_entities": sorted(accepted),
        }

    monkeypatch.setattr(stubgen, "_load_facade_contract_resources", lambda: contract)
    monkeypatch.setattr(stubgen, "_load_model_sync_entities", lambda: names)

    stubgen._validate_descriptions_and_model_sync()


def test_committed_pyi_uses_specialized_facade_bases() -> None:
    """Specialized runtime facades must appear as stub class bases."""
    pyi_path = _REPO_ROOT / "src" / "endorlabs" / "client_surface.pyi"
    content = pyi_path.read_text(encoding="utf-8")
    for base in (
        "class _ProjectFacade(ProjectFacade)",
        "class _ScanResultFacade(ScanResultFacade)",
        "class _FindingFacade(FindingFacade)",
        "class _PackageVersionFacade(PackageVersionFacade)",
        "class _VectorStoreFacade(VectorStoreFacade)",
        "class _AuthorizationPolicyFacade(AuthorizationPolicyFacade)",
        "class _VulnerabilityFacade(VulnerabilityFacade)",
    ):
        assert base in content


def test_committed_pyi_has_no_orphan_client_attr_docstrings() -> None:
    """Client attr lines must not be followed by stray string literals."""
    pyi_path = _REPO_ROOT / "src" / "endorlabs" / "client_surface.pyi"
    content = pyi_path.read_text(encoding="utf-8")
    client_start = content.index("class Client:")
    attr_region = content[client_start : content.index("    _client:", client_start)]
    assert 'Facade\n    """' not in attr_region
    assert 'CallGraphDataFacade\n    """' not in attr_region


def test_committed_pyi_project_list_and_init_docs() -> None:
    """Project.list and Client.__init__ expose IDE-friendly signatures and docs."""
    pyi_path = _REPO_ROOT / "src" / "endorlabs" / "client_surface.pyi"
    content = pyi_path.read_text(encoding="utf-8")
    project_start = content.index("class _ProjectFacade")
    project_end = content.find("\nclass _", project_start + 1)
    project_section = content[project_start:project_end]
    assert "def list(" in project_section
    assert "traverse:" in project_section
    assert "list_params:" in project_section
    assert "filter:" in project_section
    assert "mask:" in project_section
    assert "List resources with full pagination" in project_section
    assert "def __init__(" in content
    assert "max_retries: int | None" in content
    assert "Resource-oriented client; holds default namespace" in content


def test_committed_pyi_finding_route_methods_not_untyped() -> None:
    """Route sugar on specialized facades must not be clobbered by *args stubs."""
    pyi_path = _REPO_ROOT / "src" / "endorlabs" / "client_surface.pyi"
    content = pyi_path.read_text(encoding="utf-8")
    finding_start = content.index("class _FindingFacade")
    finding_end = content.find("\nclass _", finding_start + 1)
    finding_section = content[finding_start:finding_end]
    assert "def list_by_project(self, *args" not in finding_section
    assert "def list_for_context(self, *args" not in finding_section
