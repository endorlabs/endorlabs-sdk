# Holocron Setup Protocol

> **Agent Workspace Initialization and Knowledge Base Management**

## 🎯 **Purpose**

This protocol provides step-by-step guidance for AI agents to initialize and manage their workspace using the Holocron knowledge base system. The Holocron system provides semantic search over Endor Cockpit documentation, enabling agents to quickly retrieve relevant context for their operations.

## 🚀 **Quick Start**

### **Initial Setup (First Time)**

```bash
# Initialize workspace and knowledge base
python -m holocron init

# Verify setup
python -m holocron query "How do I create a namespace?"
```

### **Regular Operations**

```bash
# Sync knowledge base after documentation updates
python -m holocron sync

# Query for specific information
python -m holocron query "How do I troubleshoot 403 errors?"
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
- `holocron_data/` - Vector database storage
- `holocron_data/vector_db/` - ChromaDB data
- `workspace/` - Agent workspace

### **Phase 3: Knowledge Base Creation**

The system processes documentation from:
- `docs/` - All documentation files
- `src/` - Source code with docstrings
- `tests/` - Test files
- `tmp/openapiv2.swagger.json` - API specification

## 🔧 **Command Reference**

### **Initialize Workspace**
```bash
python -m holocron init [--force] [--verbose]
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
python -m holocron sync [--rebuild] [--verbose]
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
python -m holocron query [query_text] [--results N] [--format text|json]
```

**Options:**
- `query_text` - Natural language query (if not provided, enters interactive mode)
- `--results N` - Number of results to return (default: 5)
- `--format` - Output format: text or json (default: text)

**Examples:**
```bash
# Specific query
python -m holocron query "How do I create a namespace?"

# Interactive mode
python -m holocron query

# JSON output for programmatic use
python -m holocron query "troubleshoot 403" --format json
```

## 🐛 **Troubleshooting**

### **Common Issues**

**1. Missing Environment Variables**
```
❌ Missing required environment variables: OPENAI_API_KEY
```
**Solution:** Set the required environment variable:
```bash
export OPENAI_API_KEY="your-openai-api-key"
```

**2. Missing Dependencies**
```
❌ Missing required packages: chromadb, openai
```
**Solution:** Install RAG dependencies:
```bash
uv pip install -e '.[rag]'
```

**3. Vector Database Not Found**
```
❌ Failed to initialize vector database: Collection not found
```
**Solution:** Rebuild the knowledge base:
```bash
python -m holocron sync --rebuild
```

**4. No Results from Query**
```
Found 0 results
```
**Solution:** 
- Check if knowledge base is initialized: `python -m holocron sync`
- Try broader search terms
- Verify documentation files exist in `docs/`

### **Debug Mode**

Use `--verbose` flag for detailed output:
```bash
python -m holocron init --verbose
python -m holocron sync --verbose
```

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

1. **Always query first**: Use `python -m holocron query` before starting any task
2. **Keep knowledge base updated**: Run `python -m holocron sync` after documentation changes
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

---

*This protocol ensures agents have access to comprehensive, up-to-date knowledge about the Endor Cockpit SDK and can efficiently retrieve relevant context for their operations.*
