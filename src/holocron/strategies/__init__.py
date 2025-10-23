"""
Detection strategies for Holocron.

Provides strategy pattern implementations for content type detection.
"""

from .detection_strategy import (
    CriteriaDetectionStrategy,
    DetectionStrategy,
    DetectionStrategyFactory,
    ExtensionDetectionStrategy,
    PatternDetectionStrategy,
)

__all__ = [
    "DetectionStrategy",
    "PatternDetectionStrategy",
    "ExtensionDetectionStrategy",
    "CriteriaDetectionStrategy",
    "DetectionStrategyFactory",
]
