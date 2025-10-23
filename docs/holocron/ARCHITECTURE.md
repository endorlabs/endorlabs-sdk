# Holocron Architecture Guide

> **System design, components, and extension points for the Holocron knowledge base**

This document provides a comprehensive overview of Holocron's architecture, including system design, component relationships, and extension points for customization.

## 🏗️ System Overview

Holocron is designed as a modular, configuration-driven knowledge base system with the following core principles:

- **Configuration-First**: All behavior controlled via `pyproject.toml`
- **Extensible**: Custom content types and chunking strategies
- **Type-Safe**: Pydantic dataclasses for all configuration
- **Modular**: Clear separation of concerns between components

## 📊 Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    Holocron System                          │
├─────────────────────────────────────────────────────────────┤
│  Configuration Layer                                        │
│  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────┐ │
│  │   HolocronConfig│  │ ContentTypeConfig│  │ PathConfig   │ │
│  │                 │  │                 │  │              │ │
│  └─────────────────┘  └─────────────────┘  └──────────────┘ │
├─────────────────────────────────────────────────────────────┤
│  Content Processing Layer                                   │
│  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────┐ │
│  │ ContentTypeRegistry│ │ ContentSource   │ │ Chunking     │ │
│  │                 │  │ (Abstract)      │  │ Strategies   │ │
│  └─────────────────┘  └─────────────────┘  └──────────────┘ │
├─────────────────────────────────────────────────────────────┤
│  Vector Database Layer                                      │
│  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────┐ │
│  │ VectorDBManager │  │ ChromaDB        │  │ Embeddings   │ │
│  │                 │  │ Integration     │  │ (OpenAI)     │ │
│  └─────────────────┘  └─────────────────┘  └──────────────┘ │
├─────────────────────────────────────────────────────────────┤
│  Query Interface Layer                                      │
│  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────┐ │
│  │ HolocronQuery   │  │ Query Interface │  │ Result       │ │
│  │                 │  │                 │  │ Formatting   │ │
│  └─────────────────┘  └─────────────────┘  └──────────────┘ │
├─────────────────────────────────────────────────────────────┤
│  External Integration Layer                                │
│  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────┐ │
│  │ External Docs   │  │ OpenAPI         │  │ Sitemap      │ │
│  │ Downloader       │  │ Downloader      │  │ Parser       │ │
│  └─────────────────┘  └─────────────────┘  └──────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

## 🔧 Core Components

### 1. Configuration System (`config.py`)

**Purpose**: Type-safe configuration loading and validation

**Key Classes**:
- `HolocronConfig`: Main configuration container
- `ContentTypeConfig`: Per-content-type configuration
- `PathConfig`: File path management
- `ExternalDocsConfig`: External documentation settings

**Features**:
- Environment variable interpolation
- Configuration validation
- Default value fallbacks
- Type safety with Pydantic

```python
@dataclass
class HolocronConfig:
    db_path: str
    manifest_path: str
    default_collection: str
    embedding_model: str
    paths: PathConfig
    external_docs: ExternalDocsConfig
    content_types: Dict[str, ContentTypeConfig]
```

### 2. Content Type System (`content_types.py`)

**Purpose**: Extensible content processing and chunking

**Key Classes**:
- `ContentSource`: Abstract base class for content processing
- `ContentTypeRegistry`: Dynamic content type management
- `Chunk`: Data structure for processed content

**Built-in Content Sources**:
- `MarkdownSource`: Header-aware markdown processing
- `ExternalDocsSource`: Underline header detection
- `CodeSource`: Function/class boundary detection
- `ApiSpecSource`: JSON/YAML structure awareness

```python
class ContentSource(ABC):
    def __init__(self, config: ContentTypeConfig): ...
    
    @abstractmethod
    def chunk_content(self, content: str, file_path: str = "") -> List[Chunk]: ...
    
    @abstractmethod
    def detect(self, file_path: str) -> bool: ...
```

### 3. Vector Database Manager (`manager.py`)

**Purpose**: ChromaDB integration and content processing pipeline

**Key Features**:
- Configuration-driven operations
- Content type detection and processing
- Batch processing for large datasets
- Manifest management for incremental updates

