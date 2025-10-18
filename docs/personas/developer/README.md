# Developer Persona Guide

> **SDK Development, Testing, and Contribution**

## 🚀 **Quick Start**

### **5-Minute Setup**
1. **Environment**: Set `ENDOR_API`, `ENDOR_API_CREDENTIALS_KEY`, `ENDOR_API_CREDENTIALS_SECRET`
2. **Install**: `uv pip install -e .`
3. **Test**: `uv run pytest tests/test_integration.py -v`
4. **Security**: `endorctl scan` before any changes
5. **Lint**: `uv run ruff check . --fix`

### **Development Workflow**
```bash
# 1. Pre-development checklist
uv run ruff check .          # Lint
uv run ruff check . --fix    # Auto-fix
uv run ruff format .         # Format
uv run pytest               # Test
endorctl scan               # Security

# 2. Make changes
# 3. Repeat checklist
# 4. Commit with conventional commits
```

---

## 🏗️ **Architecture & Design Principles**

### **Project Structure**
```
endor_cockpit/
├── api_client.py          # Core API client with retry, rate limiting, logging
├── resources/            # Resource-specific modules
│   ├── __init__.py
│   ├── namespaces.py     # Namespace operations
│   └── [other_resources] # Additional resources
└── models/               # Pydantic data models
    └── [model_files]
```

### **Resource Module Pattern**
Each resource module follows this pattern:
- **List operations**: `list_{resource}()`
- **Get operations**: `get_{resource}()`
- **Create operations**: `create_{resource}()`
- **Update operations**: `update_{resource}()`
- **Delete operations**: `delete_{resource}()`

### **Function Signatures**
```python
def create_resource(
    client: APIClient,
    parent_namespace: str,
    payload: CreateResourcePayload
) -> Optional[Resource]:
    """Create resource with proper error handling."""
```

---

## 🔧 **Code Standards & Quality**

### **Python Version Support**
- **Minimum**: Python 3.11
- **Maximum**: Python 3.14 (exclusive)
- **Testing**: Test on 3.11, 3.12, 3.13

### **Dependencies**
- **Core**: `requests==2.32.5`, `pydantic==2.12.3`
- **Development**: `pytest==8.4.2`, `ruff==0.14.1`, `pytest-cov==6.0.0`
- **Security**: `endorctl` (for scanning)

### **Pre-Development Checklist**
- [ ] Line length ≤ 88 characters
- [ ] Imports sorted and unused removed
- [ ] No trailing whitespace or blank line whitespace
- [ ] F-strings only with placeholders
- [ ] Dependencies pinned (no `latest`)

### **Common Linting Fixes**
- **E501**: Break long lines with parentheses/backslashes
- **F401**: Remove unused imports
- **W291/W293**: Remove trailing/blank line whitespace
- **F541**: Remove `f` prefix from strings without placeholders
- **I001**: Sort import blocks

---

## 🧪 **Testing Standards**

### **Test Structure**
```python
def test_create_namespace_success():
    """Test successful namespace creation."""
    
def test_create_namespace_validation_error():
    """Test validation error handling."""
    
def test_create_namespace_api_error():
    """Test API error handling."""
```

### **Test Categories**
- **Unit tests**: Individual function testing
- **Integration tests**: API interaction testing
- **Security tests**: Security scan validation
- **Performance tests**: Load and stress testing

### **Test Markers**
```python
@pytest.mark.slow
def test_large_dataset_processing():
    """Test with large datasets."""

@pytest.mark.integration
def test_api_integration():
    """Test real API integration."""
```

### **Integration Test Patterns**
```python
def test_namespace_hierarchy(api_client, tenant_namespace):
    """Test namespace hierarchy operations."""
    parent_name = f"integration-test-parent-{int(time.time())}"
    
    # Create parent namespace
    parent_namespace = create_test_namespace(
        api_client, tenant_namespace, parent_name, "Parent namespace"
    )
    
    # Create canonical parent name
    canonical_parent = f"{tenant_namespace}.{parent_name}"
    
    # Create child namespace using canonical parent
    child_namespace = create_test_namespace(
        api_client, canonical_parent, child_name, "Child namespace"
    )
    
    # List namespaces under canonical parent
    child_namespaces = namespaces.list_namespaces(api_client, canonical_parent)
    assert len(child_namespaces) > 0
```

---

## 🔒 **Security Integration**

### **Security-First Development**
- **Always scan**: `endorctl scan` before any code changes
- **Scan scenarios**: Package changes, first-party code, dependency updates
- **No PII**: This project handles no PII data
- **Secure logging**: Filter sensitive data from logs

