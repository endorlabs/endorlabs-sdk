# Knowledge Base

> **RAG-compatible knowledge base for semantic search and retrieval**

## 🎯 **Purpose**

This knowledge base contains structured, chunked content optimized for Retrieval-Augmented Generation (RAG) systems. Content is organized for semantic search and retrieval by AI agents.

## 📚 **Structure**

### **Endor Data Model**
- **[Namespaces](./endor-data-model/namespaces.md)** - Namespace resource deep-dive
- **[Projects](./endor-data-model/projects.md)** - Project resource deep-dive  
- **[Findings](./endor-data-model/findings.md)** - Finding resource deep-dive
- **[Policies](./endor-data-model/policies.md)** - Policy resource deep-dive
- **[Relationships](./endor-data-model/relationships.md)** - Resource relationships

### **API Corrections**
- **[Namespace API](./api-corrections/namespace-api.md)** - Known issues with namespace endpoints
- **[Policy API](./api-corrections/policy-api.md)** - Known issues with policy endpoints
- **[Findings API](./api-corrections/findings-api.md)** - Known issues with findings endpoints

### **Examples**
- **[Create Namespace Hierarchy](./examples/create-namespace-hierarchy.md)** - Step-by-step namespace creation
- **[Write Semgrep Policy](./examples/write-semgrep-policy.md)** - Policy authoring example
- **[Configure GitHub Integration](./examples/configure-github-integration.md)** - Integration setup
- **[Correlate Findings](./examples/correlate-findings.md)** - Cross-repo analysis

---

## 🔍 **Usage**

### **Semantic Search**
This knowledge base is designed for semantic search queries:
- "How do I create a namespace hierarchy?"
- "What are the known API issues with namespace operations?"
- "How do I write a security policy for Semgrep?"

### **Vector Database Integration**
Content is automatically indexed in the vector database for:
- **Semantic similarity search**
- **Context-aware retrieval**
- **Multi-modal content understanding**

### **Chunking Strategy**
Content is chunked using semantic strategies:
- **Markdown**: By headers and sections
- **Code**: By functions and classes
- **API Specs**: By major sections
- **Examples**: By workflow steps

**Detailed Strategy**: See [RAG Usage Guide](agents/rag_usage.md#chunking-strategy) for comprehensive chunking rules and empirical analysis.

---

## 📊 **Content Statistics**

- **Total Documents**: [Updated by init_vector_db.py]
- **Total Chunks**: [Updated by init_vector_db.py]
- **Last Updated**: [Updated by init_vector_db.py]

---

## 🔄 **Maintenance**

### **Adding New Content**
1. Create new markdown files in appropriate directories
2. Follow semantic chunking guidelines
3. Run `python workflow/init_vector_db.py` to update vector DB
4. Verify content is properly indexed

### **Updating Existing Content**
1. Edit markdown files as needed
2. Run `python workflow/init_vector_db.py` to update vector DB
3. Test semantic search to verify updates

### **Content Guidelines**
- **Semantic Structure**: Use clear headers and sections
- **Context Preservation**: Maintain context within chunks
- **Cross-References**: Link related content
- **Examples**: Include practical examples

---

*This knowledge base serves as the foundation for AI agent retrieval and understanding of Endor Cockpit systems.*
