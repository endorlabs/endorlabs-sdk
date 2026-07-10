"""Shared utilities and result types for workflows."""

from __future__ import annotations

from dataclasses import dataclass, field


def _empty_str_list() -> list[str]:
    return []


@dataclass
class WorkflowResult:
    """Base result type for all workflow functions.

    Attributes:
        status: Overall status (``"success"``, ``"partial"``, ``"error"``).
        message: Human-readable summary of what happened.
        errors: List of error messages encountered during execution.
    """

    status: str = "success"
    message: str = ""
    errors: list[str] = field(default_factory=_empty_str_list)

    @property
    def ok(self) -> bool:
        """Return True when the workflow completed without errors."""
        return self.status == "success"
