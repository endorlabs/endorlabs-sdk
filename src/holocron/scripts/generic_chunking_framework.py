#!/usr/bin/env python3
"""
Generic Chunking Framework for Holocron Optimization

Provides abstract base classes and implementations for different chunking strategies
across content types (Markdown, Code, External Docs, API Specs).
"""

import json
import re
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Dict, List, Tuple

import numpy as np


@dataclass
class ChunkingMetrics:
    """Metrics for evaluating chunking strategies."""

    chunk_count: int
    avg_size: float
    max_size: float
    min_size: float
    size_std: float
    searchable_ratio: float  # Ratio of chunks < 100KB
    size_distribution_score: float  # How well distributed sizes are
    total_size: int


class ChunkingStrategy(ABC):
    """Abstract base class for chunking strategies."""

    def __init__(self, name: str, **kwargs):
        self.name = name
        self.parameters = kwargs

    @abstractmethod
    def chunk(self, content: str) -> List[Dict[str, Any]]:
        """Chunk the content and return list of chunks with metadata."""
        pass

    def evaluate(self, content: str) -> ChunkingMetrics:
        """Evaluate this strategy on the given content."""
        try:
            chunks = self.chunk(content)

            if not chunks:
                return ChunkingMetrics(0, 0, 0, 0, 0, 0, 0, 0)

            chunk_sizes = [chunk["size"] for chunk in chunks]
            total_size = sum(chunk_sizes)
            avg_size = np.mean(chunk_sizes)
            max_size = np.max(chunk_sizes)
            min_size = np.min(chunk_sizes)
            size_std = np.std(chunk_sizes)

            # Calculate searchable ratio (chunks < 100KB)
            searchable_chunks = sum(1 for size in chunk_sizes if size < 100000)
            searchable_ratio = searchable_chunks / len(chunks) if chunks else 0

            # Calculate size distribution score (lower is better)
            if min_size > 0:
                size_ratio = max_size / min_size
                size_distribution_score = 1.0 / (1.0 + size_ratio)  # Higher is better
            else:
                size_distribution_score = 0.0

            return ChunkingMetrics(
                chunk_count=len(chunks),
                avg_size=avg_size,
                max_size=max_size,
                min_size=min_size,
                size_std=size_std,
                searchable_ratio=searchable_ratio,
                size_distribution_score=size_distribution_score,
                total_size=total_size,
            )

        except Exception as e:
            print(f"Error evaluating strategy {self.name}: {e}")
            return ChunkingMetrics(0, 0, 0, 0, 0, 0, 0, 0)


