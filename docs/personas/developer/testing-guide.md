# Testing Guide

> **Comprehensive testing patterns and examples**

## 🧪 **Testing Strategy**

### **Test Categories**
- **Unit tests**: Individual function testing
- **Integration tests**: API interaction testing
- **Security tests**: Security scan validation
- **Performance tests**: Load and stress testing

### **Test Structure**
```python
def test_create_namespace_success():
    """Test successful namespace creation."""
    
def test_create_namespace_validation_error():
    """Test validation error handling."""
    
def test_create_namespace_api_error():
    """Test API error handling."""
```

---

## 🔧 **Unit Testing Patterns**

### **Function Testing**
```python
def test_create_namespace_payload_validation():
    """Test namespace creation payload validation."""
    # Test valid payload
    valid_payload = CreateNamespacePayload(
        meta=NamespaceMeta(name="test", description="Test namespace")
    )
    assert valid_payload.meta.name == "test"
    
    # Test invalid payload
    with pytest.raises(ValidationError):
        CreateNamespacePayload(
            meta=NamespaceMeta(name="", description="Test")  # Empty name
        )
```

### **Error Handling Testing**
```python
def test_api_client_error_handling():
    """Test API client error handling."""
    client = APIClient()
    
    # Test 403 Forbidden
    with pytest.raises(HTTPError) as exc_info:
        namespaces.create_namespace(client, "invalid-parent", payload)
    assert exc_info.value.response.status_code == 403
```

---

## 🔗 **Integration Testing Patterns**

### **Namespace Hierarchy Testing**
```python
def test_namespace_hierarchy(api_client, tenant_namespace):
    """Test namespace hierarchy operations."""
    parent_name = f"integration-test-parent-{int(time.time())}"
    
    # Create parent namespace
    parent_namespace = create_test_namespace(
        api_client, tenant_namespace, parent_name, "Parent namespace"
    )
    assert parent_namespace is not None
    
    # Create canonical parent name
    canonical_parent = f"{tenant_namespace}.{parent_name}"
    
    # Create child namespace using canonical parent
    child_name = f"integration-test-child-{int(time.time())}"
    child_namespace = create_test_namespace(
        api_client, canonical_parent, child_name, "Child namespace"
    )
    assert child_namespace is not None
    
    # List namespaces under canonical parent
    child_namespaces = namespaces.list_namespaces(api_client, canonical_parent)
    assert len(child_namespaces) > 0
    
    # Clean up
    namespaces.delete_namespace(api_client, canonical_parent, child_namespace.uuid)
    namespaces.delete_namespace(api_client, tenant_namespace, parent_namespace.uuid)
```

### **Permission Testing Pattern**
```python
def test_permissions(api_client, tenant_namespace):
    """Test what operations are allowed."""
    # Test tenant-level operations
    test_payload = CreateNamespacePayload(
        meta=NamespaceMeta(name="test", description="Test")
    )
    result = namespaces.create_namespace(api_client, tenant_namespace, test_payload)
    assert result is not None  # Should work
    
    # Test hierarchy operations
    canonical_parent = f"{tenant_namespace}.test-parent"
    result = namespaces.create_namespace(api_client, canonical_parent, test_payload)
    assert result is not None  # Should work if permissions allow
```

### **Error Recovery Testing**
```python
def test_error_recovery(api_client, tenant_namespace):
    """Test error recovery patterns."""
    # Test 403 Forbidden recovery
    with pytest.raises(HTTPError) as exc_info:
        namespaces.create_namespace(api_client, "invalid-parent", payload)
    assert exc_info.value.response.status_code == 403
    
    # Test retry logic
    result = retry_operation(
        lambda: namespaces.create_namespace(api_client, tenant_namespace, payload),
        max_retries=3
    )
    assert result is not None
```

---

## 🔒 **Security Testing Patterns**

### **Security Scan Testing**
```python
def test_security_scan_integration():
    """Test security scan integration."""
    # Run security scan
    scan_result = subprocess.run(
        ["endorctl", "scan"],
        capture_output=True,
        text=True
    )
    assert scan_result.returncode == 0
    assert "No vulnerabilities found" in scan_result.stdout
```

### **Input Validation Testing**
```python
def test_input_validation():
    """Test input validation for security."""
    # Test XSS prevention
    malicious_input = "<script>alert('xss')</script>"
    sanitized = sanitize_input(malicious_input)
    assert "<script>" not in sanitized
    
    # Test SQL injection prevention
    sql_injection = "'; DROP TABLE users; --"
    sanitized = sanitize_input(sql_injection)
    assert "DROP TABLE" not in sanitized
```

