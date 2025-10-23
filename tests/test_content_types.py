"""
Tests for Holocron content type system.

Tests content type detection, chunking strategies, and content source implementations.
"""

import pytest

from holocron.content_types import (
    ApiSpecSource,
    Chunk,
    CodeSource,
    ContentSource,
    ContentTypeConfig,
    ContentTypeRegistry,
    ExternalDocsSource,
    MarkdownSource,
)


class TestChunk:
    """Test Chunk data structure."""

    def test_valid_chunk(self):
        """Test valid chunk creation."""
        chunk = Chunk(
            text="This is test content",
            metadata={"content_type": "markdown", "chunk_index": 0},
        )

        assert chunk.text == "This is test content"
        assert chunk.metadata == {"content_type": "markdown", "chunk_index": 0}

    def test_empty_text_raises_error(self):
        """Test empty text raises error."""
        with pytest.raises(ValueError, match="Chunk text cannot be empty"):
            Chunk(text="", metadata={"content_type": "markdown"})

    def test_invalid_metadata_raises_error(self):
        """Test invalid metadata raises error."""
        with pytest.raises(ValueError, match="Chunk metadata must be a dictionary"):
            Chunk(text="test", metadata="invalid")


class TestContentSource:
    """Test ContentSource abstract base class."""

    def test_abstract_methods(self):
        """Test that ContentSource cannot be instantiated directly."""
        config = ContentTypeConfig(
            name="Test",
            patterns=[r"\.test$"],
            chunk_size=1000,
            overlap=200,
            delimiters=["##"],
        )

        with pytest.raises(TypeError):
            ContentSource(config)

    def test_detect_method(self):
        """Test content type detection."""
        config = ContentTypeConfig(
            name="Test",
            patterns=[r"\.test$", r"\.spec$"],
            chunk_size=1000,
            overlap=200,
            delimiters=["##"],
        )

        # Create a concrete implementation for testing
        class TestSource(ContentSource):
            def chunk_content(self, content: str, file_path: str = "") -> list:
                return [Chunk(text=content, metadata={"test": True})]

        source = TestSource(config)

        # Test pattern matching
        assert source.detect("test.test") is True
        assert source.detect("test.spec") is True
        assert source.detect("test.txt") is False
        assert source.detect("docs/test.test") is True

    def test_extensions_detection(self):
        """Test extension-based detection."""
        config = ContentTypeConfig(
            name="Test",
            patterns=[r"\.test$"],
            extensions=[".test", ".spec"],
            chunk_size=1000,
            overlap=200,
            delimiters=["##"],
        )

        class TestSource(ContentSource):
            def chunk_content(self, content: str, file_path: str = "") -> list:
                return [Chunk(text=content, metadata={"test": True})]

        source = TestSource(config)

        # Test extension matching
        assert source.detect("test.test") is True
        assert source.detect("test.spec") is True
        assert source.detect("test.txt") is False