class MarkdownChunkingStrategy(ChunkingStrategy):
    """Chunking strategies for Markdown content."""

    def __init__(self, strategy_type: str, **kwargs):
        super().__init__(f"Markdown-{strategy_type}", **kwargs)
        self.strategy_type = strategy_type

    def chunk(self, content: str) -> List[Dict[str, Any]]:
        """Chunk markdown content based on strategy type."""
        if self.strategy_type == "h1_delimiter":
            return self._chunk_by_h1(content)
        elif self.strategy_type == "h2_delimiter":
            return self._chunk_by_h2(content)
        elif self.strategy_type == "h3_delimiter":
            return self._chunk_by_h3(content)
        elif self.strategy_type == "size_based":
            return self._chunk_by_size(content)
        elif self.strategy_type == "hybrid_header":
            return self._chunk_hybrid_header(content)
        elif self.strategy_type == "smart_section":
            return self._chunk_smart_section(content)
        else:
            return self._chunk_by_h2(content)  # Default

    def _chunk_by_h1(self, content: str) -> List[Dict[str, Any]]:
        """Split at H1 headers (# )."""
        chunks = []
        lines = content.split("\n")
        current_chunk = []

        for line in lines:
            if line.strip().startswith("# ") and not line.strip().startswith("## "):
                if current_chunk:
                    chunk_text = "\n".join(current_chunk)
                    chunks.append(
                        {
                            "text": chunk_text,
                            "size": len(chunk_text),
                            "type": "h1_section",
                        }
                    )
                current_chunk = [line]
            else:
                current_chunk.append(line)

        if current_chunk:
            chunk_text = "\n".join(current_chunk)
            chunks.append(
                {"text": chunk_text, "size": len(chunk_text), "type": "h1_section"}
            )

        return chunks

    def _chunk_by_h2(self, content: str) -> List[Dict[str, Any]]:
        """Split at H2 headers (## )."""
        chunks = []
        lines = content.split("\n")
        current_chunk = []

        for line in lines:
            if line.strip().startswith("## ") and not line.strip().startswith("### "):
                if current_chunk:
                    chunk_text = "\n".join(current_chunk)
                    chunks.append(
                        {
                            "text": chunk_text,
                            "size": len(chunk_text),
                            "type": "h2_section",
                        }
                    )
                current_chunk = [line]
            else:
                current_chunk.append(line)

        if current_chunk:
            chunk_text = "\n".join(current_chunk)
            chunks.append(
                {"text": chunk_text, "size": len(chunk_text), "type": "h2_section"}
            )

        return chunks

    def _chunk_by_h3(self, content: str) -> List[Dict[str, Any]]:
        """Split at H3 headers (### )."""
        chunks = []
        lines = content.split("\n")
        current_chunk = []

        for line in lines:
            if line.strip().startswith("### "):
                if current_chunk:
                    chunk_text = "\n".join(current_chunk)
                    chunks.append(
                        {
                            "text": chunk_text,
                            "size": len(chunk_text),
                            "type": "h3_section",
                        }
                    )
                current_chunk = [line]
            else:
                current_chunk.append(line)

        if current_chunk:
            chunk_text = "\n".join(current_chunk)
            chunks.append(
                {"text": chunk_text, "size": len(chunk_text), "type": "h3_section"}
            )

        return chunks

    def _chunk_by_size(self, content: str) -> List[Dict[str, Any]]:
        """Split by fixed size with overlap."""
        chunk_size = self.parameters.get("chunk_size", 2000)
        overlap = self.parameters.get("overlap", 200)

        chunks = []
        words = content.split()

        for i in range(0, len(words), chunk_size - overlap):
            chunk_words = words[i : i + chunk_size]
            chunk_text = " ".join(chunk_words)
            chunks.append(
                {"text": chunk_text, "size": len(chunk_text), "type": "size_based"}
            )

        return chunks

    def _chunk_hybrid_header(self, content: str) -> List[Dict[str, Any]]:
        """H2 headers with size limit fallback."""
        max_chunk_size = self.parameters.get("max_chunk_size", 5000)
        chunks = []
        lines = content.split("\n")
        current_chunk = []
        current_size = 0

        for line in lines:
            # Check for H2 header
            if line.strip().startswith("## ") and not line.strip().startswith("### "):
                if current_chunk:
                    chunk_text = "\n".join(current_chunk)
                    chunks.append(
                        {
                            "text": chunk_text,
                            "size": len(chunk_text),
                            "type": "hybrid_section",
                        }
                    )
                current_chunk = [line]
                current_size = len(line)
            else:
                current_chunk.append(line)
                current_size += len(line) + 1

                # Size limit fallback
                if current_size > max_chunk_size:
                    chunk_text = "\n".join(current_chunk)
                    chunks.append(
                        {
                            "text": chunk_text,
                            "size": len(chunk_text),
                            "type": "hybrid_section",
                        }
                    )
                    current_chunk = []
                    current_size = 0

        if current_chunk:
            chunk_text = "\n".join(current_chunk)
            chunks.append(
                {"text": chunk_text, "size": len(chunk_text), "type": "hybrid_section"}
            )

        return chunks

    def _chunk_smart_section(self, content: str) -> List[Dict[str, Any]]:
        """Smart sectioning based on content patterns."""
        chunks = []
        lines = content.split("\n")
        current_chunk = []
        current_size = 0
        max_size = self.parameters.get("max_chunk_size", 4000)

        for line in lines:
            # Check for any header level
            if re.match(r"^#{1,6} ", line.strip()):
                if current_chunk:
                    chunk_text = "\n".join(current_chunk)
                    chunks.append(
                        {
                            "text": chunk_text,
                            "size": len(chunk_text),
                            "type": "smart_section",
                        }
                    )
                current_chunk = [line]
                current_size = len(line)
            else:
                current_chunk.append(line)
                current_size += len(line) + 1

                # Size limit with paragraph boundary preference
                if current_size > max_size and line.strip() == "":
                    chunk_text = "\n".join(current_chunk)
                    chunks.append(
                        {
                            "text": chunk_text,
                            "size": len(chunk_text),
                            "type": "smart_section",
                        }
                    )
                    current_chunk = []
                    current_size = 0

        if current_chunk:
            chunk_text = "\n".join(current_chunk)
            chunks.append(
                {"text": chunk_text, "size": len(chunk_text), "type": "smart_section"}
            )

        return chunks


