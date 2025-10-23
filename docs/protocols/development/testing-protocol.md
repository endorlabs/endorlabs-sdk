# Testing Protocol

> **L2 (Task-Specific) - Comprehensive testing requirements and patterns**

## Overview

This protocol defines testing requirements and patterns for the Endor Cockpit SDK, ensuring comprehensive coverage and quality assurance.

## 🎯 **Test Structure Standardization**

### **Improved Approach (Recommended)**
```
tests/
├── test_namespace.py    # All namespace operations
├── test_project.py      # All project operations  
├── test_finding.py      # All finding operations
└── test_tool_*.py       # Tool-specific tests
```

### **Key Benefits**
- **Intuitive Organization**: Follows `endorctl` naming pattern
- **Consolidated Operations**: All resource operations in single files
- **Reduced Redundancy**: Eliminates duplicate test files
- **Maintainable Structure**: Easy to find and update tests
- **Consistent Naming**: `test_<resource>.py` with singular resource names

## Testing Requirements

### Mandatory Test Coverage
- [ ] CRUD tests for all resource operations
- [ ] Integration tests for API interactions
- [ ] Unit tests for individual functions
- [ ] Error handling tests
- [ ] Tag management tests
- [ ] Schema drift detection tests

### Test Validation Requirements
- [ ] **Resource Guide Alignment**: All tests must align with Resource Guide API capabilities
- [ ] **Operation Support Validation**: Only test operations that are actually supported by the API
- [ ] **Test Suite Consistency**: Ensure test suite demonstrates good engineering practices
- [ ] **API Compatibility**: Use Resource Guide as authoritative source for determining test validity

### Test Structure Requirements
- [ ] Use pytest fixtures for setup
- [ ] Mark integration tests with `@pytest.mark.integration`
- [ ] Mark slow tests with `@pytest.mark.slow`
- [ ] Use descriptive test names
- [ ] Include docstrings for test purpose

## Testing Patterns

### Unit Testing Patterns

#### Function Testing
```python
def test_function_success():
    """Test successful function execution."""
    # Arrange
    input_data = "test_input"
    expected_output = "expected_result"
    
    # Act
    result = function_under_test(input_data)
    
    # Assert
    assert result == expected_output

def test_function_validation_error():
    """Test validation error handling."""
    # Arrange
    invalid_input = None
    
    # Act & Assert
    with pytest.raises(ValidationError):
        function_under_test(invalid_input)
```

#### Model Testing
```python
def test_model_creation():
    """Test model creation with valid data."""
    data = {
        "name": "test",
        "description": "test description"
    }
    model = ResourceMeta(**data)
    assert model.name == "test"
    assert model.description == "test description"

def test_model_validation():
    """Test model validation rules."""
    with pytest.raises(ValidationError):
        ResourceMeta(name="")  # Empty name should fail
```

### Integration Testing Patterns

#### API Integration Tests
```python
@pytest.mark.integration
class TestResourceIntegration:
    """Integration tests for Resource operations."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up test environment."""
        self.client = APIClient()
        self.namespace = os.getenv("ENDOR_NAMESPACE", "endor-solutions-tgowan.cockpit")
        self.resources = resource.list_resources(self.client, self.namespace)
        if not self.resources:
            pytest.skip("No resources available for testing")
    
    def test_resource_get_list(self):
        """Test GET resources operation."""
        resources_list = resource.list_resources(self.client, self.namespace)
        assert isinstance(resources_list, list)
        assert len(resources_list) > 0
        
        # Verify structure
        for res in resources_list:
            assert hasattr(res, 'uuid')
            assert hasattr(res, 'meta')
            assert hasattr(res, 'spec')
            assert hasattr(res, 'tenant_meta')
    
    def test_resource_get_by_uuid(self):
        """Test GET resource by UUID operation."""
        test_resource = self.resources[0]
        retrieved_resource = resource.get_resource(
            self.client, self.namespace, test_resource.uuid
        )
        assert retrieved_resource is not None
        assert retrieved_resource.uuid == test_resource.uuid
        assert retrieved_resource.meta.name == test_resource.meta.name
    
    def test_resource_structure_analysis(self):
        """Test and analyze resource structure."""
        resource_obj = self.resources[0]
        
        # Analyze meta fields
        meta_fields = [field for field in dir(resource_obj.meta) if not field.startswith("_")]
        assert len(meta_fields) > 0
        
        # Analyze spec fields
        spec_fields = [field for field in dir(resource_obj.spec) if not field.startswith("_")]
        assert len(spec_fields) > 0
```

### CRUD Testing Patterns

#### CRUD Operation Tests
```python
def test_crud_operations(self):
    """Test complete CRUD lifecycle."""
    # Create
    payload = CreateResourcePayload(
        meta=ResourceMetaCreate(
            name="test-resource",
            description="Test resource"
        )
    )
    created_resource = resource.create_resource(
        self.client, self.namespace, payload
    )
    assert created_resource is not None
    assert created_resource.meta.name == "test-resource"
    
    # Read
    retrieved_resource = resource.get_resource(
        self.client, self.namespace, created_resource.uuid
    )
    assert retrieved_resource is not None
    assert retrieved_resource.uuid == created_resource.uuid
    
    # Update
    update_payload = UpdateResourcePayload(
        meta=ResourceMetaUpdate(description="Updated description")
    )
    updated_resource = resource.update_resource(
        self.client, self.namespace, created_resource.uuid, 
        update_payload, "meta.description"
    )
    assert updated_resource is not None
    assert updated_resource.meta.description == "Updated description"
    
    # Delete
    success = resource.delete_resource(
        self.client, self.namespace, created_resource.uuid
    )
    assert success is True
```

