"""
Content Type System for Holocron

Provides extensible content type detection and chunking strategies.
Supports custom content types through configuration and inheritance.
"""

import json
import os
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from .config import ContentTypeConfig
from .strategies import DetectionStrategyFactory


@dataclass
class Chunk:
    """Represents a chunk of content with metadata."""

    text: str
    metadata: Dict[str, Any]

    def __post_init__(self):
        """Validate chunk data."""
        if not self.text:
            raise ValueError("Chunk text cannot be empty")

        if not isinstance(self.metadata, dict):
            raise ValueError("Chunk metadata must be a dictionary")


class ContentSource(ABC):
    """Abstract base class for content sources."""

    def __init__(self, config: ContentTypeConfig):
        """Initialize content source with configuration."""
        self.config = config
        # Support both old patterns and new criteria
        if hasattr(config, "patterns") and config.patterns:
            self._compiled_patterns = [
                re.compile(pattern) for pattern in config.patterns
            ]
        else:
            self._compiled_patterns = []

        # New robust criteria system
        self._criteria = getattr(config, "criteria", [])
        self._criteria_rst = getattr(config, "criteria_rst", [])
        self._compiled_criteria = self._compile_criteria()

        # Initialize detection strategies
        self._detection_strategies = self._create_detection_strategies()

    def _compile_criteria(self) -> List[Dict]:
        """Compile criteria for efficient matching."""
        compiled = []

        # Process main criteria
        for criterion in self._criteria:
            compiled.append(self._compile_single_criterion(criterion))

        # Process criteria_rst (alternative criteria for .rst files)
        for criterion in self._criteria_rst:
            compiled.append(self._compile_single_criterion(criterion))

        return compiled

    def _create_detection_strategies(self) -> List:
        """Create detection strategies from configuration."""

        # Create strategy configuration
        strategy_config = {
            "patterns": (
                self.config.patterns if hasattr(self.config, "patterns") else []
            ),
            "extensions": (
                self.config.extensions if hasattr(self.config, "extensions") else []
            ),
            "criteria": self._criteria,
        }

        return DetectionStrategyFactory.create_strategies(strategy_config)

    def _compile_single_criterion(self, criterion: Dict[str, str]) -> Dict:
        """Compile a single criterion."""
        criterion_type = criterion.get("type")
        value = criterion.get("value")

        if criterion_type == "path_pattern":
            return {
                "type": "path_pattern",
                "pattern": re.compile(value),
                "value": value,
            }
        elif criterion_type == "not_path_pattern":
            return {
                "type": "not_path_pattern",
                "pattern": re.compile(value),
                "value": value,
            }
        elif criterion_type == "file_extension":
            return {"type": "file_extension", "value": value.lower()}
        elif criterion_type == "file_name":
            return {"type": "file_name", "pattern": re.compile(value), "value": value}
        else:
            # Fallback to pattern matching for unknown types
            return {"type": "pattern", "pattern": re.compile(value), "value": value}

    @abstractmethod
    def chunk_content(self, content: str, file_path: str = "") -> List[Chunk]:
        """
        Chunk content according to the content type strategy.

        Args:
            content: Raw content to chunk
            file_path: Path to source file (for metadata)

        Returns:
            List of Chunk objects
        """
        pass

    def detect(self, file_path: str) -> bool:
        """
        Detect if file matches this content type using strategy pattern.

        Args:
            file_path: Path to file to check

        Returns:
            True if file matches this content type
        """
        # Normalize path for cross-platform compatibility
        normalized_path = os.path.normpath(file_path).replace(os.path.sep, "/")

        # Use strategy pattern for detection
        for strategy in self._detection_strategies:
            if strategy.detect(file_path, normalized_path):
                return True

        # Fallback to old pattern system for backward compatibility
        return self._detect_with_patterns(normalized_path, file_path)

    def _detect_with_criteria(self, normalized_path: str, file_path: str) -> bool:
        """
        Detect using multi-criteria AND logic within each criteria set,
        OR logic between sets.
        """
        # Check main criteria (AND logic within this set)
        main_criteria_match = self._check_criteria_set(
            self._criteria, normalized_path, file_path
        )

        # Check criteria_rst (AND logic within this set)
        rst_criteria_match = self._check_criteria_set(
            self._criteria_rst, normalized_path, file_path
        )

        # Return True if either set matches (OR logic between sets)
        return main_criteria_match or rst_criteria_match

    def _check_criteria_set(
        self, criteria_set: List[Dict], normalized_path: str, file_path: str
    ) -> bool:
        """
        Legacy method - now handled by strategy pattern.
        Kept for backward compatibility.
        """
        # This method is deprecated - use strategy pattern instead
        return False

    def _detect_with_patterns(self, normalized_path: str, file_path: str) -> bool:
        """Fallback to old pattern-based detection."""
        # Check patterns
        for pattern in self._compiled_patterns:
            if pattern.search(normalized_path):
                return True

        # Check extensions if provided
        if self.config.extensions:
            file_ext = os.path.splitext(file_path)[1].lower()
            if file_ext in self.config.extensions:
                return True

        return False

    def _create_chunk_metadata(
        self, chunk_text: str, chunk_index: int, file_path: str = "", **kwargs
    ) -> Dict[str, Any]:
        """Create metadata dictionary for a chunk."""
        metadata = {
            "content_type": self.config.name.lower().replace(" ", "_"),
            "chunk_index": chunk_index,
            "size": len(chunk_text),
            "file_path": file_path,
            "file_name": os.path.basename(file_path) if file_path else "",
        }

        # Add any additional metadata
        metadata.update(kwargs)

        # Remove None values
        return {k: v for k, v in metadata.items() if v is not None}