class TestMarkdownSource:
    """Test MarkdownSource implementation."""

    def test_markdown_chunking(self):
        """Test markdown content chunking."""
        config = ContentTypeConfig(
            name="Markdown",
            patterns=[r"\.md$"],
            chunk_size=1000,
            overlap=200,
            delimiters=["##"],
        )

        source = MarkdownSource(config)

        content = """# Project Overview

This is the main project documentation.

## Installation

To install the project, run:

```bash
pip install project
```

## Usage

Basic usage example:

```python
import project
project.hello()
```

## Configuration

Configure the project by setting environment variables.
"""

        chunks = source.chunk_content(content, "docs/README.md")

        assert len(chunks) > 0
        assert all(isinstance(chunk, Chunk) for chunk in chunks)

        # Check that chunks contain the expected content
        chunk_texts = [chunk.text for chunk in chunks]
        assert any("Installation" in text for text in chunk_texts)
        assert any("Usage" in text for text in chunk_texts)
        assert any("Configuration" in text for text in chunk_texts)

    def test_markdown_metadata_extraction(self):
        """Test markdown metadata extraction."""
        config = ContentTypeConfig(
            name="Markdown",
            patterns=[r"\.md$"],
            chunk_size=1000,
            overlap=200,
            delimiters=["##"],
        )

        source = MarkdownSource(config)

        content = """# Project Resource Deep-Dive

This is a comprehensive guide to the project resource.

## Installation

Installation instructions go here.

## Usage

Usage examples go here.
"""

        chunks = source.chunk_content(content, "docs/project.md")

        # Check metadata extraction
        for chunk in chunks:
            metadata = chunk.metadata
            assert "content_type" in metadata
            assert "chunk_index" in metadata
            assert "size" in metadata
            assert "file_path" in metadata
            assert "file_name" in metadata

            # Check for extracted metadata
            if "h1_title" in metadata:
                assert metadata["h1_title"] == "Project Resource Deep-Dive"
            if "resource_type" in metadata:
                assert metadata["resource_type"] == "project"

    def test_markdown_detection(self):
        """Test markdown file detection."""
        config = ContentTypeConfig(
            name="Markdown",
            patterns=[r"\.md$", r"\.rst$"],
            chunk_size=1000,
            overlap=200,
            delimiters=["##"],
        )

        source = MarkdownSource(config)

        assert source.detect("docs/README.md") is True
        assert source.detect("docs/README.rst") is True
        assert source.detect("src/main.py") is False
        assert source.detect("docs/README.txt") is False


class TestExternalDocsSource:
    """Test ExternalDocsSource implementation."""

    def test_external_docs_chunking(self):
        """Test external documentation chunking."""
        config = ContentTypeConfig(
            name="External Docs",
            patterns=[r"\.workspace/downloads/user-docs/.*\.md$"],
            chunk_size=2000,
            overlap=300,
            delimiters=["===", "---", "\n\n"],
        )

        source = ExternalDocsSource(config)

        content = """Getting Started
==============

This guide will help you get started with the API.

Authentication
--------------

To authenticate with the API, you need an API key.

API Endpoints
-------------

The API provides several endpoints for different operations.
"""

        chunks = source.chunk_content(
            content, ".workspace/downloads/user-docs/getting-started.md"
        )

        assert len(chunks) > 0
        assert all(isinstance(chunk, Chunk) for chunk in chunks)

        # Check that chunks contain the expected content
        chunk_texts = [chunk.text for chunk in chunks]
        assert any("Getting Started" in text for text in chunk_texts)
        assert any("Authentication" in text for text in chunk_texts)
        assert any("API Endpoints" in text for text in chunk_texts)

    def test_external_docs_detection(self):
        """Test external docs file detection."""
        config = ContentTypeConfig(
            name="External Docs",
            patterns=[r"\.workspace/downloads/user-docs/.*\.md$"],
            chunk_size=2000,
            overlap=300,
            delimiters=["===", "---"],
        )

        source = ExternalDocsSource(config)

        assert (
            source.detect(".workspace/downloads/user-docs/getting-started.md") is True
        )
        assert source.detect("docs/README.md") is False
        assert source.detect(".workspace/downloads/user-docs/api-reference.md") is True

    def test_underline_header_detection(self):
        """Test underline header detection."""
        config = ContentTypeConfig(
            name="External Docs",
            patterns=[r"\.workspace/downloads/user-docs/.*\.md$"],
            chunk_size=2000,
            overlap=300,
            delimiters=["===", "---"],
        )

        source = ExternalDocsSource(config)

        # Test underline detection
        assert source._is_underline("====") is True
        assert source._is_underline("----") is True
        assert source._is_underline("===") is True
        assert source._is_underline("---") is True
        assert source._is_underline("===") is True
        assert source._is_underline("---") is True
        assert source._is_underline("text") is False
        assert source._is_underline("") is False

    def test_skip_line_detection(self):
        """Test line skipping for HTML comments and breadcrumbs."""
        config = ContentTypeConfig(
            name="External Docs",
            patterns=[r"\.workspace/downloads/user-docs/.*\.md$"],
            chunk_size=2000,
            overlap=300,
            delimiters=["===", "---"],
        )

        source = ExternalDocsSource(config)

        # Test HTML comment skipping
        assert source._should_skip_line("<!-- This is a comment -->") is True
        assert source._should_skip_line("<!-- Source: https://example.com -->") is True

        # Test breadcrumb skipping
        assert source._should_skip_line("1. [Home](/)") is True
        assert source._should_skip_line("2. [API](/api)") is True
        assert source._should_skip_line("3. [Reference](/api/reference)") is True

        # Test normal content
        assert source._should_skip_line("This is normal content") is False
        assert source._should_skip_line("## Header") is False


