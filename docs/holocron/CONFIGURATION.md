# Holocron Configuration Reference

> **Complete guide to configuring the Holocron knowledge base system**

This document provides comprehensive configuration options for customizing Holocron's behavior, content types, and processing strategies.

## 📋 Configuration Structure

All Holocron configuration is defined in `pyproject.toml` under the `[tool.holocron]` section:

```toml
[tool.holocron]
# Main configuration
db_path = ".workspace/holocron_data/vector_db"
manifest_path = ".workspace/holocron_data/vector_db_manifest.json"
default_collection = "endor_cockpit_docs"
embedding_model = "text-embedding-3-small"

[tool.holocron.paths]
# Path management
include_dirs = ["docs/", "src/", "tests/", ".workspace/downloads/"]
exclude_dirs = ["__pycache__", ".git", "node_modules", "venv", ".venv"]

[tool.holocron.external_docs]
# External documentation settings
openapi_url_template = "{ENDOR_API}/download/openapiv2.swagger.json"
openapi_output = ".workspace/downloads/openapi-swagger.json"
sitemap_url = "https://docs.endorlabs.com/sitemap.xml"
sitemap_output = ".workspace/downloads/sitemap.xml"
user_docs_output = ".workspace/downloads/user-docs/"
max_age_days = 7

[tool.holocron.content_types.markdown]
# Content type definitions
name = "Internal Markdown Documentation"
patterns = ["\\.md$", "\\.rst$"]
chunk_size = 1607
overlap = 400
delimiters = ["##"]
preserve_structure = true
preserve_complete_sections = true
```

## 🔧 Main Configuration Options

### `[tool.holocron]`

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `db_path` | string | `".workspace/holocron_data/vector_db"` | Path to ChromaDB database directory |
| `manifest_path` | string | `".workspace/holocron_data/vector_db_manifest.json"` | Path to manifest file |
| `default_collection` | string | `"endor_cockpit_docs"` | Default ChromaDB collection name |
| `embedding_model` | string | `"text-embedding-3-small"` | OpenAI embedding model to use |

### `[tool.holocron.paths]`

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `include_dirs` | array | `["docs/", "src/", "tests/", ".workspace/downloads/"]` | Directories to include in processing |
| `exclude_dirs` | array | `["__pycache__", ".git", "node_modules", "venv", ".venv"]` | Directories to exclude from processing |

### `[tool.holocron.external_docs]`

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `openapi_url_template` | string | `"{ENDOR_API}/download/openapiv2.swagger.json"` | OpenAPI spec download URL template |
| `openapi_output` | string | `".workspace/downloads/openapi-swagger.json"` | Local path for OpenAPI spec |
| `sitemap_url` | string | `"https://docs.endorlabs.com/sitemap.xml"` | Sitemap URL for external docs |
| `sitemap_output` | string | `".workspace/downloads/sitemap.xml"` | Local path for sitemap |
| `user_docs_output` | string | `".workspace/downloads/user-docs/"` | Directory for user documentation |
| `max_age_days` | integer | `7` | Maximum age in days before refresh needed |

## 🎯 Content Type Configuration

Content types define how different file types are processed and chunked. Each content type has its own configuration section:

```toml
[tool.holocron.content_types.CONTENT_TYPE_NAME]
name = "Human-readable name"
patterns = ["regex_pattern1", "regex_pattern2"]
extensions = [".ext1", ".ext2"]  # Optional
chunk_size = 1000
overlap = 200
delimiters = ["delimiter1", "delimiter2"]
preserve_structure = true
preserve_complete_sections = true
split_by_endpoints = false  # Optional, for API specs
```

### Content Type Options

| Option | Type | Required | Description |
|--------|------|----------|-------------|
| `name` | string | ✅ | Human-readable name for the content type |
| `patterns` | array | ✅ | Regex patterns for file path matching |
| `extensions` | array | ❌ | File extensions (alternative to patterns) |
| `chunk_size` | integer | ✅ | Maximum chunk size in characters |
| `overlap` | integer | ✅ | Overlap between chunks in characters |
| `delimiters` | array | ✅ | Delimiters for splitting content |
| `preserve_structure` | boolean | ✅ | Whether to preserve document structure |
| `preserve_complete_sections` | boolean | ✅ | Whether to avoid splitting sections |
| `split_by_endpoints` | boolean | ❌ | Whether to split API specs by endpoints |

