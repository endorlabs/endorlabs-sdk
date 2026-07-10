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
                "attr_name": "Project",
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
                "attr_name": "Project",
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


def test_registry_contains_pr_comment_config_pascal_case() -> None:
    """Runtime registry should expose PRCommentConfig (endorctl-style PascalCase)."""
    rows = registry_module._load_generated_runtime_contract()
    attrs = {row.get("attr_name") for row in rows}
    assert "PRCommentConfig" in attrs


def test_merge_overlay_warns_on_unknown_contract_key() -> None:
    """Overlay typos should warn instead of failing silently."""
    import endorlabs.registry_overlay as overlay_module
    from endorlabs.registry_overlay import merge_generated_contract_with_overlay

    rows = [{"attr_name": "Project", "resource_name": "projects"}]
    original = overlay_module.RESOURCE_CONTRACT_OVERLAY_BY_ATTR
    try:
        overlay_module.RESOURCE_CONTRACT_OVERLAY_BY_ATTR = {
            "NoSuchKind": {"workflow_flags": ["project-namespace-list"]},
        }
        with pytest.warns(UserWarning, match="NoSuchKind"):
            merge_generated_contract_with_overlay(rows)
    finally:
        overlay_module.RESOURCE_CONTRACT_OVERLAY_BY_ATTR = original
