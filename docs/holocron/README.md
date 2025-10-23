# Holocron Knowledge Base System

> **AI-Powered Documentation Search and Retrieval for Endor Cockpit**

## 🚨 Essential Context

- **Holocron** is semantic search over Endor Cockpit documentation, source code, and external resources
- **Required**: `OPENAI_API_KEY` environment variable for vector embeddings
- **Quick start**: `uv run python -m holocron init` then `uv run python -m holocron query "your question"`
- **Full details**: [Configuration](#configuration) | [Architecture](#architecture) | [Troubleshooting](#troubleshooting)

## Quick Reference

### Installation & Setup

```bash
# Install with holocron dependencies
uv pip install -e '.[holocron]'

# Set required environment variables
export OPENAI_API_KEY="your-openai-api-key"

# Initialize workspace and knowledge base
uv run python -m holocron init

# Query the knowledge base
uv run python -m holocron query "How do I create a namespace?"
```

### Common Commands

```bash
# Sync after documentation updates
uv run python -m holocron sync

# Show configuration
uv run python -m holocron config show

# Validate system health
python scripts/validate_holocron.py
```

### Programmatic Usage

```python
from holocron import query_holocron

# Simple query
results = query_holocron("How do I create a namespace?")
for result in results["results"]:
    print(f"Score: {result['similarity_score']:.3f}")
    print(f"Content: {result['content'][:100]}...")
```

### Content Types

| Type | Description | Chunking Strategy |
|------|-------------|-------------------|
| `markdown` | Internal documentation | Header-based sections |
| `external_docs` | External user docs | Underline header detection |
| `code` | Source code files | Function/class boundaries |
| `api_spec` | API specifications | Endpoint-based splitting |

## Configuration

Holocron uses `pyproject.toml` for all configuration settings. The system supports:

- **Environment variable interpolation** in configuration values
- **Content-type specific chunking** strategies
- **External documentation** automatic downloads
- **Cross-platform path handling** with normalization

### Basic Configuration Structure

```toml
[tool.holocron]
db_path = ".workspace/holocron_data/vector_db"
default_collection = "endor_cockpit_docs"
embedding_model = "text-embedding-3-small"

[tool.holocron.content_types.markdown]
name = "Internal Markdown Documentation"
patterns = ["\\.md$", "\\.rst$"]
chunk_size = 1607
overlap = 400
delimiters = ["##"]  # H2 headers only
```

**Complete Reference**: See [CONFIGURATION.md](CONFIGURATION.md) for comprehensive configuration options, validation, and optimization guidelines.

## Architecture

Holocron is designed as a modular, configuration-driven knowledge base system with clear separation of concerns:

- **Configuration System**: Type-safe loading with environment variable interpolation
- **Content Type System**: Extensible chunking strategies for different content types
- **Vector Database Manager**: ChromaDB integration with content processing pipeline
- **Query Interface**: Natural language search with result formatting and filtering

### Data Flow

```
File Discovery → Content Type Detection → Content Processing → Chunking → Vector Storage
User Query → Query Processing → Vector Search → Result Filtering → Response Formatting
```

**Complete Reference**: See [ARCHITECTURE.md](ARCHITECTURE.md) for detailed system design, component relationships, and extension points.

## Troubleshooting

### Common Issues

- **ChromaDB Collection Not Found**: Run `uv run python -m holocron init` to recreate collection
- **External Docs Tiny Chunks**: Check chunk size configuration (should be 6000 for external_docs)
- **Cross-Platform Path Issues**: Ensure `os.path.normpath()` is used for all path operations

### Quick Health Check

```bash
# Validate system health
python scripts/validate_holocron.py

# Debug mode for detailed output
uv run python -m holocron init --verbose
uv run python -m holocron sync --verbose
```

**Complete Reference**: See [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for comprehensive issue resolution, root cause analysis, and prevention strategies.

## Cross-References

**Related Documentation**:
- [CONFIGURATION.md](CONFIGURATION.md) - Complete configuration reference
- [ARCHITECTURE.md](ARCHITECTURE.md) - System design and components  
- [SCRIPTS.md](SCRIPTS.md) - Analysis scripts and utilities
- [TROUBLESHOOTING.md](TROUBLESHOOTING.md) - Known issues and resolutions

**Analysis Scripts**:
- [`src/holocron/scripts/analyze_chunk_sizes.py`](../../src/holocron/scripts/analyze_chunk_sizes.py) - Analyze chunk size distribution
- [`src/holocron/scripts/analyze_api_operations.py`](../../src/holocron/scripts/analyze_api_operations.py) - Analyze OpenAPI operations and patterns

**Protocols**:
- [Holocron Setup Protocol](../protocols/holocron-setup.md) - Initialization workflows
- [Knowledge Sync Protocol](../protocols/knowledge-sync-protocol.md) - Maintenance workflows

**Agent Integration**:
- [RAG Usage Guide](../agents/rag_usage.md) - RAG integration patterns for AI agents
- [Agent Guide](../agents/AGENT_GUIDE.md) - General agent instructions

---

*Holocron provides the foundation for AI agents to efficiently navigate and utilize Endor Cockpit documentation through intelligent semantic search capabilities.*
