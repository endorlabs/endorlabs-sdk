"""Unit tests for client stub generation validation guards."""
# pyright: reportMissingImports=false

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[4]
_SCRIPTS_DIR = str(_REPO_ROOT / "scripts")
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)

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
            "canonical_entities": sorted(model_sync_entity_for_model(entry.model_class)),
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
            "canonical_entities": sorted(model_sync_entity_for_model(entry.model_class) & names),
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