class MarkdownSource(ContentSource):
    """Content source for markdown documentation."""

    def chunk_content(self, content: str, file_path: str = "") -> List[Chunk]:
        """Chunk markdown content by headers and paragraphs."""
        chunks = []
        lines = content.split("\n")
        current_chunk = []
        current_size = 0

        # Track document structure for enhanced metadata
        h1_title = None
        resource_type = None
        current_section = None
        current_subsection = None
        current_header_level = None

        for line in lines:
            # Check if this is an H2 header (starts with ## but not ###)
            if line.strip().startswith("## ") and not line.strip().startswith("### "):
                # Save current chunk if it has content
                if current_chunk:
                    chunk_text = "\n".join(current_chunk)
                    chunks.append(
                        Chunk(
                            text=chunk_text,
                            metadata=self._create_chunk_metadata(
                                chunk_text,
                                len(chunks),
                                file_path,
                                resource_type=resource_type,
                                h1_title=h1_title,
                                section_name=current_section,
                                subsection_name=current_subsection,
                                header_level=current_header_level,
                            ),
                        )
                    )

                # Parse header level and content
                header_level = self._get_header_level(line)
                header_text = self._clean_header_text(line)

                # Update tracking variables
                if header_level == "h1":
                    h1_title = header_text
                    resource_type = self._extract_resource_type(header_text)
                    current_section = None
                    current_subsection = None
                elif header_level == "h2":
                    current_section = header_text
                    current_subsection = None
                elif header_level == "h3":
                    current_subsection = header_text

                current_header_level = header_level

                # Start new chunk with header
                current_chunk = [line]
                current_size = len(line)
            else:
                # Add line to current chunk
                current_chunk.append(line)
                current_size += len(line) + 1  # +1 for newline

                # Check if chunk is too large
                if (
                    current_size > self.config.chunk_size
                    and not self.config.preserve_complete_sections
                ):
                    # Save current chunk
                    chunk_text = "\n".join(current_chunk)
                    chunks.append(
                        Chunk(
                            text=chunk_text,
                            metadata=self._create_chunk_metadata(
                                chunk_text,
                                len(chunks),
                                file_path,
                                resource_type=resource_type,
                                h1_title=h1_title,
                                section_name=current_section,
                                subsection_name=current_subsection,
                                header_level=current_header_level,
                            ),
                        )
                    )

                    # Start new chunk
                    current_chunk = []
                    current_size = 0

        # Add final chunk
        if current_chunk:
            chunk_text = "\n".join(current_chunk)
            chunks.append(
                Chunk(
                    text=chunk_text,
                    metadata=self._create_chunk_metadata(
                        chunk_text,
                        len(chunks),
                        file_path,
                        resource_type=resource_type,
                        h1_title=h1_title,
                        section_name=current_section,
                        subsection_name=current_subsection,
                        header_level=current_header_level,
                    ),
                )
            )

        return chunks

    def _get_header_level(self, line: str) -> str:
        """Extract header level from markdown line."""
        stripped = line.strip()
        if stripped.startswith("# "):
            return "h1"
        elif stripped.startswith("## "):
            return "h2"
        elif stripped.startswith("### "):
            return "h3"
        elif stripped.startswith("#### "):
            return "h4"
        elif stripped.startswith("##### "):
            return "h5"
        elif stripped.startswith("###### "):
            return "h6"
        else:
            return "unknown"

    def _clean_header_text(self, line: str) -> str:
        """Clean header text by removing markdown formatting and emojis."""
        # Remove markdown header markers
        text = line.strip().lstrip("#").strip()

        # Remove emojis and special characters
        text = re.sub(r"[^\w\s\-\.]", "", text)

        # Clean up extra whitespace
        text = re.sub(r"\s+", " ", text).strip()

        return text

    def _extract_resource_type(self, h1_title: str) -> str:
        """Extract resource type from H1 title."""
        if "Project" in h1_title:
            return "project"
        elif "Finding" in h1_title:
            return "finding"
        elif "Policy" in h1_title:
            return "policy"
        elif "Namespace" in h1_title:
            return "namespace"
        elif "Scan" in h1_title:
            return "scan"
        else:
            return "unknown"


