# Endor Cockpit Architecture

> **Comprehensive architectural overview for LLM-friendly development**

## 🏗️ **System Architecture**

### **Core Principles**
- **Resource-Oriented**: All operations follow REST principles
- **Type-Safe**: Pydantic models ensure data integrity
- **Agent-Optimized**: Designed for both human and AI agent usage
- **Schema-Aware**: Built-in drift detection for API evolution

### **Module Organization**

```
src/endor_cockpit/
├── models/          # Data models (Pydantic)
├── operations/      # CRUD operations
├── utils/           # Shared utilities
├── rag/             # RAG functionality
└── api_client.py    # Core API client
```

### **Design Patterns**

#### **1. Base Model Pattern**
All resources inherit from `BaseResource` with consistent metadata:
- `uuid`: Unique identifier
- `meta`: Resource metadata (name, description, timestamps, tags)
- `spec`: Resource-specific data
- `tenant_meta`: Namespace information

#### **2. Schema Drift Detection**
Automatic detection of API evolution:
- Unknown fields logged as warnings
- Non-breaking changes handled gracefully
- Early warning system for API updates

#### **3. Validation Pipeline**
Multi-layer validation:
- Pydantic model validation
- Business logic validation
- API format validation

### **LLM-Friendly Features**

#### **Consistent Naming**
- Resource names: `Project`, `Finding`, `Policy`, `Namespace`
- Operation names: `list_*`, `get_*`, `create_*`, `update_*`, `delete_*`
- Field names: `meta.name`, `spec.level`, `tenant_meta.namespace`

#### **Type Hints**
- Complete type annotations for all functions
- Generic types for collections
- Optional types clearly marked

#### **Documentation**
- Comprehensive docstrings for all functions
- Examples in docstrings
- Clear parameter descriptions

### **Error Handling**

#### **Graceful Degradation**
- Schema drift warnings (non-blocking)
- Validation errors with clear messages
- Network errors with retry logic

#### **Logging Strategy**
- Structured logging with context
- Different levels for different concerns
- Redaction for sensitive data

### **Testing Strategy**

#### **Unit Tests**
- Model validation tests
- Operation tests with mocks
- Utility function tests

#### **Integration Tests**
- End-to-end API tests
- Schema drift detection tests
- Error handling tests

### **Performance Considerations**

#### **Caching**
- API response caching
- Model validation caching
- RAG query caching

#### **Optimization**
- Lazy loading for large datasets
- Pagination for list operations
- Batch operations where possible

### **Security**

#### **Data Protection**
- No PII in logs
- Secure credential management
- Input sanitization

#### **Access Control**
- Namespace-based isolation
- Role-based permissions
- API key management

---

*This architecture is designed to be intuitive for both human developers and AI agents, with clear patterns and comprehensive documentation.*
