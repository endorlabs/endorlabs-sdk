# Development Guidelines for AI Agents

## 1. Project Structure

### Package Organization
```
endor_cockpit/
├── api_client.py          # Core API client
├── resources/            # Resource-specific modules
│   ├── __init__.py
│   ├── namespaces.py     # Namespace operations
│   └── [other_resources] # Additional resources
└── models/               # Pydantic data models
    └── [model_files]
```

### Resource Module Pattern
Each resource module should follow this pattern:
- **List operations**: `list_{resource}()`
- **Get operations**: `get_{resource}()`
- **Create operations**: `create_{resource}()`
- **Update operations**: `update_{resource}()`
- **Delete operations**: `delete_{resource}()`

### Consistent Architecture Patterns
All resource modules must follow the established patterns from `project.py`:

#### **Documentation Standards**
- **Mutable/Immutable Fields**: Document which fields can be updated via PATCH operations
- **Comprehensive Examples**: Include practical usage examples in docstrings
- **Field Validation**: Document required fields and validation rules

#### **API Payload Structure**
- **Update Functions**: Include current resource data in API payloads to avoid validation errors
- **Required Fields**: Always include immutable required fields (e.g., `meta.name`, `tenant_meta`)
- **Field Merging**: Properly merge update payloads with existing resource data

#### **Logging and Error Handling**
- **Consistent Logging**: Use `logger.info()` for update operations with resource UUID and update mask
- **Error Handling**: Consistent error handling with proper logging and exception details
- **Validation**: Proper field validation and error reporting

#### **Code Structure**
- **Function Signatures**: Consistent parameter patterns across all resources
- **Return Types**: All functions return `Optional[Resource]` for consistency
- **Documentation**: Comprehensive docstrings with examples and field descriptions

**Reference**: See `src/endor_cockpit/resources/project.py` as the canonical implementation pattern.

## 2. Code Standards

### Python Version Support
- **Minimum**: Python 3.11
- **Maximum**: Python 3.14 (exclusive)
- **Testing**: Test on 3.11, 3.12, 3.13

### Dependencies
- **Core**: requests, pydantic
- **Development**: pytest, black, ruff, pytest-cov
- **Security**: endorctl (for scanning)

### Code Quality Tools
- **Linting**: `ruff check .`
- **Formatting**: `black --check .`
- **Testing**: `pytest --cov=endor_cockpit`

## 2.1. Linting & CI Error Prevention

### **CRITICAL: Pre-Development Checklist**
Before writing any code, ensure you understand these requirements:

#### **Line Length Standards**
- **Maximum line length**: 88 characters (configured in `pyproject.toml`)
- **Break long lines** using parentheses, backslashes, or string concatenation
- **Function signatures**: Break parameter lists across multiple lines
- **Import statements**: Use multi-line imports for long module lists

#### **Import Management**
```python
# ✅ CORRECT: Sorted imports with proper grouping
import os
import sys
from typing import Optional, Union

from requests import HTTPError
from pydantic import BaseModel, Field

from endor_cockpit.api_client import APIClient
from endor_cockpit.resources.namespaces import CreateNamespacePayload

# ❌ WRONG: Unsorted imports, unused imports
import json  # F401: unused import
import urllib3  # F401: unused import
from typing import Union  # F401: unused import
```

#### **Whitespace & Formatting**
- **No trailing whitespace**: Remove spaces at end of lines
- **No blank lines with whitespace**: Empty lines should be truly empty
- **Consistent indentation**: Use 4 spaces, never tabs
- **F-string usage**: Only use f-strings when you have placeholders

```python
# ✅ CORRECT: Proper f-string usage
name = "test"
message = f"Hello {name}"

# ❌ WRONG: F-string without placeholders
message = f"Hello world"  # Should be: message = "Hello world"
```

#### **Dependency Management**
- **Pin exact versions**: Use `==` for core dependencies
- **Avoid `latest`**: Specify exact versions in `pyproject.toml`
- **Dev dependencies**: Keep dev tools in `[project.optional-dependencies.dev]`
- **Version compatibility**: Ensure Python version constraints are correct

#### **Configuration Standards**
```toml
# ✅ CORRECT: Proper pyproject.toml structure
[tool.ruff.lint]
select = ["E", "W", "F", "I", "C", "B"]

[tool.black]
line-length = 88

[tool.ruff]
line-length = 88
```

### **Common Linting Errors & Fixes**

#### **E501: Line too long**
```python
# ❌ WRONG: Line too long
def create_namespace(client: APIClient, parent_namespace: str, payload: CreateNamespacePayload) -> Optional[Namespace]:

# ✅ CORRECT: Break into multiple lines
def create_namespace(
    client: APIClient,
    parent_namespace: str,
    payload: CreateNamespacePayload
) -> Optional[Namespace]:
```

#### **F401: Imported but unused**
```python
# ❌ WRONG: Unused imports
import json
import urllib3
from typing import Union

# ✅ CORRECT: Remove unused imports
# Only import what you use
```

#### **W291: Trailing whitespace**
```python
# ❌ WRONG: Trailing spaces
def function():    
    return "value"    

# ✅ CORRECT: No trailing spaces
def function():
    return "value"
```

#### **W293: Blank line contains whitespace**
```python
# ❌ WRONG: Blank line with spaces
def function():
    
    return "value"

# ✅ CORRECT: Truly empty blank lines
def function():

    return "value"
```

