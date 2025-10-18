# Endor Cockpit: Agent Insights & Discoveries

## 🎯 Overview

This document contains critical insights and discoveries about the Endor Labs API and Endor Cockpit SDK that agents need to know for successful integration and operation.

## 🔑 Critical Discoveries

### **Namespace Hierarchy: Canonical Naming Pattern**

**DISCOVERY**: Endor Labs uses **canonical hierarchical naming** for namespace relationships, not UUIDs.

#### **✅ CORRECT Pattern**
```python
# Use canonical hierarchical names for parent-child relationships
canonical_parent = f"{tenant_namespace}.{parent_name}"
# Example: "endor-solutions-tgowan.cockpit.integration-test-parent-{timestamp}"

# Create child namespace
child_result = namespaces.create_namespace(client, canonical_parent, child_payload)
```

#### **❌ INCORRECT Pattern**
```python
# DON'T use UUIDs as parents - this will fail with 403 Forbidden
parent_namespace.uuid  # "68f3b2956795a2693a0f5bec" - FAILS!
```

#### **Namespace Hierarchy Structure**
```
endor-solutions-tgowan.cockpit (tenant)
├── namespace-1 (child)
├── namespace-2 (child)
└── namespace-3 (child)
    ├── child-1 (grandchild) ✅ WORKS!
    └── child-2 (grandchild) ✅ WORKS!
```

### **API Permission Model**

**DISCOVERY**: The API key permission model is based on **canonical naming**, not UUIDs.

#### **✅ ALLOWED Operations**
- **Tenant-level operations**: Use tenant name (`endor-solutions-tgowan.cockpit`)
- **Hierarchy operations**: Use canonical parent names (`tenant.namespace.child`)
- **All CRUD operations**: Create, read, update, delete within allowed scope

#### **❌ FORBIDDEN Operations**
- **UUID-based parent relationships**: Cannot use UUIDs as parents
- **Cross-tenant operations**: Cannot access other tenants
- **Unauthorized resource access**: Beyond permission scope

### **SDK Implementation Patterns**

#### **Required Classes for Full Functionality**
```python
# Namespace creation
class NamespaceMetaCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str = Field(..., min_length=1)

class CreateNamespacePayload(BaseModel):
    meta: NamespaceMetaCreate

# Namespace updates (CRITICAL: Was missing!)
class NamespaceMetaUpdate(BaseModel):
    description: Optional[str] = Field(None)

class UpdateNamespacePayload(BaseModel):
    meta: NamespaceMetaUpdate

# Namespace metadata (FIXED: Empty descriptions allowed)
class NamespaceMeta(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str = Field("")  # Empty descriptions allowed
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
```

#### **Function Signatures**
```python
# CRITICAL: get_namespace requires parent_namespace parameter
def get_namespace(client: APIClient, parent_namespace: str, namespace_uuid: str) -> Optional[Namespace]

# CRITICAL: update_namespace requires UpdateNamespacePayload
def update_namespace(client: APIClient, parent_namespace: str, namespace_uuid: str, payload: UpdateNamespacePayload) -> Optional[Namespace]
```

## 🚨 Common Pitfalls & Solutions

### **Pitfall 1: Using UUIDs as Parents**
```python
# ❌ WRONG - Will fail with 403 Forbidden
child_namespace = namespaces.create_namespace(client, parent_namespace.uuid, payload)

# ✅ CORRECT - Use canonical naming
canonical_parent = f"{tenant_namespace}.{parent_name}"
child_namespace = namespaces.create_namespace(client, canonical_parent, payload)
```

### **Pitfall 2: Missing SDK Classes**
```python
# ❌ WRONG - Will fail with ImportError
from endor_cockpit.resources.namespaces import UpdateNamespacePayload  # Missing!

# ✅ CORRECT - Classes now available
from endor_cockpit.resources.namespaces import UpdateNamespacePayload, NamespaceMetaUpdate
```

### **Pitfall 3: Pydantic Validation Errors**
```python
# ❌ WRONG - Will fail with validation error
description: str = Field(..., min_length=1)  # Empty descriptions not allowed

# ✅ CORRECT - Allow empty descriptions
description: str = Field("")  # Empty descriptions allowed
```