class ExternalDocsSource(ContentSource):
    """Content source for external documentation."""

    def chunk_content(self, content: str, file_path: str = "") -> List[Chunk]:
        """Chunk external documentation content - preserve complete sections."""
        chunks = []
        lines = content.split("\n")

        # Track structure
        h1_title = None
        current_section = None
        current_subsection = None
        source_url = self._extract_source_url(lines)

        # Accumulate content until next header
        current_chunk = []
        current_size = 0

        for i, line in enumerate(lines):
            if self._should_skip_line(line):
                continue

            # Check for underline header pattern (look-behind)
            # is_underline_header = False  # Not used
            if i > 0 and self._is_underline(line):
                # Previous line is the actual header text
                header_text = lines[i - 1].strip()
                if header_text and not self._should_skip_line(lines[i - 1]):
                    # is_underline_header = True  # Not used
                    # Process i-1 and i together as header
                    if current_chunk:
                        self._save_current_chunk(
                            current_chunk,
                            chunks,
                            source_url,
                            h1_title,
                            current_section,
                            current_subsection,
                            file_path,
                        )
                        current_chunk = []
                        current_size = 0

                    # Update tracking for the header
                    h1_title, current_section, current_subsection = (
                        self._update_header_tracking(
                            lines[i - 1], h1_title, current_section, current_subsection
                        )
                    )

                    # Start new chunk WITH header + underline
                    current_chunk = [lines[i - 1], line]
                    current_size = len(lines[i - 1]) + len(line) + 1
                    # Skip processing this underline line since we've already added it
                    continue

            # Check if this is a regular header
            if self._is_external_doc_header(line):
                # If we have accumulated content, save it now with its header
                if current_chunk:
                    self._save_current_chunk(
                        current_chunk,
                        chunks,
                        source_url,
                        h1_title,
                        current_section,
                        current_subsection,
                        file_path,
                    )
                    current_chunk = []
                    current_size = 0

                # Update tracking - DON'T save yet
                h1_title, current_section, current_subsection = (
                    self._update_header_tracking(
                        line, h1_title, current_section, current_subsection
                    )
                )

                # Start new chunk WITH this header
                current_chunk = [line]
                current_size = len(line)
            else:
                # Accumulate content
                current_chunk.append(line)
                current_size += len(line) + 1

                # Only split if chunk is too large AND we're not in middle of a section
                # Look ahead to see if next line is a header
                if current_size > self.config.chunk_size:
                    is_next_header = i + 1 < len(lines) and (
                        self._is_external_doc_header(lines[i + 1])
                        or (i + 2 < len(lines) and self._is_underline(lines[i + 1]))
                    )

                    if is_next_header or current_size > self.config.chunk_size * 1.5:
                        # Save and start new chunk
                        self._save_current_chunk(
                            current_chunk,
                            chunks,
                            source_url,
                            h1_title,
                            current_section,
                            current_subsection,
                            file_path,
                        )
                        current_chunk = []
                        current_size = 0

        # Save final chunk
        if current_chunk:
            self._save_current_chunk(
                current_chunk,
                chunks,
                source_url,
                h1_title,
                current_section,
                current_subsection,
                file_path,
            )

        return chunks

    def _extract_source_url(self, lines: List[str]) -> str:
        """Extract source URL from HTML comment in first few lines."""
        for line in lines[:5]:  # Check first few lines for source URL
            if line.strip().startswith("<!-- Source:"):
                return line.strip().replace("<!-- Source: ", "").replace(" -->", "")
        return ""

    def _should_skip_line(self, line: str) -> bool:
        """Check if line should be skipped (HTML comments, breadcrumbs)."""
        stripped = line.strip()
        return (
            stripped.startswith("<!--")
            or stripped.startswith("1. [")
            or stripped.startswith("2. [")
            or stripped.startswith("3. [")
        )

    def _is_underline(self, line: str) -> bool:
        """Check if line is an underline (=== or ---)."""
        stripped = line.strip()
        if len(stripped) < 3:
            return False
        return all(c == "=" for c in stripped) or all(c == "-" for c in stripped)

    def _is_external_doc_header(self, line: str) -> bool:
        """Check if line is a header in external docs format."""
        stripped = line.strip()

        # Ignore empty lines and very short lines
        if len(stripped) < 3:
            return False

        # Check for underline headers ONLY if previous line exists
        # This requires look-behind logic - move to parent function
        if (
            stripped.endswith("=")
            and len(stripped) > 3
            and all(c == "=" for c in stripped)
        ):
            return True
        if (
            stripped.endswith("-")
            and len(stripped) > 3
            and all(c == "-" for c in stripped)
        ):
            return True

        # Remove title case check - too aggressive, matches breadcrumbs
        return False

    def _clean_external_header_text(self, line: str) -> str:
        """Clean external doc header text."""
        # Remove underline characters
        text = line.strip().rstrip("=-")

        # Remove extra whitespace
        text = re.sub(r"\s+", " ", text).strip()

        return text

    def _update_header_tracking(
        self,
        line: str,
        h1_title: Optional[str],
        current_section: Optional[str],
        current_subsection: Optional[str],
    ) -> tuple:
        """Update header tracking variables based on line content."""
        header_text = self._clean_external_header_text(line)

        if line.strip().endswith("="):
            return header_text, "", ""
        elif line.strip().endswith("-"):
            return h1_title or "", header_text, ""
        else:
            return h1_title or "", current_section or "", header_text

    def _save_current_chunk(
        self,
        current_chunk: List[str],
        chunks: List[Chunk],
        source_url: str,
        h1_title: Optional[str],
        current_section: Optional[str],
        current_subsection: Optional[str],
        file_path: str,
    ) -> None:
        """Save current chunk to chunks list."""
        if current_chunk:
            chunk_text = "\n".join(current_chunk)
            chunks.append(
                Chunk(
                    text=chunk_text,
                    metadata=self._create_chunk_metadata(
                        chunk_text,
                        len(chunks),
                        file_path,
                        source_url=source_url or "",
                        h1_title=h1_title or "",
                        section_name=current_section or "",
                        subsection_name=current_subsection or "",
                    ),
                )
            )


