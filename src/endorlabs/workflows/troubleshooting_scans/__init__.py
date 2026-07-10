"""Troubleshooting scan workflow — library surface for composition.

CLI-oriented step scripts live in sibling modules; this package re-exports
stable helpers for session scripts. Experimental API.
"""

from __future__ import annotations

from endorlabs.utils.namespace import resource_namespace
from endorlabs.utils.serialization import object_to_dict, to_json_dict
from endorlabs.workflows.common import WorkflowResult
from endorlabs.workflows.troubleshooting_scans.common import (
    load_json,
    match_projects,
    write_json,
)

# Compat alias: prefer ``resource_namespace`` in new code.
project_namespace = resource_namespace

__all__ = [
    "WorkflowResult",
    "load_json",
    "match_projects",
    "object_to_dict",
    "project_namespace",
    "resource_namespace",
    "to_json_dict",
    "write_json",
]
