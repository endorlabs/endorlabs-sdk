#!/usr/bin/env python3
"""
Simplified tests for core chunking functionality.

Tests essential chunking strategies without over-engineering.
These tests are marked as local-only since they test functionality
that is already validated by scripts/analyze_documentation_chunks.py in CI.
"""

import pytest

from holocron.scripts.generic_chunking_framework import (
    ChunkingMetrics,
    ChunkingStrategyFactory,
    CodeChunkingStrategy,
    MarkdownChunkingStrategy,
)


@pytest.mark.local
class TestChunkingStrategy:
    """Test base chunking strategy functionality."""

    def test_strategy_initialization(self):
        """Test strategy initialization with parameters."""
        strategy = MarkdownChunkingStrategy(
            "h2_delimiter", chunk_size=2000, overlap=200
        )
        assert strategy.name == "Markdown-h2_delimiter"
        assert strategy.parameters["chunk_size"] == 2000
        assert strategy.parameters["overlap"] == 200

    def test_strategy_evaluation(self):
        """Test strategy evaluation returns metrics."""
        strategy = MarkdownChunkingStrategy("h2_delimiter")
        content = """# Title

## Section 1
Content here.

## Section 2
More content."""

        metrics = strategy.evaluate(content)
        assert isinstance(metrics, ChunkingMetrics)
        assert metrics.chunk_count > 0
        assert metrics.avg_size > 0


@pytest.mark.local
class TestMarkdownChunkingStrategy:
    """Test markdown chunking strategies."""

    def test_h2_delimiter_chunking(self):
        """Test H2 delimiter chunking."""
        strategy = MarkdownChunkingStrategy("h2_delimiter")
        content = """# Title

## Section 1
Content here.

## Section 2
More content."""

        chunks = strategy.chunk(content)
        assert len(chunks) >= 2
        assert all(chunk["type"] == "h2_section" for chunk in chunks)

    def test_size_based_chunking(self):
        """Test size-based chunking."""
        strategy = MarkdownChunkingStrategy("size_based", chunk_size=50, overlap=10)
        content = "This is a test content that should be chunked by size."

        chunks = strategy.chunk(content)
        assert len(chunks) > 0
        assert all(chunk["type"] == "size_based" for chunk in chunks)


class TestCodeChunkingStrategy:
    """Test code chunking strategies."""

    def test_function_based_chunking(self):
        """Test function-based chunking."""
        strategy = CodeChunkingStrategy("function_based")
        content = """def function1():
    return "test"

def function2():
    return "another test"
"""

        chunks = strategy.chunk(content)
        assert len(chunks) >= 2
        assert all(chunk["type"] == "function" for chunk in chunks)


class TestChunkingStrategyFactory:
    """Test chunking strategy factory."""

    def test_create_markdown_strategy(self):
        """Test creating markdown strategy."""
        strategy = ChunkingStrategyFactory.create_strategy("markdown", "h2_delimiter")
        assert isinstance(strategy, MarkdownChunkingStrategy)
        assert strategy.name == "Markdown-h2_delimiter"

    def test_create_code_strategy(self):
        """Test creating code strategy."""
        strategy = ChunkingStrategyFactory.create_strategy("code", "function_based")
        assert isinstance(strategy, CodeChunkingStrategy)
        assert strategy.name == "Code-function_based"

    def test_get_available_strategies(self):
        """Test getting available strategies."""
        markdown_strategies = ChunkingStrategyFactory.get_available_strategies(
            "markdown"
        )
        code_strategies = ChunkingStrategyFactory.get_available_strategies("code")

        assert "h2_delimiter" in markdown_strategies
        assert "size_based" in markdown_strategies
        assert "function_based" in code_strategies
        assert "class_based" in code_strategies


class TestIntegration:
    """Test integration scenarios."""

    def test_markdown_optimization_workflow(self):
        """Test basic markdown optimization workflow."""
        strategy = MarkdownChunkingStrategy("h2_delimiter")
        content = """# Main Title

## Section 1
This is the first section with some content.

## Section 2
This is the second section with more content.

## Section 3
This is the third section with additional content."""

        # Test chunking
        chunks = strategy.chunk(content)
        assert len(chunks) >= 3

        # Test evaluation
        metrics = strategy.evaluate(content)
        assert metrics.chunk_count >= 3
        assert metrics.avg_size > 0

    def test_code_optimization_workflow(self):
        """Test basic code optimization workflow."""
        strategy = CodeChunkingStrategy("function_based")
        content = """def main():
    return "hello"

def helper():
    return "world"

def another():
    return "test"
"""

        # Test chunking
        chunks = strategy.chunk(content)
        assert len(chunks) >= 3

        # Test evaluation
        metrics = strategy.evaluate(content)
        assert metrics.chunk_count >= 3
        assert metrics.avg_size > 0
