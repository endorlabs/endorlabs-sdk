# RAG Usage Guide for AI Agents

> **Retrieval Augmented Generation (RAG) integration for Endor Cockpit documentation**

## Prerequisites

Before using the RAG system, ensure you have:

### Required Environment Variables
```bash
# OpenAI API key for embeddings
export OPENAI_API_KEY="your-openai-api-key"

# Endor Labs API credentials (for context)
export ENDOR_API="https://api.endorlabs.com"
export ENDOR_API_CREDENTIALS_KEY="your-api-key"
export ENDOR_API_CREDENTIALS_SECRET="your-api-secret"
```

### Required Dependencies
```bash
# Install RAG dependencies
uv pip install -e ".[rag]"
```

### Vector Database Initialization
```bash
# Initialize the knowledge base (first time only)
uv run python workflow/init_vector_db.py

# Rebuild after documentation updates
uv run python workflow/init_vector_db.py --rebuild
```

## Overview

The Endor Cockpit RAG system provides semantic search capabilities over the project documentation using ChromaDB vector database. This enables AI agents to retrieve relevant context for API usage, troubleshooting, design patterns, and best practices.

## Chunking Strategy

**Date Updated**: 2025-10-21  
**Logbook Reference**: `.workspace/logbook.md#2025-10-21-holocron-chunking-strategy-optimization`

The RAG system uses data-driven chunking strategies based on empirical analysis of 1,910 sections across all content types. Optimal chunk sizes are determined using P95 (95th percentile) + 1000 token buffer.

### Content Type Chunking Rules

**Internal Documentation** (`docs/`):
- **Chunk Size**: 1,607 tokens (P95: 607 + 1000 buffer)
- **Split Points**: H2 headers only (`## `)
- **Preservation**: Complete H2 sections with all H3 subsections
- **Overlap**: 400 tokens for context continuity

**External Documentation** (`.workspace/downloads/user-docs/`):
- **Chunk Size**: 2,165 tokens (P95: 1165 + 1000 buffer)
- **Split Points**: Major section delimiters (`===`, `---`, `\n\n`)
- **Preservation**: Complete procedures and workflows
- **Overlap**: 500 tokens for context continuity

**Code Files** (`src/`, `tests/`):
- **Chunk Size**: 6,851 tokens (P95: 5851 + 1000 buffer)
- **Split Points**: Function and class boundaries (`def `, `class `)
- **Preservation**: Complete functions and classes
- **Overlap**: 500 tokens for context continuity

**API Specifications** (`.workspace/downloads/openapi-swagger.json`):
- **Chunk Size**: 5,000 tokens (split by individual endpoints)
- **Split Points**: Service endpoint boundaries
- **Preservation**: Complete endpoint definitions
- **Overlap**: 300 tokens for context continuity

### Semantic Coherence Principles

- **H2-only splitting**: Preserves complete sections with all subsections
- **Complete section preservation**: Never split H2 sections regardless of size
- **Context continuity**: Sufficient overlap for semantic coherence
- **Cross-platform compatibility**: OS-agnostic path handling with debug logging

## Quick Start

### Basic Usage

```python
from endor_cockpit.rag import query_vector_db, get_vector_db_info

# Query the documentation
results = query_vector_db("How do I create a namespace?")
for result in results["results"]:
    print(f"Score: {result['similarity_score']:.3f}")
    print(f"Content: {result['content'][:100]}...")

# Get database info
info = get_vector_db_info()
print(f"Total chunks: {info['chunk_count']}")
```

### Advanced Usage

```python
# Customize query parameters
results = query_vector_db(
    query_text="What are the API quirks for canonical naming?",
    n_results=3,
    include_metadata=True
)

# Access metadata
for result in results["results"]:
    if "metadata" in result:
        source = result["metadata"].get("source", "Unknown")
        print(f"Source: {source}")
```

---

## Framework Integrations

### 1. OpenAI Function Calling

