"""Deprecated: use endorlabs.experimental.sast_analysis instead.

This package is deprecated. Import from endorlabs.experimental.sast_analysis
for FindingDataLoader and FindingDatabase.
"""

import warnings

from endorlabs.experimental.sast_analysis import FindingDataLoader, FindingDatabase

warnings.warn(
    "endorlabs.analysis is deprecated; use endorlabs.experimental.sast_analysis",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = [
    "FindingDataLoader",
    "FindingDatabase",
]
