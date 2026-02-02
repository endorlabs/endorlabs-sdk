"""Shared utilities for Endor Cockpit SDK.

This module provides common utilities used across resource modules to avoid
code duplication while maintaining functionality and type safety.
"""

from .model_consistency import (
    compute_attribute_overlap_report,
    compute_flatten_collision_report,
    compute_model_consistency_diff,
    enumerate_sdk_models_flat_paths,
    enumerate_spec_fields_flat,
    enumerate_spec_top_level_refs,
    load_spec,
    path_to_flattened,
    run_model_consistency_report,
)
from .namespace import resolve_namespace_for_resource
from .schema_drift import SchemaDriftDetector
from .traversal import create_namespace_scoped_params, create_traverse_params

__all__ = [
    "SchemaDriftDetector",
    "compute_attribute_overlap_report",
    "compute_flatten_collision_report",
    "compute_model_consistency_diff",
    "create_namespace_scoped_params",
    "create_traverse_params",
    "enumerate_sdk_models_flat_paths",
    "enumerate_spec_fields_flat",
    "enumerate_spec_top_level_refs",
    "load_spec",
    "path_to_flattened",
    "resolve_namespace_for_resource",
    "run_model_consistency_report",
]