class CodeSource(ContentSource):
    """Content source for source code files."""

    def chunk_content(self, content: str, file_path: str = "") -> List[Chunk]:
        """Chunk code content by functions and classes."""
        chunks = []
        lines = content.split("\n")
        current_chunk = []
        current_size = 0

        for line in lines:
            # Check if this is a function or class definition
            if line.strip().startswith(("def ", "class ")):
                # Save current chunk if it has content
                if current_chunk:
                    chunk_text = "\n".join(current_chunk)
                    chunks.append(
                        Chunk(
                            text=chunk_text,
                            metadata=self._create_chunk_metadata(
                                chunk_text, len(chunks), file_path
                            ),
                        )
                    )

                # Start new chunk
                current_chunk = [line]
                current_size = len(line)
            else:
                # Add line to current chunk
                current_chunk.append(line)
                current_size += len(line) + 1

                # Check if chunk is too large
                if current_size > self.config.chunk_size:
                    # Save current chunk
                    chunk_text = "\n".join(current_chunk)
                    chunks.append(
                        Chunk(
                            text=chunk_text,
                            metadata=self._create_chunk_metadata(
                                chunk_text, len(chunks), file_path
                            ),
                        )
                    )

                    # Start new chunk
                    current_chunk = []
                    current_size = 0

        # Add final chunk
        if current_chunk:
            chunk_text = "\n".join(current_chunk)
            chunks.append(
                Chunk(
                    text=chunk_text,
                    metadata=self._create_chunk_metadata(
                        chunk_text, len(chunks), file_path
                    ),
                )
            )

        return chunks


