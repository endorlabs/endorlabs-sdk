"""Shared utilities and result types for workflows."""

from __future__ import annotations

from endorlabs.workflows.common.cli_client import (
    add_client_auth_arguments,
    client_from_namespace_args,
    client_kwargs_from_args,
)
from endorlabs.workflows.common.result import WorkflowResult

__all__ = [
    "WorkflowResult",
    "add_client_auth_arguments",
    "client_from_namespace_args",
    "client_kwargs_from_args",
]