## 📝 Built-in Content Types

### Markdown Documentation
```toml
[tool.holocron.content_types.markdown]
name = "Internal Markdown Documentation"
patterns = ["\\.md$", "\\.rst$"]
chunk_size = 1607
overlap = 400
delimiters = ["##"]  # H2 headers only
preserve_structure = true
preserve_complete_sections = true
```

**Characteristics:**
- Chunks by H2 headers (`##`)
- Preserves complete sections
- Enhanced metadata extraction
- Resource type detection

### External Documentation
```toml
[tool.holocron.content_types.external_docs]
name = "External User Documentation"
patterns = ["\\.workspace/downloads/user-docs/.*\\.md$"]
chunk_size = 6000
overlap = 500
delimiters = ["===", "---", "\\n\\n", "Introduction", "About"]
preserve_structure = true
preserve_complete_sections = true
```

**Characteristics:**
- Look-behind detection for underline headers
- Larger chunk sizes for complete procedures
- Source URL tracking
- Breadcrumb filtering

### Source Code
```toml
[tool.holocron.content_types.code]
name = "Source Code Files"
patterns = ["\\.py$", "\\.js$", "\\.ts$", "\\.go$", "\\.java$"]
extensions = [".py", ".js", ".ts", ".go", ".java"]
chunk_size = 6851
overlap = 500
delimiters = ["def ", "class "]
preserve_structure = true
preserve_complete_sections = true
```

**Characteristics:**
- Chunks by function and class boundaries
- Preserves complete functions/classes
- Language-agnostic approach
- Docstring inclusion

### API Specifications
```toml
[tool.holocron.content_types.api_spec]
name = "API Specifications"
patterns = ["openapi.*\\.json$", "swagger.*\\.json$", "\\.yaml$", "\\.yml$"]
extensions = [".json", ".yaml", ".yml"]
chunk_size = 5000
overlap = 300
delimiters = ['"paths":', '"components":', '"definitions":']
preserve_structure = true
split_by_endpoints = true
```

**Characteristics:**
- JSON/YAML structure awareness
- Endpoint-based splitting
- Schema definition preservation
- API documentation optimization

## 🔄 Environment Variable Interpolation

Holocron supports environment variable interpolation in configuration values:

```toml
[tool.holocron.external_docs]
openapi_url_template = "{ENDOR_API}/download/openapiv2.swagger.json"
```

**Supported Variables:**
- `{ENDOR_API}` - Endor Labs API endpoint
- `{OPENAI_API_KEY}` - OpenAI API key (for embedding model)
- Any custom environment variables

**Default Values:**
```toml
# You can provide defaults
openapi_url_template = "{ENDOR_API:https://api.endorlabs.com}/download/openapiv2.swagger.json"
```

## 🎨 Custom Content Types

### Creating a Custom Content Type

1. **Define the Configuration**:
```toml
[tool.holocron.content_types.yaml_configs]
name = "YAML Configuration Files"
patterns = ["\\.yaml$", "\\.yml$"]
chunk_size = 2000
overlap = 300
delimiters = ["^[a-zA-Z_][a-zA-Z0-9_]*:", "^  [a-zA-Z_][a-zA-Z0-9_]*:"]
preserve_structure = true
preserve_complete_sections = true
```

2. **Test the Configuration**:
```bash
# Validate configuration
uv run python -m holocron config validate

# Test with sample files
uv run python -m holocron sync --verbose
```

3. **Implement Custom Chunking** (optional):
```python
from holocron.content_types import ContentSource, Chunk

class YamlConfigSource(ContentSource):
    def chunk_content(self, content: str, file_path: str = "") -> List[Chunk]:
        # Custom YAML chunking logic
        # Split by top-level keys
        # Preserve nested structure
        pass
```

### Advanced Pattern Examples

**File Extension Patterns:**
```toml
patterns = ["\\.py$", "\\.js$", "\\.ts$", "\\.go$", "\\.java$"]
```

**Directory-Specific Patterns:**
```toml
patterns = ["^docs/.*\\.md$", "^src/.*\\.py$"]
```

