# Holocron Troubleshooting Guide

> **Known issues, solutions, and prevention strategies for the Holocron knowledge base system**

This document contains validated solutions to common Holocron issues, based on real-world testing and logbook entries. Each issue includes symptoms, root cause analysis, working solutions, and prevention strategies.

## 🚨 Critical Issues

### ChromaDB Collection Not Found Error

**Date Discovered**: 2025-01-27  
**Source**: Logbook entry - ChromaDB collection issues after virtual environment changes

**Symptoms**:
- `HolocronQueryError: Failed to initialize vector database: Collection [endor_cockpit_docs] does not exist`
- Database files exist in `.workspace/holocron_data/vector_db/` but collection is missing
- System worked before but fails after virtual environment changes

**Root Cause**: The ChromaDB collection `endor_cockpit_docs` needs to be created through holocron initialization, not just database file restoration.

**Solution**: Initialize the holocron system to create the collection.

```bash
# Initialize holocron system
uv run python -m holocron init --verbose

# Verify collection exists
uv run python -c "from holocron import query_holocron; print('Holocron working')"
```

**Prevention**: Always run `holocron init` after virtual environment changes or when setting up the system for the first time.

**Key Learning**: The `endor_cockpit_docs` collection is a ChromaDB entity that contains vector embeddings of processed documentation, not the same as the physical `docs/` folder. When switching virtual environments, the collection needs to be recreated even if database files exist.

**Test Validation**: See `tests/test_holocron_config.py` for collection initialization tests.

---

## 🔧 Content Processing Issues

### External Documentation Chunking - Tiny Chunks with Only Headers

**Date Discovered**: 2025-10-22  
**Source**: Logbook entry - External docs content type detection and chunking issues

**Symptoms**:
- Query results show only headers like "Create a namespace" (19-40 characters) without content
- Chunks are being split at underline headers but content isn't being included
- Breadcrumbs like "2. Set up namespaces" are being treated as headers

**Root Cause**: Headers being saved before content is added, and chunk size too small for external doc structure.

**Solution**: Complete rewrite of external docs chunking with look-behind detection:

```python
# Key changes in _chunk_external_docs method:
# 1. Look-behind detection for underline headers (=== or ---)
if i > 0 and self._is_underline(line):
    # Previous line is the actual header text
    header_text = lines[i - 1].strip()
    if header_text and not self._should_skip_line(lines[i - 1]):
        # Start new chunk WITH header + underline
        current_chunk = [lines[i - 1], line]
        current_size = len(lines[i - 1]) + len(line) + 1
        continue  # Skip processing underline line

# 2. Increased chunk size from 2165 to 6000 tokens
# 3. Added _is_underline() helper method
# 4. Removed aggressive title case matching that caught breadcrumbs
```

**Configuration Changes**:
```toml
[tool.holocron.content_types.external_docs]
chunk_size = 6000  # Increased from 2165
delimiters = ["===", "---", "\n\n", "Introduction", "About"]
```

**Prevention**: 
- Use look-behind detection for underline headers
- Headers must be included WITH content, not as separate chunks
- Configure chunk sizes based on content characteristics (6000 tokens for external docs)

**Test Validation**: See `tests/test_content_types.py` for external docs chunking tests.

---

### Content Type Detection - "Not in Scope" Errors

**Date Discovered**: 2025-10-22  
**Source**: Logbook entry - Content type detection issues during chunking

**Symptoms**:
- `name 'content_type' is not defined` errors in chunking methods
- External docs are detected and processed during sync
- Content type detection works correctly (returns `external_docs`)
- But chunking methods fail with `content_type` not in scope errors

**Root Cause**: Parameter passing issues through method calls when trying to pass content_type through chunking methods.

**Solution**: Use path specificity approach - hardcode content type in chunking methods since we know the content type from the file path.

```python
# In _chunk_external_docs method, use hardcoded content type
"content_type": "external_docs"
```

**Prevention**: When dealing with content type detection in chunking methods, use path specificity (hardcoded values based on file path patterns) rather than trying to pass parameters through multiple method calls.

