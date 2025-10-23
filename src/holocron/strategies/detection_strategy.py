"""
Detection Strategy Pattern for Content Type Detection.

Extracts complex detection logic from _check_criteria_set() to reduce complexity.
"""

import os
import re
from abc import ABC, abstractmethod
from typing import List


class DetectionStrategy(ABC):
    """Abstract base class for content type detection strategies."""

    @abstractmethod
    def detect(self, file_path: str, normalized_path: str) -> bool:
        """Detect if file matches this strategy's criteria."""
        pass


class PatternDetectionStrategy(DetectionStrategy):
    """Detection strategy using regex patterns."""

    def __init__(self, patterns: List[str]):
        """Initialize with compiled patterns."""
        self.patterns = [re.compile(pattern) for pattern in patterns]

    def detect(self, file_path: str, normalized_path: str) -> bool:
        """Check if file matches any of the patterns."""
        for pattern in self.patterns:
            if pattern.search(normalized_path):
                return True
        return False


class ExtensionDetectionStrategy(DetectionStrategy):
    """Detection strategy using file extensions."""

    def __init__(self, extensions: List[str]):
        """Initialize with file extensions."""
        self.extensions = [ext.lower() for ext in extensions]

    def detect(self, file_path: str, normalized_path: str) -> bool:
        """Check if file extension matches."""
        if not self.extensions:
            return False

        file_ext = os.path.splitext(file_path)[1].lower()
        return file_ext in self.extensions


class CriteriaDetectionStrategy(DetectionStrategy):
    """Detection strategy using complex criteria sets."""

    def __init__(self, criteria: List[dict]):
        """Initialize with criteria sets."""
        self.criteria = criteria

    def detect(self, file_path: str, normalized_path: str) -> bool:
        """Check criteria with AND logic within sets, OR logic between sets."""
        file_name = os.path.basename(file_path)

        for criteria_set in self.criteria:
            if self._check_criteria_set(criteria_set, normalized_path, file_name):
                return True
        return False

    def _check_criteria_set(
        self, criteria_set: dict, normalized_path: str, file_name: str
    ) -> bool:
        """Check criteria with AND logic, except file_extensions use OR logic."""
        # Check file extensions (OR logic)
        if "file_extensions" in criteria_set:
            extensions = criteria_set["file_extensions"]
            file_ext = os.path.splitext(file_name)[1].lower()
            if not any(ext.lower() == file_ext for ext in extensions):
                return False

        # Check not patterns (AND logic - none should match)
        if "not_patterns" in criteria_set:
            not_patterns = criteria_set["not_patterns"]
            for pattern in not_patterns:
                if re.compile(pattern).search(normalized_path):
                    return False

        # Check not file patterns (AND logic - none should match)
        if "not_file_patterns" in criteria_set:
            not_file_patterns = criteria_set["not_file_patterns"]
            for pattern in not_file_patterns:
                if re.compile(pattern).search(file_name):
                    return False

        # Check patterns (AND logic - all must match)
        if "patterns" in criteria_set:
            patterns = criteria_set["patterns"]
            for pattern in patterns:
                if not re.compile(pattern).search(normalized_path):
                    return False

        return True


class DetectionStrategyFactory:
    """Factory for creating detection strategies."""

    @staticmethod
    def create_strategies(config: dict) -> List[DetectionStrategy]:
        """Create detection strategies from configuration."""
        strategies = []

        # Add pattern strategy if patterns exist
        if config.get("patterns"):
            strategies.append(PatternDetectionStrategy(config["patterns"]))

        # Add extension strategy if extensions exist
        if config.get("extensions"):
            strategies.append(ExtensionDetectionStrategy(config["extensions"]))

        # Add criteria strategy if criteria exist
        if config.get("criteria"):
            strategies.append(CriteriaDetectionStrategy(config["criteria"]))

        return strategies