**Complex Regex Patterns:**
```toml
patterns = ["^.*/config/.*\\.(yaml|yml)$", "^.*/templates/.*\\.(html|jinja2)$"]
```

## ⚙️ Chunking Strategy Optimization

### Chunk Size Guidelines

| Content Type | Recommended Size | Reasoning |
|--------------|------------------|-----------|
| Markdown | 1000-2000 | Preserve complete sections |
| External Docs | 4000-6000 | Complete procedures (empirically optimized) |
| Code | 3000-7000 | Complete functions/classes |
| API Specs | 2000-5000 | Individual endpoints |

**External Docs Optimization**: Based on empirical analysis, external documentation requires larger chunk sizes (6000 tokens) to preserve complete procedures and step-by-step instructions. Smaller chunks (2165 tokens) resulted in fragmented content with only headers.

### Overlap Guidelines

| Content Type | Recommended Overlap | Reasoning |
|--------------|---------------------|-----------|
| Markdown | 200-400 | Context preservation |
| External Docs | 400-600 | Procedure continuity |
| Code | 300-500 | Function context |
| API Specs | 200-400 | Endpoint relationships |

### Delimiter Selection

**For Markdown:**
```toml
delimiters = ["##"]  # H2 headers only
delimiters = ["#", "##"]  # H1 and H2 headers
delimiters = ["##", "###"]  # H2 and H3 headers
```

**For Code:**
```toml
delimiters = ["def ", "class "]  # Python
delimiters = ["function ", "class "]  # JavaScript
delimiters = ["func ", "type "]  # Go
```

**For API Specs:**
```toml
delimiters = ['"paths":', '"components":', '"definitions":']
```

## 🔍 Configuration Validation

### Built-in Validation

Holocron automatically validates:
- Required fields are present
- Chunk sizes are positive
- Overlap is less than chunk size
- Patterns are valid regex
- Paths are accessible

### Manual Validation

```bash
# Validate configuration
uv run python -m holocron config validate

# Show current configuration
uv run python -m holocron config show

# Show configuration in JSON format
uv run python -m holocron config show --format json
```

### Common Validation Errors

**Chunk Size Issues:**
```
❌ chunk_size must be positive, got -100
```

**Overlap Issues:**
```
❌ overlap (500) must be less than chunk_size (400)
```

**Pattern Issues:**
```
❌ Invalid regex pattern: "[unclosed"
```

## 🚀 Performance Tuning

### Database Performance

**Chunk Size Optimization:**
- Larger chunks = fewer database entries
- Smaller chunks = better search precision
- Balance based on content type

**Overlap Optimization:**
- Higher overlap = better context preservation
- Lower overlap = faster processing
- Adjust based on content structure

### Memory Usage

**Processing Large Files:**
```toml
# Reduce chunk size for large files
chunk_size = 1000
overlap = 200
```

**Batch Processing:**
- Holocron processes files in batches
- Memory usage scales with batch size
- Adjust based on available RAM

### Search Performance

**Content Type Filtering:**
```python
# Query specific content types
results = query_holocron(
    "authentication methods",
    collection_filter={"content_type": {"$in": ["api_spec", "external_docs"]}}
)
```

**Result Limiting:**
```python
# Limit results for faster queries
results = query_holocron("query", n_results=3)
```

## 🔧 Configuration Validation

### Validation Tools

**Comprehensive Validation:**
```bash
# Run full configuration validation
python scripts/validate_holocron.py

# Check configuration only
python scripts/validate_holocron.py --check-config

# Built-in validation
uv run python -m holocron config validate
```

**Configuration Debugging:**
```bash
# Show current configuration
uv run python -m holocron config show --verbose

# Test configuration loading
uv run python -m holocron config validate --verbose
```

### Validation Criteria

The validation system checks:

1. **Configuration File**: TOML syntax, required sections, field types
2. **Environment Variables**: Required variables, interpolation success
3. **Content Types**: Pattern validity, chunk size constraints, overlap limits
4. **Paths**: Directory existence, accessibility, cross-platform compatibility
5. **Dependencies**: Required packages, import availability

**Reference**: See [validate_holocron.py](../../scripts/validate_holocron.py) for complete validation implementation.

## 🔧 Common Configuration Issues

