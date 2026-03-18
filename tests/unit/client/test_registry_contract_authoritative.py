"""Contract-authoritative runtime registry behavior tests."""

from __future__ import annotations

import pytest

import endorlabs.registry as registry_module


def test_registry_module_has_no_runtime_fallback_helpers() -> None:
    """Legacy fallback loaders must not remain in runtime registry module."""
    assert not hasattr(registry_module, "_fallback_model_class")
    assert not hasattr(registry_module, "_fallback_create_builder")


def test_registry_requires_model_import_path(monkeypatch: pytest.MonkeyPatch) -> None:
    """Registry build must fail fast when model import path is missing."""

    def _rows() -> list[dict[str, object]]:
        return [
            {
                "attr_name": "project",
                "resource_name": "projects",
                "model_class": "Project",
                "supported_ops": ["list", "get", "create", "update", "delete"],
                "filter_kwarg_map": {},
            }
        ]

    monkeypatch.setattr(registry_module, "_load_generated_runtime_contract", _rows)
    monkeypatch.setattr(
        registry_module,
        "merge_generated_contract_with_overlay",
        lambda rows: rows,
    )

    with pytest.raises(TypeError, match="Missing model_class_import_path"):
        registry_module._build_resource_registry()


def test_registry_requires_builder_import_path_when_builder_name_present(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Named create builder must include import path in the contract."""

    def _rows() -> list[dict[str, object]]:
        return [
            {
                "attr_name": "project",
                "resource_name": "projects",
                "model_class": "Project",
                "model_class_import_path": "endorlabs.resources.project:Project",
                "build_create_payload_fn_name": "project_build_create",
                "supported_ops": ["list", "get", "create", "update", "delete"],
                "filter_kwarg_map": {},
            }
        ]

    monkeypatch.setattr(registry_module, "_load_generated_runtime_contract", _rows)
    monkeypatch.setattr(
        registry_module,
        "merge_generated_contract_with_overlay",
        lambda rows: rows,
    )

    with pytest.raises(TypeError, match="Missing build_create_payload_fn_import_path"):
        registry_module._build_resource_registry()