### **Security Scanning Requirements**
```bash
# Required before any code changes
endorctl scan

# For dependency changes
endorctl scan --dependencies

# For first-party code changes
endorctl scan --sast
```

### **Environment Security**
- **Credentials**: Use environment variables only
- **No hardcoded secrets**: All secrets via env vars
- **Secure logging**: No sensitive data in logs
- **Input validation**: Validate all inputs

---

## 📚 **API Client Design**

### **Authentication**
```python
class APIClient:
    def __init__(self):
        # Auto-authentication via environment variables
        # Token refresh handling
        # Rate limiting
```

### **Error Handling**
- **HTTP errors**: Proper status code handling
- **Retries**: Exponential backoff for transient failures
- **Rate limiting**: Respect API limits
- **Validation**: Pydantic model validation

### **Logging**
- **Secure filters**: No PII or sensitive data
- **Structured logging**: JSON format for production
- **Context preservation**: Operation context in logs

---

## 🛠️ **Development Tools**

### **Code Quality Tools**
- **Linting**: `ruff check .`
- **Formatting**: `ruff format .`
- **Testing**: `pytest --cov=endor_cockpit`
- **Security**: `endorctl scan`

### **CI/CD Integration**
- **Automated testing**: Multi-version Python testing
- **Security scanning**: Integrated endorctl scans
- **Caching**: Efficient dependency caching
- **Parallel jobs**: Optimized build times

### **Quality Gates**
- **Linting**: Must pass ruff checks
- **Formatting**: Must pass black checks
- **Testing**: Must pass all tests
- **Security**: Must pass endorctl scan

---

## 📖 **Documentation Standards**

### **Function Documentation**
```python
def create_namespace(
    client: APIClient,
    parent_namespace: str,
    payload: CreateNamespacePayload
) -> Optional[Namespace]:
    """
    Create a new namespace within the specified parent namespace.
    
    Args:
        client: Authenticated API client
        parent_namespace: Parent namespace name (canonical format)
        payload: Namespace creation payload
        
    Returns:
        Created namespace or None if failed
        
    Raises:
        ValidationError: If payload is invalid
        HTTPError: If API request fails
    """
```

### **Example Usage**
```python
# Example: Creating a namespace
from endor_cockpit.api_client import APIClient
from endor_cockpit.resources.namespaces import CreateNamespacePayload, NamespaceMeta

client = APIClient()
payload = CreateNamespacePayload(
    meta=NamespaceMeta(
        name="my-namespace",
        description="Created by developer"
    )
)
namespace = create_namespace(client, "tenant.namespace", payload)
```

---

## 🎯 **Contributing Guidelines**

### **Development Process**
1. **Fork the repository**
2. **Create a feature branch**
3. **Make your changes**
4. **Run tests and linting**
5. **Submit a pull request**

### **Code Review Checklist**
- [ ] All tests passing
- [ ] No linting errors
- [ ] Security scan clean
- [ ] Documentation updated
- [ ] Examples provided

### **Commit Message Format**
```
feat(namespaces): add update_namespace function
fix(api_client): handle 403 errors gracefully
docs(readme): update installation instructions
test(integration): add namespace hierarchy tests
```

---

## 🔍 **Troubleshooting**

### **Common Issues**

#### **403 Forbidden Errors**
1. Check if using canonical naming instead of UUIDs
2. Verify API key has required permissions
3. Confirm parent namespace exists and is accessible

#### **Import Errors**
1. Ensure all required classes are imported
2. Check if SDK classes are missing
3. Verify package installation

#### **Validation Errors**
1. Check Pydantic field definitions
2. Ensure optional fields are properly defined
3. Handle empty values gracefully

### **Debugging Tools**
- **API Client Logging**: Enable debug logging for API calls
- **Integration Tests**: Use real API endpoints for validation
- **Security Scans**: Run `endorctl scan` to identify issues

---

## 📚 **Related Documentation**

- **[Architecture Guide](./architecture.md)**: Endor Data Model deep-dive
- **[API Quirks](./api-quirks.md)**: Known API discrepancies and workarounds
- **[Testing Guide](./testing-guide.md)**: Comprehensive testing patterns
- **[Contributing Guide](./contributing.md)**: How to extend the SDK

---

## 🎉 **Success Metrics**

When everything is working correctly, you should see:
- ✅ All integration tests passing
- ✅ Namespace hierarchy operations working
- ✅ Security scanning integration working
- ✅ Error handling working gracefully
- ✅ Rate limiting compliance

**The Endor Cockpit SDK is production-ready and fully validated against the live Endor Labs API!** 🚀