**External Documentation Chunking**:
- **Issue**: Tiny chunks with only headers (19-40 characters)
- **Cause**: Chunk size too small for external doc structure
- **Solution**: Increase `chunk_size` to 6000 for external_docs content type
- **Configuration**: `[tool.holocron.content_types.external_docs] chunk_size = 6000`
- **Validation**: See `tests/test_content_types.py` for chunking tests

**Content Type Detection**:
- **Issue**: Content type not detected correctly
- **Cause**: Regex patterns not matching file paths
- **Solution**: Test patterns with actual file paths
- **Configuration**: Use specific patterns like `["\\.workspace/downloads/user-docs/.*\\.md$"]`
- **Validation**: See `scripts/validate_holocron.py` for detection validation

**Chunking Strategy**:
- **Issue**: Headers separated from content
- **Cause**: Delimiters not matching content structure
- **Solution**: Use content-specific delimiters (e.g., `["===", "---"]` for external docs)
- **Configuration**: Match delimiters to actual content structure
- **Validation**: See `tests/test_content_types.py` for delimiter tests

**Cross-Platform Path Issues**:
- **Issue**: Content type detection fails on different operating systems
- **Cause**: Inconsistent path handling between Windows and Unix systems
- **Solution**: Use `os.path.normpath()` for all path operations
- **Configuration**: Ensure patterns work with normalized paths
- **Validation**: See `scripts/validate_holocron.py` for cross-platform validation

### Empirical Data from Logbook

**External Documentation Optimization** (2025-10-22):
- **Before**: 2165 token chunks → Tiny fragments with only headers
- **After**: 6000 token chunks → Complete procedures with headers + content
- **Result**: 1,703 external_docs chunks properly indexed vs 0 before
- **Validation**: See `.workspace/logbook.md` for detailed analysis

**Chunk Size Recommendations**:
- **Markdown**: 1,607 tokens (P95: 607 + 1000 buffer)
- **External Docs**: 6,000 tokens (empirically optimized for complete procedures)
- **Code**: 6,851 tokens (P95: 5851 + 1000 buffer)
- **API Specs**: 5,000 tokens (endpoint-based splitting)

**Reference**: See [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for comprehensive issue resolution and [ARCHITECTURE.md](ARCHITECTURE.md) for system design details.

## 📚 Examples

### Complete Configuration Example

```toml
[tool.holocron]
db_path = ".workspace/holocron_data/vector_db"
manifest_path = ".workspace/holocron_data/vector_db_manifest.json"
default_collection = "my_project_docs"
embedding_model = "text-embedding-3-small"

[tool.holocron.paths]
include_dirs = [
    "docs/",
    "src/",
    "tests/",
    "examples/",
    ".workspace/downloads/"
]
exclude_dirs = [
    "__pycache__",
    ".git",
    "node_modules",
    "venv",
    ".venv",
    "build",
    "dist"
]

[tool.holocron.external_docs]
openapi_url_template = "{ENDOR_API}/download/openapiv2.swagger.json"
openapi_output = ".workspace/downloads/openapi-swagger.json"
sitemap_url = "https://docs.example.com/sitemap.xml"
sitemap_output = ".workspace/downloads/sitemap.xml"
user_docs_output = ".workspace/downloads/user-docs/"
max_age_days = 3

# Custom content types
[tool.holocron.content_types.markdown]
name = "Documentation"
patterns = ["\\.md$", "\\.rst$"]
chunk_size = 2000
overlap = 400
delimiters = ["##"]
preserve_structure = true
preserve_complete_sections = true

[tool.holocron.content_types.code]
name = "Source Code"
patterns = ["\\.py$", "\\.js$", "\\.ts$"]
chunk_size = 5000
overlap = 500
delimiters = ["def ", "class ", "function "]
preserve_structure = true
preserve_complete_sections = true

[tool.holocron.content_types.configs]
name = "Configuration Files"
patterns = ["\\.yaml$", "\\.yml$", "\\.json$"]
chunk_size = 1500
overlap = 200
delimiters = ["^[a-zA-Z_][a-zA-Z0-9_]*:"]
preserve_structure = true
preserve_complete_sections = true
```

---

*This configuration reference provides comprehensive guidance for customizing Holocron to meet your specific documentation and search requirements.*
