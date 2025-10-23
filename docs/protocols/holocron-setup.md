# Holocron Setup Protocol

> **Agent Workspace Initialization and Knowledge Base Management**

## 🎯 **Purpose**

This protocol provides step-by-step guidance for AI agents to initialize and manage their workspace using the Holocron knowledge base system. The Holocron system provides semantic search over Endor Cockpit documentation, enabling agents to quickly retrieve relevant context for their operations.

## 🚀 **Quick Start**

### **Initial Setup (First Time)**

```bash
# Initialize workspace and knowledge base
uv run python -m holocron init

# Verify setup
uv run python -m holocron query "How do I create a namespace?"
```

### **Regular Operations**

```bash
# Sync knowledge base after documentation updates
uv run python -m holocron sync

# Query for specific information
uv run python -m holocron query "How do I troubleshoot 403 errors?"
```

## 📋 **Detailed Workflow**

### **Phase 1: Environment Validation**

The `holocron init` command automatically validates:

1. **Required Environment Variables**:
   - `OPENAI_API_KEY` - For vector embeddings (required)
   
2. **Optional Environment Variables**:
   - `ENDOR_API` - Endor Labs API endpoint
   - `ENDOR_API_CREDENTIALS_KEY` - API credentials
   - `ENDOR_API_CREDENTIALS_SECRET` - API secret

3. **Dependencies**:
   - `chromadb` - Vector database
   - `openai` - Embeddings
   - `requests` - HTTP client
   - `pydantic` - Data validation

### **Phase 2: Workspace Initialization**

The system creates necessary directories:
- `.workspace/holocron_data/` - Vector database storage
- `.workspace/holocron_data/vector_db/` - ChromaDB data
- `.workspace/` - Agent workspace

### **Phase 3: Knowledge Base Creation**

The system processes documentation from:
- `docs/` - All documentation files
- `src/` - Source code with docstrings
- `tests/` - Test files
- `external_docs/openapi-swagger.json` - API specification

## 🔧 **Command Reference**

### **Initialize Workspace**
```bash
uv run python -m holocron init [--force] [--verbose]
```

**Options:**
- `--force` - Force reinitialization even if workspace exists
- `--verbose` - Enable detailed output

**When to use:**
- First-time agent setup
- After major documentation changes
- When troubleshooting workspace issues

### **Sync Knowledge Base**
```bash
uv run python -m holocron sync [--rebuild] [--verbose]
```

**Options:**
- `--rebuild` - Force full rebuild of vector database
- `--verbose` - Enable detailed output

**When to use:**
- After documentation updates
- When new files are added to docs/
- When troubleshooting search issues

### **Query Knowledge Base**
```bash
uv run python -m holocron query [query_text] [--results N] [--format text|json]
```

**Options:**
- `query_text` - Natural language query (if not provided, enters interactive mode)
- `--results N` - Number of results to return (default: 5)
- `--format` - Output format: text or json (default: text)

**Examples:**
```bash
# Specific query
uv run python -m holocron query "How do I create a namespace?"

# Interactive mode
uv run python -m holocron query

# JSON output for programmatic use
uv run python -m holocron query "troubleshoot 403" --format json
```

## 🐛 **Troubleshooting**

### **Quick Health Check**

**System Validation**:
```bash
# Run comprehensive health check
python scripts/validate_holocron.py

# Check specific components
python scripts/validate_holocron.py --check-config
python scripts/validate_holocron.py --check-database
```

### **Common Issues**

**1. ChromaDB Collection Not Found**
```
❌ Collection [endor_cockpit_docs] does not exist
```
**Solution:** Initialize the holocron system:
```bash
uv run python -m holocron init --verbose
```

**2. External Docs Tiny Chunks**
```
Found chunks with only headers (19-40 characters)
```
**Solution:** Check chunk size configuration (should be 6000 for external_docs):
```bash
uv run python -m holocron config show
```

**3. Cross-Platform Path Issues**
```
Content type detection fails on different operating systems
```
**Solution:** Ensure `os.path.normpath()` is used for all path operations

**4. Missing Environment Variables**
```
❌ Missing required environment variables: OPENAI_API_KEY
```
**Solution:** Set the required environment variable:
```bash
export OPENAI_API_KEY="your-openai-api-key"
```

### **Debug Mode**

Use `--verbose` flag for detailed output:
```bash
uv run python -m holocron init --verbose
uv run python -m holocron sync --verbose
uv run python -m holocron query "test query" --verbose
```

**Reference**: See [docs/holocron/TROUBLESHOOTING.md](../holocron/TROUBLESHOOTING.md) for comprehensive issue resolution and [docs/holocron/README.md](../holocron/README.md) for system overview.

## 🔄 **Integration with Agent Workflow**

### **RAG-First Approach**

Always query the knowledge base before making changes:

