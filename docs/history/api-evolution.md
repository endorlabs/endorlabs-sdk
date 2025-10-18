# API Evolution

> **How the Endor Labs API has changed over time**

## 🎯 **Purpose**

This document tracks the evolution of the Endor Labs API, documenting changes, deprecations, and new features that affect the Endor Cockpit SDK.

## 📅 **Timeline**

### **2025-10-18 - Current State**
- **API Version**: v1.0
- **OpenAPI Spec**: 3.0.0
- **Base URL**: https://api.endorlabs.com
- **Authentication**: API Key + Secret

---

## 🔄 **API Changes**

### **Namespace Operations**

#### **Canonical Naming Requirement**
**Date**: 2025-10-18
**Change**: Namespace operations now require canonical naming for parent relationships
**Impact**: Breaking change for existing integrations

**Before**:
```python
# Could use UUIDs as parent namespaces
child_namespace = namespaces.create_namespace(client, parent_namespace.uuid, payload)
```

**After**:
```python
# Must use canonical naming
canonical_parent = f"{tenant_namespace}.{parent_name}"
child_namespace = namespaces.create_namespace(client, canonical_parent, payload)
```

#### **Parent Namespace Parameter**
**Date**: 2025-10-18
**Change**: All namespace operations now require `parent_namespace` parameter
**Impact**: Breaking change for existing integrations

**Before**:
```python
# Only required UUID parameter
namespace = namespaces.get_namespace(client, namespace_uuid)
```

**After**:
```python
# Requires both parent_namespace and namespace_uuid
namespace = namespaces.get_namespace(client, parent_namespace, namespace_uuid)
```

---

## 🚨 **Breaking Changes**

### **Namespace API Changes**

#### **GET /namespaces/{uuid}**
**Date**: 2025-10-18
**Change**: Added required `parent_namespace` query parameter
**Reason**: Permission validation and access control
**Migration**:
```python
# Before
namespace = namespaces.get_namespace(client, namespace_uuid)

# After
namespace = namespaces.get_namespace(client, parent_namespace, namespace_uuid)
```

#### **POST /namespaces**
**Date**: 2025-10-18
**Change**: `parent_namespace` parameter now requires canonical naming
**Reason**: Hierarchical permission model
**Migration**:
```python
# Before
namespace = namespaces.create_namespace(client, parent_namespace.uuid, payload)

# After
canonical_parent = f"{tenant_namespace}.{parent_name}"
namespace = namespaces.create_namespace(client, canonical_parent, payload)
```

#### **PUT /namespaces/{uuid}**
**Date**: 2025-10-18
**Change**: Added required `parent_namespace` query parameter
**Reason**: Permission validation and access control
**Migration**:
```python
# Before
namespace = namespaces.update_namespace(client, namespace_uuid, payload)

# After
namespace = namespaces.update_namespace(client, parent_namespace, namespace_uuid, payload)
```

#### **DELETE /namespaces/{uuid}**
**Date**: 2025-10-18
**Change**: Added required `parent_namespace` query parameter
**Reason**: Permission validation and access control
**Migration**:
```python
# Before
success = namespaces.delete_namespace(client, namespace_uuid)

# After
success = namespaces.delete_namespace(client, parent_namespace, namespace_uuid)
```

---

## 📊 **Response Format Changes**

### **Namespace List Response**

#### **Added Fields**
**Date**: 2025-10-18
**Change**: Added `created_at` and `updated_at` fields to namespace metadata
**Impact**: Non-breaking addition

**Before**:
```json
{
  "namespaces": [
    {
      "uuid": "68f3b2956795a2693a0f5bec",
      "meta": {
        "name": "namespace-name",
        "description": "Namespace description"
      }
    }
  ]
}
```

**After**:
```json
{
  "namespaces": [
    {
      "uuid": "68f3b2956795a2693a0f5bec",
      "meta": {
        "name": "namespace-name",
        "description": "Namespace description",
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-01T00:00:00Z"
      }
    }
  ]
}
```

#### **Empty Descriptions**
**Date**: 2025-10-18
**Change**: API now returns namespaces with empty descriptions
**Impact**: Breaking change for strict validation

**Before**:
```python
# Required non-empty description
class NamespaceMeta(BaseModel):
    description: str = Field(..., min_length=1)
```

**After**:
```python
# Allow empty descriptions
class NamespaceMeta(BaseModel):
    description: str = Field("")
```