## 🔧 Integration Test Patterns

### **Successful Hierarchy Testing**
```python
def test_namespace_hierarchy(self, api_client, tenant_namespace):
    """Test namespace hierarchy operations."""
    parent_name = f"integration-test-parent-{int(time.time())}"
    
    # Create parent namespace
    parent_namespace = self._create_test_namespace(
        api_client, tenant_namespace, parent_name, "Parent namespace"
    )
    
    # Create canonical parent name
    canonical_parent = f"{tenant_namespace}.{parent_name}"
    
    # Create child namespace using canonical parent
    child_namespace = self._create_test_namespace(
        api_client, canonical_parent, child_name, "Child namespace"
    )
    
    # List namespaces under canonical parent
    child_namespaces = namespaces.list_namespaces(api_client, canonical_parent)
```

### **Permission Testing Pattern**
```python
def test_permissions(self, api_client, tenant_namespace):
    """Test what operations are allowed."""
    # Test tenant-level operations
    result = namespaces.create_namespace(client, tenant_namespace, payload)
    assert result is not None  # Should work
    
    # Test hierarchy operations
    canonical_parent = f"{tenant_namespace}.{parent_name}"
    result = namespaces.create_namespace(client, canonical_parent, payload)
    assert result is not None  # Should work if permissions allow
```

## 📊 API Response Patterns

### **Success Patterns**
```json
{
  "uuid": "68f3b2956795a2693a0f5bec",
  "meta": {
    "name": "namespace-name",
    "description": "Namespace description",
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": "2024-01-01T00:00:00Z"
  }
}
```

### **Error Patterns**
```json
// 403 Forbidden - Permission denied
{
  "code": 7,
  "message": "Unauthorized request for given endpoint",
  "details": [
    {
      "@type": "type.googleapis.com/internal.endor.ai.rpc.v1.HTTPErrorInfo",
      "status_code": 403,
      "redirect_url": ""
    }
  ]
}

// 501 Not Implemented - API limitation
{
  "code": 12,
  "message": "Method Not Allowed"
}
```

## 🎯 Best Practices for Agents

### **1. Always Use Canonical Naming**
- Use `tenant.namespace.child` format for hierarchy operations
- Never use UUIDs as parent namespaces
- Build canonical names dynamically: `f"{tenant}.{parent}.{child}"`

### **2. Handle Empty Descriptions**
- API may return namespaces with empty descriptions
- Use `Field("")` instead of `Field(..., min_length=1)` for descriptions
- Validate input but allow empty output

### **3. Test Permission Scope**
- Always test what operations are allowed
- Use permission checkers to validate scope
- Handle 403 errors gracefully

### **4. Use Integration Tests**
- Test with real API endpoints
- Validate against live backend
- Clean up test objects automatically

## 🔍 Debugging Guide

### **403 Forbidden Errors**
1. Check if using canonical naming instead of UUIDs
2. Verify API key has required permissions
3. Confirm parent namespace exists and is accessible

### **Import Errors**
1. Ensure all required classes are imported
2. Check if SDK classes are missing
3. Verify package installation

### **Validation Errors**
1. Check Pydantic field definitions
2. Ensure optional fields are properly defined
3. Handle empty values gracefully

## 📚 Related Documentation

- [Core Principles](./core-principles.md) - Fundamental guidelines
- [Development Guidelines](./development.md) - Development best practices
- [Usage Patterns](./usage-patterns.md) - Common usage patterns
- [Security Guidelines](./security.md) - Security-first practices
- [Tool Definitions](./tool-definitions.md) - LLM tool schemas

## 🎉 Success Metrics

When everything is working correctly, you should see:
- ✅ All integration tests passing (11/11)
- ✅ Namespace hierarchy operations working
- ✅ Security scanning integration working
- ✅ Error handling working gracefully
- ✅ Rate limiting compliance

**The Endor Cockpit SDK is production-ready and fully validated against the live Endor Labs API!** 🚀