class CodeChunkingStrategy(ChunkingStrategy):
    """Chunking strategies for code content."""

    def __init__(self, strategy_type: str, **kwargs):
        super().__init__(f"Code-{strategy_type}", **kwargs)
        self.strategy_type = strategy_type

    def chunk(self, content: str) -> List[Dict[str, Any]]:
        """Chunk code content based on strategy type."""
        if self.strategy_type == "function_based":
            return self._chunk_by_functions(content)
        elif self.strategy_type == "class_based":
            return self._chunk_by_classes(content)
        elif self.strategy_type == "both":
            return self._chunk_by_both(content)
        elif self.strategy_type == "size_with_context":
            return self._chunk_size_with_context(content)
        elif self.strategy_type == "hybrid":
            return self._chunk_hybrid_code(content)
        else:
            return self._chunk_by_functions(content)  # Default

    def _chunk_by_functions(self, content: str) -> List[Dict[str, Any]]:
        """Split at function definitions."""
        chunks = []
        lines = content.split("\n")
        current_chunk = []

        for line in lines:
            if re.match(r"^\s*def\s+\w+", line):
                if current_chunk:
                    chunk_text = "\n".join(current_chunk)
                    chunks.append(
                        {
                            "text": chunk_text,
                            "size": len(chunk_text),
                            "type": "function",
                        }
                    )
                current_chunk = [line]
            else:
                current_chunk.append(line)

        if current_chunk:
            chunk_text = "\n".join(current_chunk)
            chunks.append(
                {"text": chunk_text, "size": len(chunk_text), "type": "function"}
            )

        return chunks

    def _chunk_by_classes(self, content: str) -> List[Dict[str, Any]]:
        """Split at class definitions."""
        chunks = []
        lines = content.split("\n")
        current_chunk = []

        for line in lines:
            if re.match(r"^\s*class\s+\w+", line):
                if current_chunk:
                    chunk_text = "\n".join(current_chunk)
                    chunks.append(
                        {"text": chunk_text, "size": len(chunk_text), "type": "class"}
                    )
                current_chunk = [line]
            else:
                current_chunk.append(line)

        if current_chunk:
            chunk_text = "\n".join(current_chunk)
            chunks.append(
                {"text": chunk_text, "size": len(chunk_text), "type": "class"}
            )

        return chunks

    def _chunk_by_both(self, content: str) -> List[Dict[str, Any]]:
        """Split at both function and class definitions."""
        chunks = []
        lines = content.split("\n")
        current_chunk = []

        for line in lines:
            if re.match(r"^\s*(def|class)\s+\w+", line):
                if current_chunk:
                    chunk_text = "\n".join(current_chunk)
                    chunks.append(
                        {
                            "text": chunk_text,
                            "size": len(chunk_text),
                            "type": "code_block",
                        }
                    )
                current_chunk = [line]
            else:
                current_chunk.append(line)

        if current_chunk:
            chunk_text = "\n".join(current_chunk)
            chunks.append(
                {"text": chunk_text, "size": len(chunk_text), "type": "code_block"}
            )

        return chunks

    def _chunk_size_with_context(self, content: str) -> List[Dict[str, Any]]:
        """Size-based chunking with context preservation."""
        chunk_size = self.parameters.get("chunk_size", 2000)
        overlap = self.parameters.get("overlap", 200)

        chunks = []
        words = content.split()

        for i in range(0, len(words), chunk_size - overlap):
            chunk_words = words[i : i + chunk_size]
            chunk_text = " ".join(chunk_words)
            chunks.append(
                {
                    "text": chunk_text,
                    "size": len(chunk_text),
                    "type": "size_with_context",
                }
            )

        return chunks

    def _chunk_hybrid_code(self, content: str) -> List[Dict[str, Any]]:
        """Logical boundaries with size limits."""
        max_chunk_size = self.parameters.get("max_chunk_size", 3000)
        chunks = []
        lines = content.split("\n")
        current_chunk = []
        current_size = 0

        for line in lines:
            # Check for logical boundaries
            if re.match(r"^\s*(def|class)\s+\w+", line):
                if current_chunk:
                    chunk_text = "\n".join(current_chunk)
                    chunks.append(
                        {
                            "text": chunk_text,
                            "size": len(chunk_text),
                            "type": "hybrid_code",
                        }
                    )
                current_chunk = [line]
                current_size = len(line)
            else:
                current_chunk.append(line)
                current_size += len(line) + 1

                # Size limit fallback
                if current_size > max_chunk_size:
                    chunk_text = "\n".join(current_chunk)
                    chunks.append(
                        {
                            "text": chunk_text,
                            "size": len(chunk_text),
                            "type": "hybrid_code",
                        }
                    )
                    current_chunk = []
                    current_size = 0

        if current_chunk:
            chunk_text = "\n".join(current_chunk)
            chunks.append(
                {"text": chunk_text, "size": len(chunk_text), "type": "hybrid_code"}
            )

        return chunks


