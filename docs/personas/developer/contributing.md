# Contributing Guide

> **How to extend and contribute to the Endor Cockpit SDK**

## 🚀 **Getting Started**

### **Development Setup**
1. **Fork the repository**
2. **Clone your fork**: `git clone https://github.com/your-username/endor-cockpit.git`
3. **Install dependencies**: `uv pip install -e .`
4. **Run tests**: `uv run pytest`
5. **Run security scan**: `endorctl scan`

### **Development Workflow**
```bash
# 1. Create feature branch
git checkout -b feat/your-feature-name

# 2. Make changes
# 3. Run pre-commit checks
uv run ruff check . --fix
uv run ruff format .
uv run pytest
endorctl scan

# 4. Commit with conventional commits
git commit -m "feat(namespaces): add update_namespace function"

# 5. Push and create PR
git push origin feat/your-feature-name
```

---

## 🏗️ **Architecture Guidelines**

### **Resource Module Pattern**
Each resource module should follow this pattern:

```python
# resources/namespaces.py
from typing import List, Optional
from endor_cockpit.api_client import APIClient
from endor_cockpit.models.namespaces import (
    Namespace, CreateNamespacePayload, UpdateNamespacePayload
)

def list_namespaces(
    client: APIClient, 
    parent_namespace: str
) -> List[Namespace]:
    """List namespaces in a parent namespace."""
    # Implementation here

def get_namespace(
    client: APIClient, 
    parent_namespace: str, 
    namespace_uuid: str
) -> Optional[Namespace]:
    """Get a specific namespace."""
    # Implementation here

def create_namespace(
    client: APIClient, 
    parent_namespace: str, 
    payload: CreateNamespacePayload
) -> Optional[Namespace]:
    """Create a new namespace."""
    # Implementation here

def update_namespace(
    client: APIClient, 
    parent_namespace: str, 
    namespace_uuid: str, 
    payload: UpdateNamespacePayload
) -> Optional[Namespace]:
    """Update an existing namespace."""
    # Implementation here

def delete_namespace(
    client: APIClient, 
    parent_namespace: str, 
    namespace_uuid: str
) -> bool:
    """Delete a namespace."""
    # Implementation here
```

### **Pydantic Model Pattern**
```python
# models/namespaces.py
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field

class NamespaceMeta(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str = Field("")  # Empty descriptions allowed
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class Namespace(BaseModel):
    uuid: str
    meta: NamespaceMeta

class NamespaceMetaCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str = Field("")

class CreateNamespacePayload(BaseModel):
    meta: NamespaceMetaCreate

class NamespaceMetaUpdate(BaseModel):
    description: Optional[str] = Field(None)

class UpdateNamespacePayload(BaseModel):
    meta: NamespaceMetaUpdate
```

---

## 🔧 **Code Standards**

### **Python Version Support**
- **Minimum**: Python 3.11
- **Maximum**: Python 3.13 (exclusive)
- **Testing**: Test on 3.11, 3.12, 3.13

### **Dependencies**
- **Core**: `requests==2.32.5`, `pydantic==2.12.3`
- **Development**: `pytest==8.4.2`, `ruff==0.14.1`, `pytest-cov==6.0.0`
- **Security**: `endorctl` (for scanning)

### **Code Quality Requirements**
- **Line length**: ≤ 88 characters
- **Imports**: Sorted and unused removed
- **Whitespace**: No trailing whitespace or blank line whitespace
- **F-strings**: Only use when placeholders are present
- **Dependencies**: Pin exact versions, avoid `latest`

### **Pre-Development Checklist**
- [ ] Line length ≤ 88 characters
- [ ] Imports sorted and unused removed
- [ ] No trailing whitespace or blank line whitespace
- [ ] F-strings only with placeholders
- [ ] Dependencies pinned (no `latest`)

---

## 🧪 **Testing Requirements**

### **Test Coverage**
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

---

## 🔒 **Security Requirements**

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

### **Input Validation**
```python
def validate_input(input_data: str) -> str:
    """Validate and sanitize input data."""
    # Remove potential XSS
    sanitized = input_data.replace('<', '&lt;').replace('>', '&gt;')
    # Remove potential SQL injection
    sanitized = sanitized.replace("'", "''")
    return sanitized
```

---

## 📚 **Documentation Requirements**

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
        
    Example:
        >>> client = APIClient()
        >>> payload = CreateNamespacePayload(
        ...     meta=NamespaceMeta(name="test", description="Test namespace")
        ... )
        >>> namespace = create_namespace(client, "tenant.namespace", payload)
        >>> print(namespace.uuid)
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
        description="Created by contributor"
    )
)
namespace = create_namespace(client, "tenant.namespace", payload)
```

---

## 🎯 **Pull Request Process**

### **Before Submitting**
1. **Run all checks**: `uv run ruff check . --fix && uv run pytest && endorctl scan`
2. **Update documentation**: Add/update relevant documentation
3. **Add tests**: Include tests for new functionality
4. **Update changelog**: Document changes in CHANGELOG.md

### **Pull Request Template**
```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
- [ ] Unit tests pass
- [ ] Integration tests pass
- [ ] Security scan passes
- [ ] Manual testing completed

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Documentation updated
- [ ] Tests added/updated
```

### **Code Review Checklist**
- [ ] All tests passing
- [ ] No linting errors
- [ ] Security scan clean
- [ ] Documentation updated
- [ ] Examples provided
- [ ] Breaking changes documented

---

## 🔄 **Release Process**

### **Version Bumping**
- **Patch**: Bug fixes, documentation updates
- **Minor**: New features, backward-compatible changes
- **Major**: Breaking changes

### **Release Checklist**
- [ ] All tests passing
- [ ] Security scan clean
- [ ] Documentation updated
- [ ] Changelog updated
- [ ] Version bumped
- [ ] Release notes prepared

---

## 🎯 **Best Practices**

### **Code Organization**
- **Single responsibility**: Each function should do one thing
- **Clear naming**: Use descriptive names for functions and variables
- **Consistent patterns**: Follow established patterns in the codebase
- **Error handling**: Handle errors gracefully with meaningful messages

### **Testing**
- **Test coverage**: Aim for high test coverage
- **Test isolation**: Tests should not depend on each other
- **Test data**: Use realistic test data
- **Clean up**: Always clean up test data

### **Documentation**
- **Keep it current**: Update documentation with code changes
- **Be specific**: Provide concrete examples
- **Explain why**: Document the reasoning behind decisions
- **Link related docs**: Cross-reference related documentation

---

## 📚 **Related Documentation**

- **[Architecture Guide](./architecture.md)**: Understanding the data model
- **[API Quirks](./api-quirks.md)**: Known issues and workarounds
- **[Testing Guide](./testing-guide.md)**: Testing patterns and examples

---

## 🆘 **Getting Help**

### **Resources**
- **Documentation**: Check existing documentation first
- **Issues**: Search existing issues for similar problems
- **Discussions**: Use GitHub discussions for questions
- **Security**: Report security issues privately

### **Contact**
- **Maintainers**: [List maintainers]
- **Security**: [Security contact]
- **General**: [General contact]

---

*This contributing guide helps maintain code quality and consistency across the Endor Cockpit SDK.*