```python
from holocron import query_holocron

# Query for relevant context
results = query_holocron("How do I create a namespace?")
for result in results["results"]:
    print(f"Score: {result['similarity_score']:.3f}")
    print(f"Content: {result['content'][:100]}...")
```

### **Programmatic Usage**

```python
from holocron import init_workspace, query_holocron, get_holocron_info

# Initialize workspace programmatically
success = init_workspace(force=False, verbose=True)

# Query knowledge base
results = query_holocron("How do I troubleshoot API errors?", n_results=3)

# Get database information
info = get_holocron_info()
print(f"Total chunks: {info['chunk_count']}")
```

## 📊 **Knowledge Base Information**

### **Content Types Processed**

1. **Markdown Documentation** (`docs/*.md`)
   - Chunked by headers and paragraphs
   - Enhanced metadata extraction
   - Resource type detection

2. **Source Code** (`src/**/*.py`)
   - Chunked by functions and classes
   - Docstring preservation
   - Type annotation inclusion

3. **API Specifications** (`*.json`, `*.yaml`)
   - Chunked by major sections
   - Endpoint documentation
   - Schema definitions

4. **External Documentation** (`external_docs/`)
   - OpenAPI specification from Endor API
   - User documentation from docs.endorlabs.com
   - Automatically downloaded during init

### **External Documentation Downloads**

During `holocron init`, the following external resources are automatically downloaded:

1. **OpenAPI Specification**
   - Source: `{ENDOR_API}/download/openapiv2.swagger.json`
   - Location: `external_docs/openapi-swagger.json`
   - Purpose: Complete API specification for endpoint discovery
   - Timestamp tracked in manifest

2. **Sitemap.xml**
   - Source: `https://docs.endorlabs.com/sitemap.xml`
   - Location: `external_docs/sitemap.xml`
   - Purpose: Index of all user documentation pages

3. **User Documentation**
   - Source: All pages from sitemap.xml
   - Location: `external_docs/user-docs/*.md`
   - Purpose: Comprehensive external documentation for context
   - Converted from HTML to markdown for optimal indexing

### **Refresh Guidance**

External documentation is timestamped in the manifest file:

- **Freshness check**: Automatic warning if downloads >7 days old
- **Manual refresh**: Run `uv run python -m holocron init --force` to update
- **Check status**: Review `.workspace/holocron_data/vector_db_manifest.json`
- **Manifest location**: `external_docs` section in manifest

Example manifest structure:
```json
{
  "external_docs": {
    "openapi_spec": {
      "last_downloaded": "2025-10-20T01:30:00",
      "file_hash": "abc123...",
      "size": 524288,
      "url": "https://api.endorlabs.com/download/openapiv2.swagger.json"
    },
    "user_docs": {
      "last_downloaded": "2025-10-20T01:35:00",
      "page_count": 125,
      "sitemap_url": "https://docs.endorlabs.com/sitemap.xml"
    }
  }
}
```

### **Metadata Enhancement**

Each chunk includes:
- `content_type` - Type of content (markdown, code, api_spec)
- `file_path` - Source file path
- `file_name` - Source file name
- `resource_type` - Detected resource type (project, finding, policy, etc.)
- `h1_title` - Main document title
- `section_name` - H2 section name
- `subsection_name` - H3 section name
- `header_level` - Header level (h1, h2, h3)

## 🎯 **Best Practices**

### **For AI Agents**

1. **Always query first**: Use `uv run python -m holocron query` before starting any task
2. **Keep knowledge base updated**: Run `uv run python -m holocron sync` after documentation changes
3. **Use specific queries**: More specific queries yield better results
4. **Check similarity scores**: Higher scores indicate more relevant content

### **For Documentation Maintenance**

1. **Update after changes**: Run sync after modifying documentation
2. **Test queries**: Verify that important information is retrievable
3. **Monitor chunk quality**: Check that headers and sections are properly detected

## 🔗 **Related Documentation**

- [Agent Guide](../agents/AGENT_GUIDE.md) - General agent instructions
- [From Scratch Guide](../agents/FROM_SCRATCH_GUIDE.md) - Complete setup workflow
- [Knowledge Capture Workflow](knowledge-capture-workflow.md) - Documentation maintenance
- [API Quirks](../personas/developer/api-quirks.md) - Known API issues

## Cross-Platform Path Handling

### Path Normalization Requirements
**Source**: Logbook entry 2025-01-27

**Problem**: Cross-platform path handling issues cause content type detection failures and query function disconnects.

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

**Related**: [Cross-Platform Development Guide](../agents/developer/README.md#cross-platform-development)

## Troubleshooting

### **ChromaDB Collection Not Found Error**

**Date Discovered**: 2025-01-27  

**Issue**: Holocron system fails with "Collection [endor_cockpit_docs] does not exist" error after switching virtual environments.

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

---

*This protocol ensures agents have access to comprehensive, up-to-date knowledge about the Endor Cockpit SDK and can efficiently retrieve relevant context for their operations.*
