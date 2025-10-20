# _RESOURCE_TEMPLATE.md

> **Template for Endor Labs resource documentation**

This template provides the standard structure for documenting Endor Labs platform resources. Use this as a guide when creating or updating resource documentation.

## Template Philosophy

- **Direct SDK References**: Point to actual SDK classes and functions, not auto-generated docs
- **Real Examples**: Use working code examples that reference actual SDK implementations
- **Status Markers**: Only use ✅ IMPLEMENTED (no conceptual/planned markers for this SDK)
- **RAG-Optimized**: Structure content for semantic chunking and vector database retrieval

---

## Template Structure

```markdown
# [Resource] Resource Deep-Dive

> **Comprehensive guide to [Resource] resources in Endor Labs platform**

<!-- RAG METADATA
resource_type: [resource]
sdk_module: src/endor_cockpit/resources/[resource].py
last_reviewed: YYYY-MM-DD
-->

## Architecture

<!-- ~500 tokens | Query: "What is [resource] architecture?" -->

### Resource Structure
[Visual representation of resource hierarchy and relationships]

### Core Concepts
- Key concept 1
- Key concept 2
- Key concept 3

### Lifecycle
[Resource lifecycle states and transitions]

---

## Data Model

<!-- ~700 tokens | Query: "What fields does [resource] have?" -->

### SDK Implementation

**Location**: `src/endor_cockpit/resources/[resource].py:[line-range]`

```python
# Direct reference - see SDK for full definition
class [Resource](BaseModel):
    # Reference actual fields from SDK
```

**To explore fields**:
- View `[Resource]Meta` in SDK (lines X-Y)
- View `[Resource]Spec` in SDK (lines A-B)
- View `[Resource]Status` in SDK (lines C-D)

### Core Properties

**[Resource]Meta** (`src/endor_cockpit/resources/[resource].py:line-range`):
- `name`: [Resource] name/title
- `description`: [Resource] description
- `tags`: General resource tags
- `create_time`, `created_by`: Creation metadata
- `update_time`, `updated_by`: Auto-managed timestamps

**[Resource]Spec** (`src/endor_cockpit/resources/[resource].py:line-range`):
- `field_name`: [Description of field]
- `field_name`: [Description of field]
- `field_name`: [Description of field]

**[Resource]Context** (`src/endor_cockpit/resources/[resource].py:line-range`):
- `field_name`: [Description of field]
- `field_name`: [Description of field]

### [Resource] Types

**[Type 1]**:
- **Purpose**: [Purpose description]
- **Scope**: [Scope description]
- **Examples**: [Example use cases]

**[Type 2]**:
- **Purpose**: [Purpose description]
- **Scope**: [Scope description]
- **Examples**: [Example use cases]

**[Type 3]**:
- **Purpose**: [Purpose description]
- **Scope**: [Scope description]
- **Examples**: [Example use cases]

### Mutable Fields

**Via PATCH operations**:
- `field_name`: type - [description]
- `field_name`: type - [description]

### Immutable Fields

**Read-only, API-managed**:
- `field_name`: Unique identifier
- `field_name`: [description]
- `field_name`: [description]

### Field Validation

**Validators** (see `[Resource]Update:line-range`):
- `field_name`: [validation rules]
- `field_name`: [validation rules]

---

## Operations

<!-- ~800 tokens | Query: "How do I [operation] [resource]?" -->

### CRUD Operations

**Location**: `src/endor_cockpit/resources/[resource].py:line-range`

#### List [Resources]
```python
from endor_cockpit.resources import [resource]

# List all [resources] in namespace
[resources] = [resource].list_[resources](client, namespace)

# List [resources] for specific [filter]
[resources] = [resource].list_[resources](client, namespace, filter_param="value")
```

#### Get [Resource]
```python
# Get specific [resource]
[resource]_obj = [resource].get_[resource](client, namespace, [resource]_uuid)
```

#### Create [Resource]
```python
from endor_cockpit.resources.[resource] import Create[Resource]Payload, [Resource]Spec

# Create new [resource]
payload = Create[Resource]Payload(
    spec=[Resource]Spec(
        field="value",
        another_field="another_value"
    )
)
new_[resource] = [resource].create_[resource](client, namespace, payload)
```

#### Update [Resource]
```python
from endor_cockpit.resources.[resource] import Update[Resource]Payload, [Resource]Spec

# Update [resource] fields
payload = Update[Resource]Payload(
    spec=[Resource]Spec(field="new_value")
)
updated_[resource] = [resource].update_[resource](
    client, namespace, [resource]_uuid, payload, "spec.field"
)
```

#### Delete [Resource]
```python
# Delete [resource]
success = [resource].delete_[resource](client, namespace, [resource]_uuid)
```

### Mutable vs Immutable Fields

**MUTABLE FIELDS** (can be updated via PATCH):
- `field_name`: [Description]
- `field_name`: [Description]
- `field_name`: [Description]

**IMMUTABLE FIELDS** (read-only, managed by API):
- `uuid`: Unique identifier (set at creation)
- `field_name`: [Description]
- `field_name`: [Description]


---

## Relationships

<!-- ~500 tokens | Query: "How does [resource] relate to X?" -->

### [Resource]-[RelatedResource]

[Description of relationship]

### [Resource]-[AnotherResource]

[Description of relationship]

### [Resource]-[ThirdResource]

[Description of relationship]

---

## Common Issues

<!-- ~600 tokens | Query: "What are common [resource] issues?" -->

### Issue: [Common Issue Name]

**Cause**: [Root cause]  
**Solution**: [Solution steps]

```python
# ❌ WRONG
[Actual wrong pattern]