**Processing Pipeline**:
1. **File Discovery**: Scan configured directories
2. **Content Type Detection**: Use registry to identify content types
3. **Content Processing**: Delegate to appropriate ContentSource
4. **Vector Storage**: Store embeddings in ChromaDB
5. **Manifest Update**: Track processing state

### 4. Query Interface (`query.py`)

**Purpose**: Natural language search over vector database

**Key Features**:
- Semantic similarity search
- Content type filtering
- Result formatting and ranking
- Metadata extraction

**Query Flow**:
1. **Query Processing**: Convert natural language to embeddings
2. **Vector Search**: Find similar content in ChromaDB
3. **Result Filtering**: Apply content type filters
4. **Result Formatting**: Return structured results with metadata

## 🔄 Data Flow

### 1. Initialization Flow

```
User Command → CLI Parser → Config Loading → Workspace Setup → External Downloads → Vector DB Init
```

**Steps**:
1. Parse command line arguments
2. Load configuration from `pyproject.toml`
3. Validate environment and dependencies
4. Create necessary directories
5. Download external documentation
6. Initialize vector database with content

### 2. Content Processing Flow

```
File Discovery → Content Type Detection → Content Processing → Chunking → Vector Storage
```

**Steps**:
1. **File Discovery**: Scan include directories, exclude specified paths
2. **Content Type Detection**: Use regex patterns to identify content types
3. **Content Processing**: Read file content and detect changes
4. **Chunking**: Apply content-type-specific chunking strategies
5. **Vector Storage**: Generate embeddings and store in ChromaDB

### 3. Query Flow

```
User Query → Query Processing → Vector Search → Result Filtering → Response Formatting
```

**Steps**:
1. **Query Processing**: Convert natural language to embeddings
2. **Vector Search**: Find similar content using ChromaDB
3. **Result Filtering**: Apply content type and metadata filters
4. **Response Formatting**: Return structured results with similarity scores

## 🎯 Content Type Architecture

### Abstract ContentSource

```python
class ContentSource(ABC):
    """Abstract base class for content sources."""
    
    def __init__(self, config: ContentTypeConfig):
        self.config = config
        self._compiled_patterns = [re.compile(pattern) for pattern in config.patterns]
    
    @abstractmethod
    def chunk_content(self, content: str, file_path: str = "") -> List[Chunk]:
        """Chunk content according to the content type strategy."""
        pass
    
    def detect(self, file_path: str) -> bool:
        """Detect if file matches this content type."""
        # Pattern matching logic
        pass
```

### Content Type Registry

```python
class ContentTypeRegistry:
    """Registry for managing content type sources."""
    
    def __init__(self, content_types: Dict[str, ContentTypeConfig]):
        self.content_types = content_types
        self.sources = {}
        self._initialize_sources()
    
    def detect_content_type(self, file_path: str) -> Optional[str]:
        """Detect content type for a file."""
        pass
    
    def chunk_content(self, content: str, file_path: str, content_type: str) -> List[Chunk]:
        """Chunk content using the appropriate source."""
        pass
```

### Chunking Strategies

#### Markdown Chunking
- **Strategy**: Header-based sectioning
- **Delimiters**: H2 headers (`##`)
- **Metadata**: H1 title, section name, resource type
- **Preservation**: Complete sections, no mid-section splits

#### External Docs Chunking
- **Strategy**: Underline header detection with look-behind
- **Delimiters**: `===`, `---`, `\n\n`
- **Metadata**: Source URL, section hierarchy
- **Preservation**: Complete procedures, larger chunks
- **Key Learning**: Look-behind detection is essential for underline headers (`===` or `---`)
- **Critical**: Headers must be included WITH content, not as separate chunks
- **Optimization**: Chunk size of 6000 tokens preserves complete sections

#### Code Chunking
- **Strategy**: Function/class boundary detection
- **Delimiters**: `def `, `class `
- **Metadata**: File path, function/class names
- **Preservation**: Complete functions/classes

#### API Spec Chunking
- **Strategy**: JSON/YAML structure awareness
- **Delimiters**: `"paths":`, `"components":`, `"definitions":`
- **Metadata**: Section name, endpoint information
- **Preservation**: Individual endpoints, schema definitions