class ApiSpecSource(ContentSource):
    """Content source for API specifications."""

    def chunk_content(self, content: str, file_path: str = "") -> List[Chunk]:
        """Chunk API specification content by sections."""
        chunks = []
        try:
            data = json.loads(content)
        except json.JSONDecodeError:
            # If not JSON, treat as generic content
            return self._chunk_generic(content, file_path)

        # Chunk by major sections
        for section_name, section_content in data.items():
            if isinstance(section_content, dict):
                section_text = json.dumps({section_name: section_content}, indent=2)
                chunks.append(
                    Chunk(
                        text=section_text,
                        metadata=self._create_chunk_metadata(
                            section_text, len(chunks), file_path, section=section_name
                        ),
                    )
                )

        return chunks

    def _chunk_generic(self, content: str, file_path: str) -> List[Chunk]:
        """Generic chunking for non-JSON content."""
        chunks = []
        words = content.split()
        current_chunk = []
        current_size = 0

        for word in words:
            current_chunk.append(word)
            current_size += len(word) + 1  # +1 for space

            if current_size > self.config.chunk_size:
                chunk_text = " ".join(current_chunk)
                chunks.append(
                    Chunk(
                        text=chunk_text,
                        metadata=self._create_chunk_metadata(
                            chunk_text, len(chunks), file_path
                        ),
                    )
                )

                current_chunk = []
                current_size = 0

        # Add final chunk
        if current_chunk:
            chunk_text = " ".join(current_chunk)
            chunks.append(
                Chunk(
                    text=chunk_text,
                    metadata=self._create_chunk_metadata(
                        chunk_text, len(chunks), file_path
                    ),
                )
            )

        return chunks


class ContentTypeRegistry:
    """Registry for managing content type sources."""

    def __init__(
        self,
        content_types: Dict[str, ContentTypeConfig] = None,
        collection_mapping: Dict[str, str] = None,
        collections: Dict[str, Any] = None,
    ):
        """Initialize registry with content type configurations."""
        self.content_types = content_types or {}
        self.collection_mapping = collection_mapping or {}
        self.collections = collections or {}
        self.sources = {}
        self._initialize_sources()

    def _initialize_sources(self):
        """Initialize content source instances."""
        # Initialize from collections (new format)
        for collection_name, collection_config in self.collections.items():
            # Convert collection config to content type config
            content_type_config = collection_config.to_content_type_config()
            source_class = self._get_source_class(collection_name)
            self.sources[collection_name] = source_class(content_type_config)

        # Initialize from legacy content types (for backward compatibility)
        for content_type_name, config in self.content_types.items():
            # Map content type names to source classes
            source_class = self._get_source_class(content_type_name)
            self.sources[content_type_name] = source_class(config)

    def _get_source_class(self, content_type_name: str) -> type:
        """Get source class for content type."""
        source_mapping = {
            # New collection names
            "markdown": MarkdownSource,
            "endor_user_docs": ExternalDocsSource,
            "code": CodeSource,
            "api_spec": ApiSpecSource,
            # Legacy content type names
            "external_docs": ExternalDocsSource,
        }

        return source_mapping.get(content_type_name, MarkdownSource)

    def detect_content_type(self, file_path: str) -> Optional[str]:
        """Detect content type for a file using first-match detection."""
        for content_type_name, source in self.sources.items():
            if source.detect(file_path):
                return content_type_name
        return None

    def get_source(self, content_type_name: str) -> Optional[ContentSource]:
        """Get content source for a content type."""
        return self.sources.get(content_type_name)

    def get_collection_name(self, content_type_name: str) -> str:
        """Get collection name for a content type."""
        # For collections, the collection name is the same as the content type name
        if content_type_name in self.collections:
            return content_type_name

        # Legacy: check the collection mapping
        if content_type_name in self.collection_mapping:
            return self.collection_mapping[content_type_name]

        # Legacy: fallback to content type config
        if content_type_name in self.content_types:
            config = self.content_types[content_type_name]
            return getattr(config, "collection_name", f"{content_type_name}_docs")

        # Final fallback
        return f"{content_type_name}_docs"

    def chunk_content(
        self, content: str, file_path: str, content_type: str
    ) -> List[Chunk]:
        """Chunk content using the appropriate source."""
        source = self.get_source(content_type)
        if not source:
            raise ValueError(f"Unknown content type: {content_type}")

        return source.chunk_content(content, file_path)
