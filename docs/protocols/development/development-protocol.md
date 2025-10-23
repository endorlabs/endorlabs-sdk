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
- [ ] Query holocron for semantic patterns: `uv run python -m holocron query "your question"`
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
- **Maximum**: Python 3.13 (exclusive)
- **Testing**: Test on 3.13

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
from endor_cockpit.resources.namespace import CreateNamespacePayload

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