## 🔌 Extension Points

### 1. Custom Content Types

**Adding a New Content Type**:

1. **Define Configuration**:
```toml
[tool.holocron.content_types.custom]
name = "Custom Content Type"
patterns = ["\\.custom$"]
chunk_size = 2000
overlap = 300
delimiters = ["CUSTOM_DELIMITER"]
```

2. **Implement ContentSource** (optional):
```python
class CustomSource(ContentSource):
    def chunk_content(self, content: str, file_path: str = "") -> List[Chunk]:
        # Custom chunking logic
        chunks = []
        # Process content according to custom strategy
        return chunks
```

3. **Register in Registry**:
```python
# Add to source_mapping in ContentTypeRegistry._get_source_class()
source_mapping = {
    "markdown": MarkdownSource,
    "external_docs": ExternalDocsSource,
    "code": CodeSource,
    "api_spec": ApiSpecSource,
    "custom": CustomSource,  # Add custom source
}
```

### 2. Custom Chunking Strategies

**Implementing Custom Chunking**:

```python
class CustomChunkingStrategy:
    def __init__(self, config: ContentTypeConfig):
        self.config = config
    
    def chunk_content(self, content: str) -> List[Chunk]:
        # Custom chunking logic
        chunks = []
        
        # Example: Split by custom delimiters
        for delimiter in self.config.delimiters:
            if delimiter in content:
                # Process delimiter-based splitting
                pass
        
        return chunks
```

### 3. Custom Metadata Extraction

**Enhancing Metadata**:

```python
def _extract_custom_metadata(self, content: str, file_path: str) -> Dict[str, Any]:
    """Extract custom metadata from content."""
    metadata = {
        "content_type": self.config.name.lower().replace(" ", "_"),
        "file_path": file_path,
        "file_name": os.path.basename(file_path),
    }
    
    # Custom metadata extraction
    if "version:" in content:
        metadata["version"] = self._extract_version(content)
    
    if "author:" in content:
        metadata["author"] = self._extract_author(content)
    
    return metadata
```

## 🗄️ Data Storage

### ChromaDB Integration

**Collection Structure**:
- **Collection Name**: Configurable via `default_collection`
- **Documents**: Chunked content text
- **Metadatas**: Content type, file path, chunk index, custom fields
- **IDs**: Unique identifiers for each chunk

**Metadata Schema**:
```python
{
    "content_type": "markdown",
    "chunk_index": 0,
    "size": 1500,
    "file_path": "docs/README.md",
    "file_name": "README.md",
    "h1_title": "Project Overview",
    "section_name": "Installation",
    "subsection_name": "Requirements",
    "resource_type": "project"
}
```

### Manifest Management

**Manifest Structure**:
```json
{
    "version": "1.0",
    "last_updated": "2025-01-27T10:30:00",
    "embedding_model": "text-embedding-3-small",
    "chunking_strategy": "semantic_headers",
    "documents": {
        "docs/README.md": {
            "file_hash": "abc123...",
            "chunks": 5,
            "last_modified": "2025-01-27T10:30:00",
            "content_type": "markdown"
        }
    },
    "total_chunks": 1250,
    "total_documents": 45
}
```

## 🔍 Query Processing

### Query Pipeline

1. **Query Preprocessing**:
   - Natural language input
   - Content type filtering
   - Result count limits

2. **Vector Search**:
   - Convert query to embeddings
   - Search ChromaDB for similar content
   - Apply similarity thresholds

3. **Result Processing**:
   - Filter by content type
   - Apply metadata filters
   - Rank by similarity score

4. **Response Formatting**:
   - Structure results with metadata
   - Include similarity scores
   - Format for display or programmatic use

### Query Interface

```python
def query_holocron(
    query_text: str,
    n_results: int = 10,
    include_metadata: bool = True,
    collection_filter: Optional[Dict] = None
) -> Dict[str, Any]:
    """Query the Endor Cockpit vector database."""
    pass
```

## 🚀 Performance Considerations

### Chunking Optimization