class ExternalDocsChunkingStrategy(ChunkingStrategy):
    """Chunking strategies for external documentation."""

    def __init__(self, strategy_type: str, **kwargs):
        super().__init__(f"ExternalDocs-{strategy_type}", **kwargs)
        self.strategy_type = strategy_type

    def chunk(self, content: str) -> List[Dict[str, Any]]:
        """Chunk external docs content based on strategy type."""
        if self.strategy_type == "underline_headers":
            return self._chunk_by_underline_headers(content)
        elif self.strategy_type == "paragraphs":
            return self._chunk_by_paragraphs(content)
        elif self.strategy_type == "size_large":
            return self._chunk_size_large(content)
        elif self.strategy_type == "hybrid_docs":
            return self._chunk_hybrid_docs(content)
        else:
            return self._chunk_by_underline_headers(content)  # Default

    def _chunk_by_underline_headers(self, content: str) -> List[Dict[str, Any]]:
        """Split at underline headers (===, ---)."""
        chunks = []
        lines = content.split("\n")
        current_chunk = []

        for i, line in enumerate(lines):
            # Check for underline headers (look ahead)
            if i < len(lines) - 1 and re.match(r"^[=\-]+$", lines[i + 1]):
                if current_chunk:
                    chunk_text = "\n".join(current_chunk)
                    chunks.append(
                        {
                            "text": chunk_text,
                            "size": len(chunk_text),
                            "type": "underline_header",
                        }
                    )
                current_chunk = [line]
            else:
                current_chunk.append(line)

        if current_chunk:
            chunk_text = "\n".join(current_chunk)
            chunks.append(
                {
                    "text": chunk_text,
                    "size": len(chunk_text),
                    "type": "underline_header",
                }
            )

        return chunks

    def _chunk_by_paragraphs(self, content: str) -> List[Dict[str, Any]]:
        """Split at double newlines."""
        chunks = []
        paragraphs = content.split("\n\n")

        for paragraph in paragraphs:
            if paragraph.strip():
                chunks.append(
                    {
                        "text": paragraph.strip(),
                        "size": len(paragraph.strip()),
                        "type": "paragraph",
                    }
                )

        return chunks

    def _chunk_size_large(self, content: str) -> List[Dict[str, Any]]:
        """Large chunks for external docs."""
        chunk_size = self.parameters.get("chunk_size", 6000)
        overlap = self.parameters.get("overlap", 500)

        chunks = []
        words = content.split()

        for i in range(0, len(words), chunk_size - overlap):
            chunk_words = words[i : i + chunk_size]
            chunk_text = " ".join(chunk_words)
            chunks.append(
                {"text": chunk_text, "size": len(chunk_text), "type": "size_large"}
            )

        return chunks

    def _chunk_hybrid_docs(self, content: str) -> List[Dict[str, Any]]:
        """Headers with size limits for docs."""
        max_chunk_size = self.parameters.get("max_chunk_size", 8000)
        chunks = []
        lines = content.split("\n")
        current_chunk = []
        current_size = 0

        for i, line in enumerate(lines):
            # Check for underline headers
            if i < len(lines) - 1 and re.match(r"^[=\-]+$", lines[i + 1]):
                if current_chunk:
                    chunk_text = "\n".join(current_chunk)
                    chunks.append(
                        {
                            "text": chunk_text,
                            "size": len(chunk_text),
                            "type": "hybrid_docs",
                        }
                    )
                current_chunk = [line]
                current_size = len(line)
            else:
                current_chunk.append(line)
                current_size += len(line) + 1

                # Size limit fallback
                if current_size > max_chunk_size:
                    chunk_text = "\n".join(current_chunk)
                    chunks.append(
                        {
                            "text": chunk_text,
                            "size": len(chunk_text),
                            "type": "hybrid_docs",
                        }
                    )
                    current_chunk = []
                    current_size = 0

        if current_chunk:
            chunk_text = "\n".join(current_chunk)
            chunks.append(
                {"text": chunk_text, "size": len(chunk_text), "type": "hybrid_docs"}
            )

        return chunks