**Test Validation**: See `tests/test_content_types.py` for content type detection tests.

---

## 🖥️ Cross-Platform Issues

### Path Normalization Requirements

**Date Discovered**: 2025-01-27  
**Source**: Logbook entry - Cross-platform path handling issues

**Problem**: Cross-platform path handling issues cause content type detection failures and query function disconnects.

**Symptoms**:
- Content type detection fails on Windows (backslashes) vs macOS/Linux (forward slashes)
- Database and query function paths become disconnected
- Regex pattern matching fails due to path format differences

**Solution**: Implement consistent path normalization across all components:

```python
import os

# Always normalize paths for cross-platform compatibility
normalized_path = os.path.normpath(file_path)

# Convert to forward slashes for regex pattern matching
regex_path = normalized_path.replace(os.path.sep, "/")
```

**Prevention**: 
- Use `os.path.normpath()` for all path operations
- Convert paths to forward slashes before regex matching
- Ensure database and query function use same path conventions
- Test path handling on target platforms (Windows, macOS, Linux)

**Test Validation**: See `tests/test_content_types.py` for cross-platform path handling tests.

---

## ⚙️ Configuration Issues

### Missing Environment Variables

**Symptoms**:
```
❌ Missing required environment variables: OPENAI_API_KEY
```

**Solution**: Set the required environment variable:
```bash
export OPENAI_API_KEY="your-openai-api-key"
```

**Prevention**: Use `scripts/validate_environment.py` to check environment setup before running holocron.

### Missing Dependencies

**Symptoms**:
```
❌ Missing required packages: chromadb, openai
```

**Solution**: Install RAG dependencies:
```bash
uv pip install -e '.[holocron]'
```

**Prevention**: Always install holocron dependencies when setting up the environment.

### Vector Database Not Found

**Symptoms**:
```
❌ Failed to initialize vector database: Collection not found
```

**Solution**: Rebuild the knowledge base:
```bash
uv run python -m holocron sync --rebuild
```

**Prevention**: Run `uv run python -m holocron init` after environment changes.

### No Results from Query

**Symptoms**:
```
Found 0 results
```

**Solutions**:
- Check if knowledge base is initialized: `uv run python -m holocron sync`
- Try broader search terms
- Verify documentation files exist in `docs/`

**Prevention**: Use `scripts/validate_holocron.py` to verify system health.

---

## 🔍 Debugging Tools

### Validation Script

Use the holocron validation script to diagnose issues:

```bash
# Run comprehensive validation
python scripts/validate_holocron.py

# Check specific components
python scripts/validate_holocron.py --check-config
python scripts/validate_holocron.py --check-database
python scripts/validate_holocron.py --check-chunking
```

### Debug Mode

Enable verbose output for detailed debugging:

```bash
uv run python -m holocron init --verbose
uv run python -m holocron sync --verbose
uv run python -m holocron query "test query" --verbose
```

### Manual Database Inspection

```python
# Check database state
from holocron import get_holocron_info
info = get_holocron_info()
print(f"Collections: {info['collections']}")
print(f"Total chunks: {info['chunk_count']}")
```

---

## 📚 Related Documentation

- **[Configuration Guide](CONFIGURATION.md)** - Complete configuration reference
- **[Architecture Guide](ARCHITECTURE.md)** - System design and components  
- **[Setup Protocol](../protocols/holocron-setup.md)** - Initialization workflows
- **[Validation Script](../scripts/validate_holocron.py)** - Health check automation

---

## 🧪 Test Coverage

All solutions in this guide are validated by tests:

- **Configuration Tests**: `tests/test_holocron_config.py`
- **Content Type Tests**: `tests/test_content_types.py`
- **Integration Tests**: `tests/test_integration.py`

When adding new troubleshooting entries, ensure corresponding tests exist to validate the solutions.

---

*This troubleshooting guide is maintained based on real-world issues encountered during Holocron development and operations. All solutions have been tested and validated.*