class TestCodeSource:
    """Test CodeSource implementation."""

    def test_code_chunking(self):
        """Test source code chunking."""
        config = ContentTypeConfig(
            name="Code",
            patterns=[r"\.py$", r"\.js$"],
            chunk_size=2000,
            overlap=300,
            delimiters=["def ", "class "],
        )

        source = CodeSource(config)

        content = """#!/usr/bin/env python3
\"\"\"Test module for code chunking.\"\"\"

import os
import sys

class TestClass:
    \"\"\"Test class for demonstration.\"\"\"

    def __init__(self, name):
        self.name = name

    def test_method(self):
        \"\"\"Test method implementation.\"\"\"
        return f"Hello, {self.name}!"

def main():
    \"\"\"Main function.\"\"\"
    test = TestClass("World")
    print(test.test_method())

if __name__ == "__main__":
    main()
"""

        chunks = source.chunk_content(content, "src/test.py")

        assert len(chunks) > 0
        assert all(isinstance(chunk, Chunk) for chunk in chunks)

        # Check that chunks contain the expected content
        chunk_texts = [chunk.text for chunk in chunks]
        assert any("class TestClass" in text for text in chunk_texts)
        assert any("def main" in text for text in chunk_texts)

    def test_code_detection(self):
        """Test code file detection."""
        config = ContentTypeConfig(
            name="Code",
            patterns=[r"\.py$", r"\.js$", r"\.ts$"],
            chunk_size=2000,
            overlap=300,
            delimiters=["def ", "class "],
        )

        source = CodeSource(config)

        assert source.detect("src/main.py") is True
        assert source.detect("src/app.js") is True
        assert source.detect("src/app.ts") is True
        assert source.detect("docs/README.md") is False
        assert source.detect("src/main.go") is False


class TestApiSpecSource:
    """Test ApiSpecSource implementation."""

    def test_api_spec_chunking(self):
        """Test API specification chunking."""
        config = ContentTypeConfig(
            name="API Spec",
            patterns=[r"openapi.*\.json$", r"swagger.*\.json$"],
            chunk_size=2000,
            overlap=300,
            delimiters=['"paths":', '"components":', '"definitions":'],
        )

        source = ApiSpecSource(config)

        content = """{
  "openapi": "3.0.0",
  "info": {
    "title": "Test API",
    "version": "1.0.0"
  },
  "paths": {
    "/users": {
      "get": {
        "summary": "Get users",
        "responses": {
          "200": {
            "description": "Success"
          }
        }
      }
    }
  },
  "components": {
    "schemas": {
      "User": {
        "type": "object",
        "properties": {
          "id": {"type": "integer"},
          "name": {"type": "string"}
        }
      }
    }
  }
}"""

        chunks = source.chunk_content(content, "openapi.json")

        assert len(chunks) > 0
        assert all(isinstance(chunk, Chunk) for chunk in chunks)

        # Check that chunks contain the expected content
        chunk_texts = [chunk.text for chunk in chunks]
        assert any('"paths"' in text for text in chunk_texts)
        assert any('"components"' in text for text in chunk_texts)

    def test_api_spec_detection(self):
        """Test API spec file detection."""
        config = ContentTypeConfig(
            name="API Spec",
            patterns=[r"openapi.*\.json$", r"swagger.*\.json$", r"\.yaml$", r"\.yml$"],
            chunk_size=2000,
            overlap=300,
            delimiters=['"paths":', '"components":'],
        )

        source = ApiSpecSource(config)

        assert source.detect("openapi.json") is True
        assert source.detect("swagger.json") is True
        assert source.detect("api.yaml") is True
        assert source.detect("api.yml") is True
        assert source.detect("docs/README.md") is False

    def test_generic_chunking_fallback(self):
        """Test generic chunking fallback for non-JSON content."""
        config = ContentTypeConfig(
            name="API Spec",
            patterns=[r"\.yaml$"],
            chunk_size=2000,
            overlap=300,
            delimiters=['"paths":', '"components":'],
        )

        source = ApiSpecSource(config)

        # Test with non-JSON content
        content = """openapi: 3.0.0
info:
  title: Test API
  version: 1.0.0
paths:
  /users:
    get:
      summary: Get users
      responses:
        '200':
          description: Success
"""

        chunks = source.chunk_content(content, "api.yaml")

        assert len(chunks) > 0
        assert all(isinstance(chunk, Chunk) for chunk in chunks)