---

## 🔐 **Authentication Changes**

### **API Key Scoping**
**Date**: 2025-10-18
**Change**: API keys are now scoped to tenant namespaces
**Impact**: Cross-tenant access is now forbidden

**Before**:
```python
# Could potentially access cross-tenant resources
namespaces = list_namespaces(client, "other-tenant.namespace")
```

**After**:
```python
# Cross-tenant access returns 403 Forbidden
try:
    namespaces = list_namespaces(client, "other-tenant.namespace")
except HTTPError as e:
    if e.response.status_code == 403:
        print("Cross-tenant access forbidden")
```

### **Permission Model**
**Date**: 2025-10-18
**Change**: Implemented hierarchical permission model
**Impact**: Permissions are now inherited from parent namespaces

**Before**:
```python
# Permissions were flat
permissions = get_permissions(client, namespace_uuid)
```

**After**:
```python
# Permissions are hierarchical
permissions = get_hierarchical_permissions(client, namespace_uuid)
```

---

## 🚀 **New Features**

### **Namespace Updates**
**Date**: 2025-10-18
**Change**: Added PUT endpoint for namespace updates
**Impact**: New functionality

**New Endpoint**:
```python
# PUT /namespaces/{uuid}
def update_namespace(
    client: APIClient, 
    parent_namespace: str, 
    namespace_uuid: str, 
    payload: UpdateNamespacePayload
) -> Optional[Namespace]:
    """Update an existing namespace."""
    # Implementation details
```

### **Enhanced Error Responses**
**Date**: 2025-10-18
**Change**: Improved error response format with detailed error information
**Impact**: Better error handling and debugging

**New Error Format**:
```json
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
```

---

## 🔄 **Deprecations**

### **No Current Deprecations**
As of 2025-10-18, there are no deprecated endpoints or features.

---

## 📚 **Migration Guide**

### **Updating Existing Code**

#### **1. Update Namespace Operations**
```python
# Before
def old_get_namespace(client, namespace_uuid):
    return namespaces.get_namespace(client, namespace_uuid)

# After
def new_get_namespace(client, parent_namespace, namespace_uuid):
    return namespaces.get_namespace(client, parent_namespace, namespace_uuid)
```

#### **2. Update Canonical Naming**
```python
# Before
def old_create_namespace(client, parent_namespace, payload):
    return namespaces.create_namespace(client, parent_namespace.uuid, payload)

# After
def new_create_namespace(client, tenant_namespace, parent_name, payload):
    canonical_parent = f"{tenant_namespace}.{parent_name}"
    return namespaces.create_namespace(client, canonical_parent, payload)
```

#### **3. Update Pydantic Models**
```python
# Before
class OldNamespaceMeta(BaseModel):
    description: str = Field(..., min_length=1)

# After
class NewNamespaceMeta(BaseModel):
    description: str = Field("")
```

---

## 🔍 **Testing Changes**

### **Updated Test Patterns**
```python
# Before
def test_get_namespace(client, namespace_uuid):
    namespace = namespaces.get_namespace(client, namespace_uuid)
    assert namespace is not None

# After
def test_get_namespace(client, parent_namespace, namespace_uuid):
    namespace = namespaces.get_namespace(client, parent_namespace, namespace_uuid)
    assert namespace is not None
```

---

## 📈 **Performance Improvements**

### **Rate Limiting**
**Date**: 2025-10-18
**Change**: Implemented intelligent rate limiting
**Impact**: Better API performance and reliability

### **Connection Pooling**
**Date**: 2025-10-18
**Change**: Added HTTP connection pooling
**Impact**: Reduced connection overhead

---

## 🔮 **Future Roadmap**

### **Planned Changes**
- **GraphQL API**: Additional GraphQL endpoints for complex queries
- **Webhooks**: Real-time event notifications
- **Bulk Operations**: Batch operations for multiple resources
- **Advanced Filtering**: Enhanced filtering and search capabilities

### **Deprecation Timeline**
- **No current deprecations**
- **Future deprecations will be announced 6 months in advance**

---

## 📚 **Related Documentation**

- **[Changelog](./CHANGELOG.md)** - Project changelog
- **[API Specification](../SPECIFICATION.md)** - Current API discrepancies
- **[Developer Guide](../personas/developer/README.md)** - Developer documentation

---

*This document tracks the evolution of the Endor Labs API and provides migration guidance for breaking changes.*