class ApiSpecChunkingStrategy(ChunkingStrategy):
    """Chunking strategies for API specifications."""

    def __init__(self, strategy_type: str, **kwargs):
        super().__init__(f"ApiSpec-{strategy_type}", **kwargs)
        self.strategy_type = strategy_type

    def chunk(self, content: str) -> List[Dict[str, Any]]:
        """Chunk API spec content based on strategy type."""
        try:
            data = json.loads(content)
        except Exception:
            return []

        if self.strategy_type == "section_based":
            return self._chunk_by_sections(data)
        elif self.strategy_type == "endpoint_based":
            return self._chunk_by_endpoints(data)
        elif self.strategy_type == "service_based":
            return self._chunk_by_services(data)
        elif self.strategy_type == "resource_based":
            return self._chunk_by_resources(data)
        elif self.strategy_type == "hybrid":
            return self._chunk_hybrid_api(data)
        else:
            return self._chunk_by_sections(data)  # Default

    def _chunk_by_sections(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Split by top-level sections."""
        chunks = []
        for section_name, section_content in data.items():
            if isinstance(section_content, dict):
                chunk_text = json.dumps({section_name: section_content}, indent=2)
                chunks.append(
                    {
                        "text": chunk_text,
                        "size": len(chunk_text),
                        "type": "section",
                        "section": section_name,
                    }
                )
        return chunks

    def _chunk_by_endpoints(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Split by individual API endpoints."""
        chunks = []
        paths = data.get("paths", {})

        for path, path_item in paths.items():
            for method, operation in path_item.items():
                if method in ["get", "post", "put", "patch", "delete"]:
                    operation_data = {
                        "path": path,
                        "method": method.upper(),
                        "operation": operation,
                    }
                    chunk_text = json.dumps(operation_data, indent=2)
                    chunks.append(
                        {
                            "text": chunk_text,
                            "size": len(chunk_text),
                            "type": "endpoint",
                            "path": path,
                            "method": method.upper(),
                            "operation_id": operation.get("operationId", ""),
                        }
                    )

        return chunks

    def _chunk_by_services(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Split by service groups using tags."""
        chunks = []
        paths = data.get("paths", {})
        service_operations = defaultdict(list)

        for path, path_item in paths.items():
            for method, operation in path_item.items():
                if method in ["get", "post", "put", "patch", "delete"]:
                    service_tags = operation.get("tags", [])
                    for tag in service_tags:
                        service_operations[tag].append(
                            {
                                "path": path,
                                "method": method.upper(),
                                "operation": operation,
                            }
                        )

        for service, operations in service_operations.items():
            service_data = {"service": service, "operations": operations}
            chunk_text = json.dumps(service_data, indent=2)
            chunks.append(
                {
                    "text": chunk_text,
                    "size": len(chunk_text),
                    "type": "service",
                    "service": service,
                    "operation_count": len(operations),
                }
            )

        return chunks

    def _chunk_by_resources(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Split by resource type extracted from paths."""
        chunks = []
        paths = data.get("paths", {})
        resource_operations = defaultdict(list)

        for path, path_item in paths.items():
            # Extract resource name from path
            resource_match = re.search(
                r"/v1/namespaces/\{tenant_meta\.namespace\}/([^/]+)", path
            )
            if not resource_match:
                resource_match = re.search(
                    r"/v1/namespaces/\{object\.tenant_meta\.namespace\}/([^/]+)", path
                )

            if resource_match:
                resource = resource_match.group(1)

                for method, operation in path_item.items():
                    if method in ["get", "post", "put", "patch", "delete"]:
                        resource_operations[resource].append(
                            {
                                "path": path,
                                "method": method.upper(),
                                "operation": operation,
                            }
                        )

        for resource, operations in resource_operations.items():
            resource_data = {"resource": resource, "operations": operations}
            chunk_text = json.dumps(resource_data, indent=2)
            chunks.append(
                {
                    "text": chunk_text,
                    "size": len(chunk_text),
                    "type": "resource",
                    "resource": resource,
                    "operation_count": len(operations),
                }
            )

        return chunks

    def _chunk_hybrid_api(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Hybrid approach: service-based with size limits."""
        max_chunk_size = self.parameters.get("max_chunk_size", 50000)
        chunks = []
        paths = data.get("paths", {})
        service_operations = defaultdict(list)

        for path, path_item in paths.items():
            for method, operation in path_item.items():
                if method in ["get", "post", "put", "patch", "delete"]:
                    service_tags = operation.get("tags", [])
                    for tag in service_tags:
                        service_operations[tag].append(
                            {
                                "path": path,
                                "method": method.upper(),
                                "operation": operation,
                            }
                        )

        for service, operations in service_operations.items():
            service_data = {"service": service, "operations": operations}
            chunk_text = json.dumps(service_data, indent=2)

            if len(chunk_text) <= max_chunk_size:
                chunks.append(
                    {
                        "text": chunk_text,
                        "size": len(chunk_text),
                        "type": "service",
                        "service": service,
                        "operation_count": len(operations),
                    }
                )
            else:
                # Split into multiple chunks
                chunk_size = len(operations) // 2
                for i in range(0, len(operations), chunk_size):
                    chunk_operations = operations[i : i + chunk_size]
                    chunk_data = {
                        "service": service,
                        "operations": chunk_operations,
                        "chunk_part": f"{i // chunk_size + 1}",
                    }
                    chunk_text = json.dumps(chunk_data, indent=2)
                    chunks.append(
                        {
                            "text": chunk_text,
                            "size": len(chunk_text),
                            "type": "service_chunk",
                            "service": service,
                            "operation_count": len(chunk_operations),
                        }
                    )

        return chunks


class ChunkingStrategyFactory:
    """Factory for creating chunking strategies by content type."""

    @staticmethod
    def create_strategy(
        content_type: str, strategy_type: str, **kwargs
    ) -> ChunkingStrategy:
        """Create a chunking strategy for the given content type."""
        if content_type == "markdown":
            return MarkdownChunkingStrategy(strategy_type, **kwargs)
        elif content_type == "code":
            return CodeChunkingStrategy(strategy_type, **kwargs)
        elif content_type == "external_docs":
            return ExternalDocsChunkingStrategy(strategy_type, **kwargs)
        elif content_type == "api_spec":
            return ApiSpecChunkingStrategy(strategy_type, **kwargs)
        else:
            raise ValueError(f"Unknown content type: {content_type}")

    @staticmethod
    def get_available_strategies(content_type: str) -> List[str]:
        """Get available strategy types for a content type."""
        strategies = {
            "markdown": [
                "h1_delimiter",
                "h2_delimiter",
                "h3_delimiter",
                "size_based",
                "hybrid_header",
                "smart_section",
            ],
            "code": [
                "function_based",
                "class_based",
                "both",
                "size_with_context",
                "hybrid",
            ],
            "external_docs": [
                "underline_headers",
                "paragraphs",
                "size_large",
                "hybrid_docs",
            ],
            "api_spec": [
                "section_based",
                "endpoint_based",
                "service_based",
                "resource_based",
                "hybrid",
            ],
        }
        return strategies.get(content_type, [])

    @staticmethod
    def get_parameter_ranges(
        content_type: str, strategy_type: str
    ) -> Dict[str, Tuple[int, int]]:
        """Get parameter ranges for optimization."""
        ranges = {
            "markdown": {
                "chunk_size": (1000, 8000),
                "max_chunk_size": (2000, 10000),
                "overlap": (100, 1000),
            },
            "code": {
                "chunk_size": (1000, 5000),
                "max_chunk_size": (2000, 8000),
                "overlap": (100, 800),
            },
            "external_docs": {
                "chunk_size": (3000, 10000),
                "max_chunk_size": (5000, 15000),
                "overlap": (200, 1500),
            },
            "api_spec": {"max_chunk_size": (10000, 100000), "overlap": (500, 5000)},
        }
        return ranges.get(content_type, {})