class TestContentTypeRegistry:
    """Test ContentTypeRegistry implementation."""

    def test_registry_initialization(self):
        """Test registry initialization with content types."""
        content_types = {
            "markdown": ContentTypeConfig(
                name="Markdown",
                patterns=[r"\.md$"],
                chunk_size=1000,
                overlap=200,
                delimiters=["##"],
            ),
            "code": ContentTypeConfig(
                name="Code",
                patterns=[r"\.py$"],
                chunk_size=2000,
                overlap=300,
                delimiters=["def ", "class "],
            ),
        }

        registry = ContentTypeRegistry(content_types)

        assert len(registry.sources) == 2
        assert "markdown" in registry.sources
        assert "code" in registry.sources
        assert isinstance(registry.sources["markdown"], MarkdownSource)
        assert isinstance(registry.sources["code"], CodeSource)

    def test_content_type_detection(self):
        """Test content type detection."""
        content_types = {
            "markdown": ContentTypeConfig(
                name="Markdown",
                patterns=[r"\.md$"],
                chunk_size=1000,
                overlap=200,
                delimiters=["##"],
            ),
            "code": ContentTypeConfig(
                name="Code",
                patterns=[r"\.py$"],
                chunk_size=2000,
                overlap=300,
                delimiters=["def ", "class "],
            ),
        }

        registry = ContentTypeRegistry(content_types)

        assert registry.detect_content_type("docs/README.md") == "markdown"
        assert registry.detect_content_type("src/main.py") == "code"
        assert registry.detect_content_type("docs/README.txt") is None

    def test_content_chunking(self):
        """Test content chunking through registry."""
        content_types = {
            "markdown": ContentTypeConfig(
                name="Markdown",
                patterns=[r"\.md$"],
                chunk_size=1000,
                overlap=200,
                delimiters=["##"],
            )
        }

        registry = ContentTypeRegistry(content_types)

        content = """# Test

This is a test document.

## Section 1

Content for section 1.

## Section 2

Content for section 2.
"""

        chunks = registry.chunk_content(content, "test.md", "markdown")

        assert len(chunks) > 0
        assert all(isinstance(chunk, Chunk) for chunk in chunks)

    def test_unknown_content_type(self):
        """Test handling of unknown content type."""
        content_types = {
            "markdown": ContentTypeConfig(
                name="Markdown",
                patterns=[r"\.md$"],
                chunk_size=1000,
                overlap=200,
                delimiters=["##"],
            )
        }

        registry = ContentTypeRegistry(content_types)

        with pytest.raises(ValueError, match="Unknown content type"):
            registry.chunk_content("content", "test.txt", "unknown")

    def test_get_source(self):
        """Test getting content source."""
        content_types = {
            "markdown": ContentTypeConfig(
                name="Markdown",
                patterns=[r"\.md$"],
                chunk_size=1000,
                overlap=200,
                delimiters=["##"],
            )
        }

        registry = ContentTypeRegistry(content_types)

        source = registry.get_source("markdown")
        assert source is not None
        assert isinstance(source, MarkdownSource)

        unknown_source = registry.get_source("unknown")
        assert unknown_source is None
