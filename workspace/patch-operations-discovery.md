# PATCH Operations Discovery: Update Mask Implementation

> **Critical Discovery: The `update_mask` field enables efficient partial updates for PATCH operations**

## 🎯 **Key Discovery**

The OpenAPI specification includes a `v1UpdateRequest` object with an `update_mask` field that allows specifying which fields to update, enabling efficient partial updates without requiring full object structure.

## ✅ **Update Mask Implementation Success**

### **API Endpoint Structure**
```json
{
  "request": {
    "update_mask": "meta.tags",
    "force": false
  },
  "object": {
    "uuid": "<resource-uuid>",
    "tenant_meta": {"namespace": "<namespace>"},
    "meta": {
      "name": "<existing-name>",
      "description": "<existing-description>",
      "tags": ["new-tag"]
    }
  }
}
```

### **Update Mask Format**
- **Single Field**: `"meta.tags"` - Update only meta.tags
- **Multiple Fields**: `"meta.tags,meta.description"` - Update both fields
- **Nested Fields**: `"spec.finding_tags"` - Update spec.finding_tags
- **All Meta Fields**: `"meta"` - Update all meta fields
- **All Fields**: `"*"` - Update all fields (default)

### **Successful Test Results**
```
✅ Project PATCH with update_mask: SUCCESS
✅ Finding PATCH with update_mask: SUCCESS  
✅ Multiple fields mask: SUCCESS
✅ Spec fields mask: SUCCESS
```

## 🔧 **Implementation Details**

### **1. Project Tag Management**
```python
# Add project tag
request_data = {
    "request": {"update_mask": "meta.tags"},
    "object": {
        "uuid": project_uuid,
        "tenant_meta": {"namespace": namespace},
        "meta": {
            "name": existing_name,
            "description": existing_description,
            "tags": new_tags
        }
    }
}
```

### **2. Finding Tag Management**
```python
# Add finding meta tag
request_data = {
    "request": {"update_mask": "meta.tags"},
    "object": {
        "uuid": finding_uuid,
        "tenant_meta": {"namespace": namespace},
        "meta": {
            "name": existing_name,
            "description": existing_description,
            "tags": new_tags
        }
    }
}

# Add finding spec tag
request_data = {
    "request": {"update_mask": "spec.finding_tags"},
    "object": {
        "uuid": finding_uuid,
        "tenant_meta": {"namespace": namespace},
        "spec": {
            "project_uuid": existing_project_uuid,
            "level": existing_level,
            "finding_tags": new_tags
        }
    }
}
```

## ⚠️ **Critical Limitation Discovered**

### **Tag Persistence Issue**
- **API Response**: ✅ Returns updated tags correctly
- **Persistence**: ❌ Tags not persisted to database
- **Verification**: ❌ Tags not found when retrieving resource again

### **Test Results**
```
Request: {"request": {"update_mask": "meta.tags"}, "object": {...}}
Response: 200 OK
Updated tags: ['test-tag-direct']  # ✅ API returns correct tags
Verification: []  # ❌ Tags not persisted
```

## 🔍 **Root Cause Analysis**

### **Possible Causes**
1. **Database Persistence**: Tags may not be saved to the database
2. **Field Mapping**: The `meta.tags` field may not be properly mapped
3. **API Limitation**: The API may not support tag updates for certain resource types
4. **Permission Issue**: Insufficient permissions to modify tags
5. **Schema Validation**: Tags field may have validation constraints

### **Evidence**
- API accepts the request and returns 200 OK
- Response includes the updated tags
- Subsequent GET requests show empty tags
- No error messages or validation failures

## 💡 **Recommendations**

### **1. Immediate Actions**
- **Investigate API Documentation**: Check if tags are supported for updates
- **Test with Different Fields**: Try updating other fields to verify update_mask works
- **Check Permissions**: Verify if tag updates require special permissions
- **Contact API Support**: Inquire about tag update limitations

### **2. Alternative Approaches**
- **Full Object Updates**: Use complete object structure for tag updates
- **Different Endpoints**: Check if there are dedicated tag management endpoints
- **Bulk Operations**: Use bulk update operations for tag management

### **3. Implementation Strategy**
```python
# Current approach (not persisting)
def add_project_tag(client, namespace, project_uuid, tag):
    # Use update_mask - API accepts but doesn't persist
    pass

# Alternative approach (full object)
def add_project_tag_full(client, namespace, project_uuid, tag):
    # Get full project, modify tags, send complete object
    project = get_project(client, namespace, project_uuid)
    # ... modify project object
    # ... send complete object without update_mask
    pass
```

## 📊 **Technical Summary**

### **What Works**
- ✅ **Update Mask Format**: Correctly specified field paths
- ✅ **API Endpoints**: Correct endpoint usage
- ✅ **Request Structure**: Proper request body format
- ✅ **API Response**: Server accepts and processes requests

### **What Doesn't Work**
- ❌ **Tag Persistence**: Tags not saved to database
- ❌ **Verification**: Tags not retrievable after update
- ❌ **Production Use**: Cannot rely on tag updates

### **Next Steps**
1. **Investigate API Limitations**: Check if tags are updatable
2. **Test Other Fields**: Verify update_mask works with other fields
3. **Implement Fallback**: Use full object updates if needed
4. **Document Limitations**: Clearly document tag update constraints

## 🎯 **Conclusion**

**Update Mask Discovery**: ✅ **SUCCESSFUL** - The `update_mask` field enables efficient partial updates

**Tag Management**: ⚠️ **LIMITED** - API accepts tag updates but doesn't persist them

**Recommendation**: Investigate API limitations and implement alternative approaches for tag management that ensure persistence.

**Status**: 🔍 **INVESTIGATION NEEDED** - Update mask works but tag persistence requires further investigation.