# ✅ CORRECT
[Actual correct pattern]
```

### Issue: [Another Common Issue]

**Cause**: [Root cause]  
**Solution**: [Solution steps]

```python
# ❌ WRONG
[Actual wrong pattern]

# ✅ CORRECT
[Actual correct pattern]
```

---

## Testing Patterns

<!-- ~400 tokens -->

### CRUD Testing

**Test File**: `tests/test_[resource].py`

```python
# Reference actual test patterns from test_[resource].py
# See lines X-Y for list/get testing
# See lines A-B for create/update testing
# See lines C-D for tag management testing
```

### Integration Testing

**Test File**: `tests/test_[resource].py`

```python
# Reference integration test patterns
# See lines X-Y for relationship testing
# See lines A-B for error handling testing
```

---

## Troubleshooting

<!-- ~400 tokens | Query: "How to troubleshoot [resource] issues?" -->

### Issue: [Resource] Not Found (404 Errors)

**Date Discovered**: YYYY-MM-DD

**Symptoms**: 
- 404 errors when accessing [resources]
- [Resource] UUID incorrect or [resource] deleted
- Cross-namespace [resource] access fails

**Root Cause**: 
- [Resource] UUID incorrect or [resource] deleted
- Attempting cross-namespace operations
- [Resource] moved to different namespace

**Solution**: 
```python
# ❌ INCORRECT - Wrong UUID or namespace
[resource] = [resources].get_[resource](client, "wrong-namespace", [resource]_uuid)

# ✅ CORRECT - Verify UUID and namespace
[resource] = [resources].get_[resource](client, "correct-namespace", [resource]_uuid)
```

**Prevention**: Always verify [resource] UUID and namespace before operations.

---

### Issue: Update Failures (Validation Errors)

**Date Discovered**: YYYY-MM-DD

**Symptoms**: 
- Validation errors when updating [resources]
- "Missing required fields" errors
- PATCH requests fail with 400 Bad Request

**Root Cause**: 
- Missing required fields in `Update[Resource]Payload`
- Incomplete payload structure
- Missing required fields

**Solution**: 
```python
# ❌ INCORRECT - Missing required fields
payload = Update[Resource]Payload(
    spec=[Resource]Spec(field="value")
)

# ✅ CORRECT - Include complete payload structure
payload = Update[Resource]Payload(
    meta=[Resource]Meta(
        name=current_[resource].meta.name,
        description=current_[resource].meta.description
    ),
    spec=[Resource]Spec(field="value")
)
```

**Prevention**: Always include complete payload structure with current [resource] data.

---

### Issue: Field Mutability Violations

**Date Discovered**: YYYY-MM-DD

**Symptoms**: 
- Attempts to update immutable fields fail
- "Field is read-only" errors
- Update operations rejected

**Root Cause**: 
- Trying to update fields marked as immutable
- Attempting to change system-managed fields
- Violating field mutability rules

**Solution**: 
```python
# ❌ INCORRECT - Trying to update immutable fields
payload = Update[Resource]Payload(
    spec=[Resource]Spec(
        immutable_field="new-value"  # IMMUTABLE
    )
)

# ✅ CORRECT - Only update mutable fields
payload = Update[Resource]Payload(
    spec=[Resource]Spec(
        mutable_field="new-value"    # MUTABLE
    )
)
```

**Prevention**: Only update mutable fields: [list mutable fields].

---

## Related Resources

- [[RelatedResource]](./[related-resource].md) - [Description of relationship]
- [[AnotherResource]](./[another-resource].md) - [Description of relationship]
- [[ThirdResource]](./[third-resource].md) - [Description of relationship]

---

<!-- VALIDATION METADATA
last_reviewed: YYYY-MM-DD
reviewed_by: human
validation_status: needs_review
known_issues: []
-->

*Documentation references SDK implementation. See `src/endor_cockpit/resources/[resources].py` for complete details.*
```

---

## Usage Instructions

1. **Copy this template** to create new resource documentation
2. **Replace placeholders** with actual resource information:
   - `[Resource]` → Actual resource name (e.g., `Project`)
   - `[resource]` → Lowercase resource name (e.g., `project`)
   - `[line]` → Actual line numbers from SDK
   - `[line-range]` → Actual line ranges from SDK
3. **Fill in content** based on actual SDK implementation
4. **Validate references** to ensure all function/class references exist in SDK
5. **Test RAG queries** to ensure content is discoverable

## Validation Checklist

- [ ] All function references point to actual SDK functions
- [ ] All class references point to actual SDK classes
- [ ] All line numbers are accurate
- [ ] No "# Implementation details" placeholders remain
- [ ] All examples use actual SDK imports
- [ ] Status markers are correct (only ✅ IMPLEMENTED)
- [ ] RAG metadata is complete and accurate
- [ ] Related resources links are valid
- [ ] Common issues are based on real problems
- [ ] Testing patterns reference actual test files

---

*This template ensures consistent, accurate, and RAG-optimized documentation for all Endor Labs resources.*