#### Tag Management Tests
```python
def test_tag_management(self):
    """Test tag management operations."""
    resource_obj = self.resources[0]
    test_tag = "test-tag"
    
    # Add tag
    updated_resource = add_resource_tag(
        self.client, self.namespace, resource_obj.uuid, test_tag
    )
    assert updated_resource is not None
    assert test_tag in updated_resource.meta.tags
    
    # List tags
    tags = list_resource_tags(self.client, self.namespace, resource_obj.uuid)
    assert test_tag in tags
    
    # Remove tag
    final_resource = remove_resource_tag(
        self.client, self.namespace, resource_obj.uuid, test_tag
    )
    assert final_resource is not None
    assert test_tag not in final_resource.meta.tags
```

### Error Handling Tests

#### API Error Tests
```python
def test_api_error_handling(self):
    """Test API error handling."""
    # Test 404 error
    result = resource.get_resource(
        self.client, self.namespace, "non-existent-uuid"
    )
    assert result is None
    
    # Test 403 error (if applicable)
    with pytest.raises(HTTPError):
        resource.create_resource(
            self.client, "invalid-namespace", invalid_payload
        )
```

#### Validation Error Tests
```python
def test_validation_errors(self):
    """Test validation error handling."""
    # Test empty name
    with pytest.raises(ValidationError):
        ResourceMetaCreate(name="")
    
    # Test invalid UUID format
    with pytest.raises(ValidationError):
        resource.get_resource(self.client, self.namespace, "invalid-uuid")
```

## 🚨 **PATCH Endpoint Testing Patterns**

### **Common PATCH Debugging Issues**

#### **1. 501 Method Not Allowed Error**
```bash
# WRONG: UUID in URL path
PATCH /v1/namespaces/{namespace}/projects/{uuid}

# CORRECT: UUID in request body
PATCH /v1/namespaces/{namespace}/projects
# Request body: {"object": {"uuid": "...", ...}}
```

#### **2. 400 Bad Request - Missing Required Fields**
```bash
# Problem: API requires full object structure
# Solution: Use update_mask for partial updates
{
  "object": {"uuid": "...", "meta": {"tags": ["new-tag"]}},
  "request": {"update_mask": "meta.tags"}
}
```

#### **3. Tags Not Persisting Despite 200 OK**
```python
# Problem: Pydantic model missing tags field
class ProjectMeta(BaseModel):
    name: str
    description: str
    # Missing: tags field!

# Solution: Add missing field
class ProjectMeta(BaseModel):
    name: str
    description: str
    tags: Optional[List[str]] = None  # Added this!
```

## Test Fixtures and Setup

### Common Fixtures
```python
@pytest.fixture
def api_client():
    """Provide API client for tests."""
    return APIClient()

@pytest.fixture
def test_namespace():
    """Provide test namespace."""
    return os.getenv("ENDOR_NAMESPACE", "endor-solutions-tgowan.cockpit")

@pytest.fixture
def test_resource(api_client, test_namespace):
    """Provide test resource for operations."""
    resources = resource.list_resources(api_client, test_namespace)
    if not resources:
        pytest.skip("No resources available for testing")
    return resources[0]
```

### Test Data Management
```python
@pytest.fixture(autouse=True)
def cleanup_test_data():
    """Clean up test data after each test."""
    yield
    # Cleanup logic here
    pass
```

## Assertion Patterns

### Basic Assertions
```python
# Existence checks
assert result is not None
assert result is not []
assert result is not ""

# Type checks
assert isinstance(result, list)
assert isinstance(result, Resource)
assert isinstance(result, dict)

# Value checks
assert result == expected_value
assert result != unexpected_value
assert result in collection
assert result not in collection
```

### API Response Assertions
```python
# Structure assertions
assert hasattr(resource, 'uuid')
assert hasattr(resource, 'meta')
assert hasattr(resource, 'spec')
assert hasattr(resource, 'tenant_meta')

# Field assertions
assert resource.meta.name is not None
assert resource.meta.name != ""
assert resource.uuid is not None
assert len(resource.uuid) > 0
```

### Error Assertions
```python
# Exception assertions
with pytest.raises(ValidationError):
    invalid_operation()

with pytest.raises(HTTPError) as exc_info:
    api_operation()
    assert exc_info.value.response.status_code == 404
```

## Test Markers

### Standard Markers
```python
@pytest.mark.slow
def test_large_dataset_processing():
    """Test with large datasets."""

@pytest.mark.integration
def test_api_integration():
    """Test real API integration."""

@pytest.mark.security
def test_security_scan():
    """Test security scanning."""
```

### Custom Markers
```python
@pytest.mark.crud
def test_crud_operations():
    """Test CRUD operations."""

@pytest.mark.tag_management
def test_tag_operations():
    """Test tag management operations."""
```

## Success Criteria

- ✅ All CRUD operations tested
- ✅ Integration tests pass
- ✅ Error handling tested
- ✅ Tag management tested
- ✅ Test coverage adequate
- ✅ Tests follow established patterns

## Chunking Guidance

**Note**: If this protocol exceeds 3000 tokens, split by testing category:
- Unit Testing Patterns
- Integration Testing Patterns
- CRUD Testing Patterns
- Error Handling Patterns

## Related Protocols

- [Resource Implementation Protocol](resource-implementation-protocol.md) - For implementation context
- [Development Protocol](development-protocol.md) - For overall workflow
- [Code Commit Protocol](code-commit-protocol.md) - For pre-commit requirements

---

*This protocol ensures comprehensive testing coverage and quality assurance for the SDK.*
