"""LangGraph agent workflow for Endor Labs SDK.

Experimental: API may change; not covered by the same stability guarantees
as the rest of the SDK.

This module provides a LangGraph-based agent that can interact with the
Endor Labs API using natural language queries. The agent uses a
Plan-Execute-Reflect pattern for multi-step reasoning with tools that
wrap SDK operations.

Requires the 'agent' optional dependencies:
    pip install endorlabs-sdk[agent]
"""

try:
    from .graph import AgentState, create_endor_graph
    from .prompts import (
        PLANNER_PROMPT,
        REFLECTION_PROMPT,
        SYNTHESIS_PROMPT,
        SYSTEM_PROMPT,
    )
    from .tools import create_tools
except ImportError as e:
    _import_error = e

    # Define AgentState stub for type checking when deps not installed
    AgentState = None
    SYSTEM_PROMPT = ""  # type: ignore[misc]
    PLANNER_PROMPT = ""  # type: ignore[misc]
    REFLECTION_PROMPT = ""  # type: ignore[misc]
    SYNTHESIS_PROMPT = ""  # type: ignore[misc]

    def create_endor_graph(*args, **kwargs):  # type: ignore[misc]
        """Raise ImportError with installation instructions."""
        raise ImportError(
            "LangGraph dependencies not installed. "
            "Install with: pip install endorlabs-sdk[agent]"
        ) from _import_error

    def create_tools(*args, **kwargs):  # type: ignore[misc]
        """Raise ImportError with installation instructions."""
        raise ImportError(
            "LangGraph dependencies not installed. "
            "Install with: pip install endorlabs-sdk[agent]"
        ) from _import_error


__all__ = [
    "PLANNER_PROMPT",
    "REFLECTION_PROMPT",
    "SYNTHESIS_PROMPT",
    "SYSTEM_PROMPT",
    "AgentState",
    "create_endor_graph",
    "create_tools",
]