```python
import openai
from endor_cockpit.rag import RAG_TOOL_SCHEMA, query_endor_documentation_tool

# Add tool to OpenAI client
client = openai.OpenAI()

# Use in chat completion
response = client.chat.completions.create(
    model="gpt-4",
    messages=[
        {"role": "user", "content": "How do I troubleshoot 403 errors in the Endor API?"}
    ],
    tools=[RAG_TOOL_SCHEMA],
    tool_choice="auto"
)

# Handle tool calls
if response.choices[0].message.tool_calls:
    tool_call = response.choices[0].message.tool_calls[0]
    if tool_call.function.name == "query_endor_documentation":
        # Execute the tool
        import json
        args = json.loads(tool_call.function.arguments)
        results = query_endor_documentation_tool(**args)
        print(f"Found {results['result_count']} relevant results")
```

### 2. LangChain Integration

```python
from langchain.tools import Tool
from endor_cockpit.rag import query_endor_documentation_tool

# Create LangChain tool
rag_tool = Tool(
    name="query_endor_documentation",
    description="Search Endor Cockpit documentation using semantic search",
    func=query_endor_documentation_tool
)

# Use in LangChain agent
from langchain.agents import initialize_agent, AgentType
from langchain.llms import OpenAI

llm = OpenAI(temperature=0)
agent = initialize_agent(
    [rag_tool], 
    llm, 
    agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
    verbose=True
)

# Query the agent
result = agent.run("How do I create a namespace in the Endor API?")
```

### 3. Anthropic Claude Integration

```python
import anthropic
from endor_cockpit.rag import query_vector_db

# Create custom tool for Claude
def search_endor_docs(query: str) -> str:
    """Search Endor Cockpit documentation."""
    results = query_vector_db(query, n_results=3)
    
    formatted_results = []
    for result in results["results"]:
        formatted_results.append(
            f"Score: {result['similarity_score']:.3f}\n"
            f"Content: {result['content'][:500]}..."
        )
    
    return "\n\n".join(formatted_results)

# Use in Claude conversation
client = anthropic.Anthropic()

response = client.messages.create(
    model="claude-3-sonnet-20240229",
    max_tokens=1000,
    messages=[
        {
            "role": "user", 
            "content": "How do I troubleshoot 403 Forbidden errors in the Endor API? Use the search_endor_docs function to find relevant information."
        }
    ],
    tools=[{
        "name": "search_endor_docs",
        "description": "Search Endor Cockpit documentation",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"}
            },
            "required": ["query"]
        }
    }]
)
```

---

## Standalone CLI Usage

### Command Line Interface

```bash
# Create a simple CLI script
cat > query_docs.py << 'EOF'
#!/usr/bin/env python3
import sys
from endor_cockpit.rag import query_vector_db

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python query_docs.py <query>")
        sys.exit(1)
    
    query = " ".join(sys.argv[1:])
    results = query_vector_db(query, n_results=3)
    
    print(f"Query: {query}")
    print(f"Found {len(results['results'])} results:\n")
    
    for i, result in enumerate(results["results"], 1):
        print(f"{i}. Score: {result['similarity_score']:.3f}")
        print(f"   Content: {result['content'][:200]}...")
        print()
EOF

# Make executable and run
chmod +x query_docs.py
python query_docs.py "How do I create a namespace?"
```

---

## Best Practices

### 1. Query Optimization

**Good queries:**
- "How do I create a namespace?"
- "What are the API quirks for canonical naming?"
- "How do I troubleshoot 403 Forbidden errors?"
- "What are the security best practices?"

**Avoid:**
- Single words: "namespace"
- Too specific: "line 42 error"
- Too vague: "help"

### 2. Result Processing

```python
def process_rag_results(results: dict, min_score: float = 0.3) -> list:
    """Process RAG results with quality filtering."""
    filtered_results = []
    
    for result in results["results"]:
        if result["similarity_score"] >= min_score:
            filtered_results.append({
                "content": result["content"],
                "score": result["similarity_score"],
                "source": result.get("metadata", {}).get("source", "Unknown")
            })
    
    return filtered_results

# Usage
results = query_vector_db("How do I create a namespace?")
quality_results = process_rag_results(results, min_score=0.4)
```

### 3. Context Window Management

```python
def get_context_for_llm(query: str, max_tokens: int = 2000) -> str:
    """Get formatted context for LLM input."""
    results = query_vector_db(query, n_results=5)
    
    context_parts = []
    current_tokens = 0
    
    for result in results["results"]:
        content = result["content"]
        # Rough token estimation (4 chars per token)
        content_tokens = len(content) // 4
        
        if current_tokens + content_tokens > max_tokens:
            break
            
        context_parts.append(f"Score: {result['similarity_score']:.3f}\n{content}")
        current_tokens += content_tokens
    
    return "\n\n---\n\n".join(context_parts)
```

