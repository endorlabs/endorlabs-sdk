# Development Protocol

> **L1 (Essential - Always Required) - Feature implementation workflow**

## Overview

This protocol guides the implementation of new features, ensuring consistency with existing patterns and comprehensive documentation.

## Development Workflow

### 1. Research Phase
- [ ] **MANDATORY**: Complete [API Validation Protocol](api-validation-protocol.md) first
- [ ] Analyze OpenAPI spec for service endpoints
- [ ] Test with endorctl for live data structure
- [ ] **CRITICAL**: Validate schema matches between OpenAPI spec and live data
- [ ] Identify canonical implementations (use project.py as north star)
- [ ] Search related documentation if ambiguous

### 2. Planning Phase
- [ ] Create implementation plan
- [ ] Identify required CRUD operations
- [ ] Plan Pydantic model structure
- [ ] Design test strategy
- [ ] User validation checkpoint

### 3. Documentation Context Phase
- [ ] Query holocron for semantic patterns: `python -m holocron query "your question"`
- [ ] Extract documentation context and examples
- [ ] Identify best practices and common patterns
- [ ] Gather real-world usage examples

### 4. Implementation Phase
- [ ] Follow [Resource Implementation Protocol](resource-implementation-protocol.md)
- [ ] Implement CRUD operations following project.py patterns
- [ ] Add comprehensive docstrings with examples from context phase
- [ ] Configure schema drift detection
- [ ] Implement field validation

### 5. Testing Phase
- [ ] Follow [Testing Protocol](testing-protocol.md)
- [ ] Write CRUD tests mirroring test_project.py
- [ ] Add integration tests
- [ ] Test tag management operations
- [ ] Validate error handling

### 6. Documentation Phase
- [ ] Create resource documentation using project.md template
- [ ] Document all operations with code examples
- [ ] Add troubleshooting section
- [ ] Update cross-references

## Implementation Patterns

### Resource Module Structure
```python
# Follow project.py patterns
def list_resources(client: APIClient, tenant_meta_namespace: str) -> List[Resource]:
    """List all resources in namespace."""
    
def get_resource(client: APIClient, tenant_meta_namespace: str, resource_uuid: str) -> Optional[Resource]:
    """Get specific resource by UUID."""
    
def create_resource(client: APIClient, tenant_meta_namespace: str, payload: CreateResourcePayload) -> Optional[Resource]:
    """Create new resource."""
    
def update_resource(client: APIClient, tenant_meta_namespace: str, resource_uuid: str, payload: UpdateResourcePayload, update_mask: Optional[str] = None) -> Optional[Resource]:
    """Update existing resource."""
    
def delete_resource(client: APIClient, tenant_meta_namespace: str, resource_uuid: str) -> bool:
    """Delete resource."""
```

### Pydantic Model Patterns
```python
class ResourceMeta(BaseModel):
    """Resource metadata."""
    name: str
    description: Optional[str] = None
    create_time: Optional[str] = None
    # ... other fields

class Resource(BaseModel):
    """Resource entity."""
    uuid: str
    meta: ResourceMeta
    spec: ResourceSpec
    tenant_meta: TenantMeta
    
    @field_validator('*', mode='before')
    @classmethod
    def detect_schema_drift(cls, v, info):
        """Detect and log schema drift."""
        # Schema drift detection implementation
        return v
```

## Success Criteria

- ✅ Feature implemented following project.py patterns
- ✅ All CRUD operations working
- ✅ Comprehensive tests written
- ✅ Documentation complete
- ✅ Schema drift detection configured
- ✅ Error handling graceful

## Related Protocols

- [Resource Implementation Protocol](resource-implementation-protocol.md) - Detailed implementation steps
- [Testing Protocol](testing-protocol.md) - Testing requirements
- [Code Commit Protocol](code-commit-protocol.md) - Pre-commit requirements

---

*This protocol ensures consistent, high-quality feature implementation across the SDK.*