---

## 📊 **Performance Testing Patterns**

### **Load Testing**
```python
def test_namespace_creation_performance():
    """Test namespace creation performance."""
    start_time = time.time()
    
    # Create multiple namespaces
    for i in range(10):
        payload = CreateNamespacePayload(
            meta=NamespaceMeta(name=f"test-{i}", description="Performance test")
        )
        namespaces.create_namespace(api_client, tenant_namespace, payload)
    
    end_time = time.time()
    duration = end_time - start_time
    
    # Should complete within reasonable time
    assert duration < 30  # 30 seconds for 10 namespaces
```

### **Rate Limiting Testing**
```python
def test_rate_limiting():
    """Test rate limiting behavior."""
    # Make rapid requests
    for i in range(100):
        try:
            namespaces.list_namespaces(api_client, tenant_namespace)
        except HTTPError as e:
            if e.response.status_code == 429:  # Rate limited
                break
    else:
        pytest.fail("Rate limiting not triggered")
```

---

## 🎯 **Test Markers and Configuration**

### **Test Markers**
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

### **Test Configuration**
```python
# pytest.ini
[tool:pytest]
markers =
    slow: marks tests as slow (deselect with '-m "not slow"')
    integration: marks tests as integration tests
    security: marks tests as security tests
```

---

## 🔍 **Debugging Test Failures**

### **Common Test Issues**

#### **403 Forbidden in Tests**
```python
def test_namespace_creation_with_debug():
    """Test namespace creation with debugging."""
    try:
        result = namespaces.create_namespace(api_client, parent_namespace, payload)
        assert result is not None
    except HTTPError as e:
        if e.response.status_code == 403:
            # Debug: Check if using canonical naming
            assert "." in parent_namespace, "Use canonical naming for parent_namespace"
            raise
```

#### **Import Errors in Tests**
```python
def test_import_validation():
    """Test that all required classes are imported."""
    from endor_cockpit.resources.namespaces import (
        CreateNamespacePayload,
        UpdateNamespacePayload,
        NamespaceMeta,
        NamespaceMetaCreate,
        NamespaceMetaUpdate
    )
    # All imports should succeed
```

#### **Validation Errors in Tests**
```python
def test_pydantic_validation():
    """Test Pydantic model validation."""
    # Test valid model
    valid_meta = NamespaceMeta(name="test", description="")
    assert valid_meta.name == "test"
    assert valid_meta.description == ""
    
    # Test invalid model
    with pytest.raises(ValidationError):
        NamespaceMeta(name="", description="test")  # Empty name
```

---

## 📚 **Test Data Management**

### **Test Fixtures**
```python
@pytest.fixture
def api_client():
    """Create API client for testing."""
    return APIClient()

@pytest.fixture
def tenant_namespace():
    """Get tenant namespace for testing."""
    return os.getenv("ENDOR_NAMESPACE", "endor-solutions-tgowan.cockpit")

@pytest.fixture
def test_namespace_payload():
    """Create test namespace payload."""
    return CreateNamespacePayload(
        meta=NamespaceMeta(
            name=f"test-{int(time.time())}",
            description="Test namespace"
        )
    )
```

### **Test Cleanup**
```python
@pytest.fixture(autouse=True)
def cleanup_test_namespaces(api_client, tenant_namespace):
    """Clean up test namespaces after each test."""
    yield
    # Clean up logic here
    pass
```

---

## 🎯 **Best Practices**

### **Test Organization**
- **One test per scenario**: Each test should test one specific behavior
- **Descriptive names**: Test names should clearly describe what they test
- **Independent tests**: Tests should not depend on each other
- **Clean up**: Always clean up test data

### **Test Data**
- **Unique names**: Use timestamps or UUIDs for unique test data
- **Minimal data**: Use only the data necessary for the test
- **Realistic data**: Use data that reflects real-world usage

### **Error Testing**
- **Test all error paths**: Cover both success and failure scenarios
- **Meaningful assertions**: Assertions should clearly indicate what went wrong
- **Error recovery**: Test that errors are handled gracefully

---

## 📚 **Related Documentation**

- **[Architecture Guide](./architecture.md)**: Understanding the data model
- **[API Quirks](./api-quirks.md)**: Known issues and workarounds
- **[Contributing Guide](./contributing.md)**: How to add new tests

---

*This testing guide provides comprehensive patterns for testing Endor Cockpit SDK functionality.*
