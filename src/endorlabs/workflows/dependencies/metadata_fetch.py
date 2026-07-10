"""DependencyMetadata fetch — thin re-export of ``endorlabs.tools.dependency_metadata``.

Prefer importing from ``endorlabs.tools.dependency_metadata`` in new code.
"""

from __future__ import annotations

from endorlabs.tools.dependency_metadata import (
    retrieve_dep_metadata_full,
    summarize_dep_metadata,
)

__all__ = [
    "retrieve_dep_metadata_full",
    "summarize_dep_metadata",
]