---

## Error Handling

```python
from endor_cockpit.rag import query_vector_db, RAGQueryError

try:
    results = query_vector_db("How do I create a namespace?")
except RAGQueryError as e:
    print(f"RAG query failed: {e}")
    # Fallback to static documentation or error message
except Exception as e:
    print(f"Unexpected error: {e}")
```

---

## Database Management

### Check Database Status

```python
from endor_cockpit.rag import get_vector_db_info

info = get_vector_db_info()
print(f"Database status:")
print(f"  Collection: {info['collection_name']}")
print(f"  Chunks: {info['chunk_count']}")
print(f"  Documents: {info.get('total_documents', 'Unknown')}")
print(f"  Last updated: {info.get('last_updated', 'Unknown')}")
```

### Rebuild Database

```bash
# Rebuild the vector database
python workflow/init_vector_db.py --rebuild
```

---

## Troubleshooting

### Common Issues

#### 1. Missing Dependencies
```
ImportError: No module named 'chromadb'
```
**Solution**: Install RAG dependencies
```bash
uv pip install -e ".[rag]"
```

#### 2. OpenAI API Key Missing
```
WARNING: OPENAI_API_KEY environment variable not set
```
**Solution**: Set the environment variable
```bash
export OPENAI_API_KEY="your-openai-api-key"
```

#### 3. Vector Database Not Initialized
```
FileNotFoundError: [Errno 2] No such file or directory: 'workflow/vector_db'
```
**Solution**: Initialize the vector database
```bash
python workflow/init_vector_db.py
```

#### 4. Empty Query Results
If queries return no results, check:
- Vector database is initialized
- OpenAI API key is valid
- Documentation files are present
- Try rebuilding the database: `python workflow/init_vector_db.py --rebuild`

### Knowledge Base Maintenance

#### When to Update
- Contradictions found between knowledge base and actual behavior
- New patterns or best practices discovered
- API changes or new features added
- Security guidelines updated

#### How to Update
1. **Identify Contradiction**: Note the discrepancy between knowledge base and reality
2. **Document Finding**: Create a note about the correct information
3. **Update Documentation**: Modify the relevant documentation files
4. **Rebuild Database**: Run `python workflow/init_vector_db.py --rebuild`
5. **Verify Update**: Query the database to confirm the new information is indexed

#### Testing Knowledge Base Updates
```python
# Test that new information is properly indexed
results = query_vector_db("your specific question")
assert len(results["results"]) > 0
assert "expected content" in results["results"][0]["content"]
```

---

## Integration Examples

### Custom Agent Framework

```python
class EndorAgent:
    def __init__(self):
        self.rag_tool = query_endor_documentation_tool
    
    def get_context(self, user_query: str) -> str:
        """Get relevant context for user query."""
        results = self.rag_tool(
            query=user_query,
            max_results=3,
            include_metadata=True
        )
        
        if not results["success"]:
            return "Unable to retrieve documentation context."
        
        context_parts = []
        for result in results["results"]:
            context_parts.append(result["content"])
        
        return "\n\n".join(context_parts)
    
    def respond(self, user_query: str) -> str:
        """Generate response with RAG context."""
        context = self.get_context(user_query)
        
        # Use context with your LLM of choice
        prompt = f"""
        Context from documentation:
        {context}
        
        User question: {user_query}
        
        Please provide a helpful response based on the context above.
        """
        
        # Return LLM response
        return self.llm.generate(prompt)
```

---

## Troubleshooting

### Common Issues

1. **Database not found**: Ensure `workflow/vector_db/` exists and is initialized
2. **Empty results**: Check if vector database is populated with `get_vector_db_info()`
3. **Low similarity scores**: Try rephrasing queries or check database quality
4. **Import errors**: Ensure `endor-cockpit` package is installed with RAG dependencies

### Debug Mode

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Enable debug logging for RAG queries
results = query_vector_db("test query", n_results=1)
```

---

*This guide provides comprehensive examples for integrating the Endor Cockpit RAG system with various AI frameworks and use cases.*