**Chunk Size Impact**:
- **Larger chunks**: Fewer database entries, better context
- **Smaller chunks**: More precise search, more database entries
- **Balance**: Content-type specific optimization

**Overlap Impact**:
- **Higher overlap**: Better context preservation, more storage
- **Lower overlap**: Faster processing, less storage
- **Optimal**: 20-30% of chunk size

### Database Performance

**Batch Processing**:
- Process files in batches of 1000 chunks
- Reduce memory usage for large datasets
- Enable incremental updates

**Indexing Strategy**:
- Use ChromaDB's built-in indexing
- Optimize for similarity search
- Consider content type partitioning

### Memory Management

**Processing Large Files**:
- Stream processing for large files
- Chunk-based processing to limit memory
- Garbage collection between batches

**Query Optimization**:
- Limit result counts
- Use content type filtering
- Cache frequent queries

## 🔧 System Validation

### Health Check Tools

**Comprehensive Validation**:
```bash
# Run full system validation
python scripts/validate_holocron.py

# Check specific components
python scripts/validate_holocron.py --check-config
python scripts/validate_holocron.py --check-database
python scripts/validate_holocron.py --check-chunking
```

**Configuration Debugging**:
```bash
uv run python -m holocron config show --verbose
uv run python -m holocron config validate
```

**Processing Debugging**:
```bash
uv run python -m holocron sync --verbose
```

**Query Debugging**:
```bash
uv run python -m holocron query "test query" --verbose
```

### Validation Points

The system includes validation at multiple levels:

1. **Configuration Validation**: TOML syntax, required fields, value ranges
2. **Dependency Validation**: Required packages, import availability
3. **Database Validation**: Collection existence, chunk counts, query functionality
4. **Content Type Validation**: Pattern matching, chunking strategy effectiveness
5. **Cross-Platform Validation**: Path normalization, file system compatibility

**Reference**: See [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for detailed issue resolution and [validate_holocron.py](../../scripts/validate_holocron.py) for validation implementation.

## 🔧 Common Chunking Issues

**External Documentation Chunking**:
- **Issue**: Tiny chunks with only headers, no content
- **Cause**: Headers being saved before content is added
- **Solution**: Use look-behind detection for underline headers
- **Implementation**: Include headers WITH content, not as separate chunks
- **Validation**: See `tests/test_content_types.py` for test coverage

**Content Type Detection**:
- **Issue**: Content type not in scope errors during chunking
- **Cause**: Parameter passing issues through method calls
- **Solution**: Use path specificity (hardcoded content type based on file path)
- **Implementation**: Set content type directly in chunking methods
- **Validation**: See `tests/test_content_types.py` for detection tests

**Chunk Size Optimization**:
- **Issue**: Fragmented content with incomplete sections
- **Cause**: Chunk size too small for content structure
- **Solution**: Increase chunk size for content type (e.g., 6000 tokens for external docs)
- **Implementation**: Configure chunk sizes based on content characteristics
- **Validation**: See `scripts/validate_holocron.py` for chunking validation

**Cross-Platform Path Issues**:
- **Issue**: Content type detection fails on different operating systems
- **Cause**: Inconsistent path handling between Windows (backslashes) and Unix (forward slashes)
- **Solution**: Use `os.path.normpath()` for all path operations
- **Implementation**: Convert paths to forward slashes before regex matching
- **Validation**: See `tests/test_content_types.py` for cross-platform tests

## 📚 Best Practices

### Configuration Design

1. **Start Simple**: Begin with default configurations
2. **Iterate**: Adjust based on content characteristics
3. **Test**: Validate with sample content
4. **Monitor**: Track search quality and performance

### Content Type Design

1. **Pattern Matching**: Use specific, non-overlapping patterns
2. **Chunking Strategy**: Match strategy to content structure
3. **Metadata**: Extract relevant metadata for search
4. **Testing**: Validate with representative content

### Performance Optimization

1. **Chunk Sizes**: Optimize based on content type
2. **Overlap**: Balance context vs. performance
3. **Filtering**: Use content type filters for focused searches
4. **Caching**: Consider query result caching

---

*This architecture guide provides the foundation for understanding, extending, and optimizing the Holocron knowledge base system.*
