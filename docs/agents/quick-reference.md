# Endor Cockpit: Agent Quick Reference

## 🚀 Essential Patterns

### **Namespace Hierarchy (CRITICAL)**
```python
# ✅ CORRECT: Use canonical naming
canonical_parent = f"{tenant_namespace}.{parent_name}"
child_result = namespaces.create_namespace(client, canonical_parent, payload)

# ❌ WRONG: Don't use UUIDs as parents
child_result = namespaces.create_namespace(client, parent_namespace.uuid, payload)  # FAILS!
```

### **Required Imports**
```python
from endor_cockpit.api_client import APIClient
from endor_cockpit.resources import namespaces
from endor_cockpit.resources.namespaces import (
    CreateNamespacePayload, 
    NamespaceMetaCreate,
    UpdateNamespacePayload,  # CRITICAL: Was missing!
    NamespaceMetaUpdate      # CRITICAL: Was missing!
)
```

### **Function Signatures**
```python
# CRITICAL: get_namespace requires parent_namespace
namespaces.get_namespace(client, parent_namespace, namespace_uuid)

# CRITICAL: update_namespace requires UpdateNamespacePayload
namespaces.update_namespace(client, parent_namespace, namespace_uuid, UpdateNamespacePayload(...))
```

## 🔧 Common Fixes

### **403 Forbidden Error**
- Check if using canonical naming instead of UUIDs
- Verify API key permissions
- Use `tenant.namespace.child` format

### **ImportError: Missing Classes**
- Ensure `UpdateNamespacePayload` and `NamespaceMetaUpdate` are imported
- Check if SDK classes are missing

### **Pydantic Validation Error**
- Allow empty descriptions: `Field("")` instead of `Field(..., min_length=1)`
- Handle optional fields properly

## 📊 Success Indicators

- ✅ All integration tests passing (11/11)
- ✅ Namespace hierarchy operations working
- ✅ Security scanning integration working
- ✅ Error handling working gracefully

## 🔍 Quick Debug

```python
# Test basic connectivity
client = APIClient()
namespaces_list = namespaces.list_namespaces(client, "endor-solutions-tgowan.cockpit")

# Test hierarchy
canonical_parent = f"endor-solutions-tgowan.cockpit.{parent_name}"
child_result = namespaces.create_namespace(client, canonical_parent, payload)
```

## 📚 Full Documentation

- **[Agent Insights](./insights.md)** - Complete discoveries and patterns
- **[Usage Patterns](./usage-patterns.md)** - Detailed examples
- **[Development Guidelines](./development.md)** - SDK development