#### **I001: Import block is un-sorted**
```python
# ❌ WRONG: Unsorted imports
from endor_cockpit.api_client import APIClient
import os
from typing import Optional

# ✅ CORRECT: Sorted imports
import os
from typing import Optional

from endor_cockpit.api_client import APIClient
```

### **Pre-Commit Workflow**
1. **Run linting**: `uv run ruff check .`
2. **Fix auto-fixable issues**: `uv run ruff check . --fix`
3. **Check formatting**: `uv run black --check .`
4. **Format code**: `uv run ruff format .`
5. **Run tests**: `uv run pytest`
6. **Security scan**: `endorctl scan`

### **CI Error Prevention**
- **Dependency resolution**: Use `uv sync --dev` for consistent environments
- **Version pinning**: Never use `latest` in production dependencies
- **Test coverage**: Maintain comprehensive test coverage
- **Security scanning**: Always run `endorctl scan` before commits
- **Multi-version testing**: Ensure compatibility across Python versions

## 3. API Client Design

### Authentication
```python
class APIClient:
    def __init__(self):
        # Auto-authentication via environment variables
        # Token refresh handling
        # Rate limiting
```

### Error Handling
- **HTTP errors**: Proper status code handling
- **Retries**: Exponential backoff for transient failures
- **Rate limiting**: Respect API limits
- **Validation**: Pydantic model validation

### Logging
- **Secure filters**: No PII or sensitive data
- **Structured logging**: JSON format for production
- **Context preservation**: Operation context in logs

## 4. Resource Implementation

### Function Signatures
```python
def create_namespace(
    client: APIClient,
    parent_namespace: str,
    payload: CreateNamespacePayload
) -> Optional[Namespace]:
    """Create a new namespace with proper error handling."""
```

### Error Handling Pattern
```python
try:
    response = client.post(endpoint, json=payload.dict())
    response.raise_for_status()
    return Namespace.parse_obj(response.json())
except HTTPError as e:
    logger.error(f"Failed to create namespace: {e}")
    return None
```

### Type Safety
- **Pydantic models**: All data structures
- **Type hints**: Complete function signatures
- **Validation**: Input/output validation

## 5. Testing Standards

### Test Structure
```python
def test_create_namespace_success():
    """Test successful namespace creation."""
    
def test_create_namespace_validation_error():
    """Test validation error handling."""
    
def test_create_namespace_api_error():
    """Test API error handling."""
```

### Test Categories
- **Unit tests**: Individual function testing
- **Integration tests**: API interaction testing
- **Security tests**: Security scan validation
- **Performance tests**: Load and stress testing

### Test Markers
```python
@pytest.mark.slow
def test_large_dataset_processing():
    """Test with large datasets."""

@pytest.mark.integration
def test_api_integration():
    """Test real API integration."""
```

## 6. Security Integration

### Security Scanning
- **Pre-commit**: Run `endorctl scan` before commits
- **CI/CD**: Automated security scanning in pipeline
- **Dependencies**: Scan all package changes
- **Code changes**: Scan first-party code modifications

### Security Best Practices
- **No hardcoded secrets**: Use environment variables
- **Secure logging**: Filter sensitive data
- **Input validation**: Validate all inputs
- **Output sanitization**: Clean output data

## 7. Documentation Standards

### Function Documentation
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
        parent_namespace: Parent namespace name
        payload: Namespace creation payload
        
    Returns:
        Created namespace or None if failed
        
    Raises:
        ValidationError: If payload is invalid
        HTTPError: If API request fails
    """
```

### Example Usage
```python
# Example: Creating a namespace
from endor_cockpit.api_client import APIClient
from endor_cockpit.resources.namespaces import CreateNamespacePayload

client = APIClient()
payload = CreateNamespacePayload(
    meta=NamespaceMeta(
        name="my-namespace",
        description="Created by agent"
    )
)
namespace = create_namespace(client, "tenant", payload)
```

## 8. CI/CD Integration

### Workflow Structure
- **Lint job**: Code quality checks
- **Test job**: Multi-version testing
- **Security job**: Security scanning
- **Caching**: Dependency caching

### Quality Gates
- **Linting**: Must pass ruff checks
- **Formatting**: Must pass black checks
- **Testing**: Must pass all tests
- **Security**: Must pass endorctl scan

## 9. Agent Integration

### Tool Definitions
Create LLM tool schemas for each resource function:
```json
{
  "name": "create_namespace",
  "description": "Create a new namespace",
  "parameters": {
    "type": "object",
    "properties": {
      "parent_namespace": {"type": "string"},
      "name": {"type": "string"},
      "description": {"type": "string"}
    },
    "required": ["parent_namespace", "name", "description"]
  }
}
```

### Error Handling for Agents
- **Predictable errors**: Consistent error responses
- **Actionable messages**: Clear error descriptions
- **Recovery guidance**: How to fix common issues
- **Context preservation**: Maintain operation context

## 10. Performance Considerations

### Caching Strategy
- **API responses**: Cache where appropriate
- **Authentication**: Token caching
- **Dependencies**: CI/CD caching

### Resource Management
- **Connection pooling**: Reuse HTTP connections
- **Memory usage**: Efficient data structures
- **Rate limiting**: Respect API limits

### Monitoring
- **Metrics**: Performance metrics
- **Logging**: Structured logging
- **Alerting**: Error rate monitoring
