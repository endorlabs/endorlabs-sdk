# Policy Resource Deep-Dive

> **Comprehensive guide to Policy resources in Endor Labs platform**

<!-- RAG METADATA
resource_type: policy
sdk_module: src/endor_cockpit/resources/policy.py
last_reviewed: 2025-10-19
-->

## Architecture

<!-- ~500 tokens | Query: "What is policy architecture?" -->

### Resource Structure

Policies in Endor Labs represent security rules and compliance configurations:

```
Namespace (tenant.namespace)
├── Policy (security-rule-1) - SYSTEM_FINDING
├── Policy (compliance-rule-1) - USER_FINDING
├── Policy (admission-rule-1) - ADMISSION
└── Policy (ml-rule-1) - ML_FINDING
```

### Core Concepts

- **Rule-based**: Policies contain OPA/Rego rules for security enforcement
- **Namespace-scoped**: Policies belong to a specific namespace
- **Type-specific**: Different policy types for different security concerns
- **Template-based**: Policies can be created from templates

### Lifecycle

```
Template → Policy → Rule Evaluation → Finding Generation
```

**Lifecycle States**:
- **Created**: Policy created in namespace
- **Active**: Policy rules are evaluated
- **Triggered**: Policy generates findings or actions
- **Updated**: Policy rules modified
- **Deleted**: Policy removed from namespace

---

## Data Model

<!-- ~800 tokens | Query: "What are policy data structures?" -->

### SDK Implementation

**Location**: `src/endor_cockpit/resources/policy.py:152-200`

```python
# Direct reference - see SDK for full definition
class Policy(BaseModel):
    uuid: str = Field(..., description="Unique identifier for the policy")
    meta: PolicyMeta = Field(..., description="Policy metadata")
    spec: PolicySpec = Field(..., description="Policy specification")
    tenant_meta: TenantMeta = Field(..., description="Tenant metadata")
```

### Core Properties

**PolicyMeta** (`src/endor_cockpit/resources/policy.py:202-250`):
- `name`: Policy name/title
- `description`: Policy description
- `tags`: General resource tags
- `create_time`, `created_by`: Creation metadata
- `update_time`, `updated_by`: Auto-managed timestamps

**PolicySpec** (`src/endor_cockpit/resources/policy.py:252-320`):
- `policy_type`: Policy type (SYSTEM_FINDING, USER_FINDING, ADMISSION, ML_FINDING, NOTIFICATION)
- `rule`: OPA/Rego rule in text format
- `project_selector`: Project selector tags
- `project_exceptions`: Project exception tags
- `resource_kinds`: Resource kinds this policy applies to
- `disable`: Policy disable flag
- `propagate`: Visibility in child namespaces

### Policy Types

**SYSTEM_FINDING**:
- **Purpose**: System-generated security findings
- **Scope**: Automated vulnerability detection
- **Examples**: CVE detection, dependency vulnerabilities

**USER_FINDING**:
- **Purpose**: User-defined security rules
- **Scope**: Custom security policies
- **Examples**: Custom compliance rules, business logic violations

**ADMISSION**:
- **Purpose**: Admission control policies
- **Scope**: Resource admission and validation
- **Examples**: Deployment policies, resource validation

**ML_FINDING**:
- **Purpose**: Machine learning-based findings
- **Scope**: AI-driven security analysis
- **Examples**: Anomaly detection, behavioral analysis

**NOTIFICATION**:
- **Purpose**: Notification and alerting policies
- **Scope**: Event-driven notifications
- **Examples**: Security alerts, compliance notifications

---

## Operations

<!-- ~600 tokens | Query: "How to work with policies?" -->

### CRUD Operations

**Location**: `src/endor_cockpit/resources/policy.py:400-628`

#### List Policies
```python
from endor_cockpit.resources import policy

# List all policies in namespace
policies = policy.list_policies(client, namespace)

# List policies by type
policies = policy.list_policies(client, namespace, policy_type="SYSTEM_FINDING")
```

#### Get Policy
```python
# Get specific policy
policy_obj = policy.get_policy(client, namespace, policy_uuid)
```

#### Create Policy
```python
from endor_cockpit.resources.policy import CreatePolicyPayload, PolicySpec, PolicyType

# Create new policy
payload = CreatePolicyPayload(
    spec=PolicySpec(
        policy_type=PolicyType.USER_FINDING,
        rule="package policy\n\ndefault allow = false\n\nallow {\n    input.resource.kind == \"Repository\"\n}"
    )
)
new_policy = policy.create_policy(client, namespace, payload)
```

#### Update Policy
```python
from endor_cockpit.resources.policy import UpdatePolicyPayload, PolicySpec

# Update policy description
payload = UpdatePolicyPayload(
    meta=PolicyMetaUpdate(description="Updated policy description")
)
updated_policy = policy.update_policy(
    client, namespace, policy_uuid, payload, "meta.description"
)

# Disable policy
payload = UpdatePolicyPayload(
    spec=PolicySpec(disable=True)
)
updated_policy = policy.update_policy(
    client, namespace, policy_uuid, payload, "spec.disable"
)
```

#### Delete Policy
```python
# Delete policy
success = policy.delete_policy(client, namespace, policy_uuid)
```

### Mutable vs Immutable Fields

**MUTABLE FIELDS** (can be updated via PATCH):
- `meta.description`: Policy description
- `meta.tags`: General resource tags
- `spec.rule`: OPA/Rego rule content
- `spec.project_selector`: Project selector tags
- `spec.project_exceptions`: Project exception tags
- `spec.resource_kinds`: Resource kinds
- `spec.disable`: Policy disable flag
- `spec.propagate`: Visibility in child namespaces

**IMMUTABLE FIELDS** (read-only, managed by API):
- `uuid`: Unique identifier (set at creation)
- `meta.name`: Policy name (set at creation)
- `spec.policy_type`: Policy type (set at creation)
- `tenant_meta.namespace`: Namespace assignment

---

## Relationships

<!-- ~400 tokens | Query: "How do policies relate to other resources?" -->

### Namespace Relationship
- **Hierarchical**: Namespace → Policies
- **Scoped**: Policies are isolated by namespace
- **Propagation**: Policies can propagate to child namespaces

### Project Relationship
- **Selector-based**: Policies use project selectors to target specific projects
- **Exception-based**: Policies can exclude specific projects
- **Resource-kind-based**: Policies target specific resource types

### Finding Relationship
- **Generation**: Policies generate findings when triggered
- **Type-specific**: Different policy types generate different finding types
- **Rule-based**: Findings are created based on policy rule evaluation

---

## Common Issues

<!-- ~500 tokens | Query: "What are common policy issues?" -->

### API Endpoint Issues
- **Issue**: Individual policy retrieval fails with 404 errors despite successful listing
- **Cause**: API endpoint inconsistency or policy UUID issues
- **Solution**: Use list_policies() and filter by UUID instead of get_policy()
- **Reference**: `src/endor_cockpit/resources/policy.py:320-336`

### Policy Creation Complexity
- **Issue**: Policy creation requires complex OPA/Rego rules
- **Cause**: API validation requires specific rule formats and UUID returns
- **Solution**: Use existing policies as templates or start with simple rules
- **Reference**: `src/endor_cockpit/resources/policy.py:338-380`

### Schema Drift
- **Issue**: API responses contain unknown fields in meta and spec
- **Solution**: Schema drift detection logs warnings for unknown fields
- **Reference**: `src/endor_cockpit/resources/policy.py:36-50`

### Rule Validation
- **Issue**: OPA/Rego rules must return specific resource UUIDs
- **Cause**: API validation requires rules to return Endor resource UUIDs
- **Solution**: Study existing policy rules for proper format
- **Reference**: Policy creation examples in user documentation

---

## Testing Patterns

<!-- ~300 tokens | Query: "How to test policies?" -->

### Unit Testing
```python
def test_policy_operations():
    # Test policy listing
    policies = policy.list_policies(client, namespace)
    assert len(policies) > 0
    
    # Test policy filtering
    system_policies = policy.list_policies(client, namespace, policy_type="SYSTEM_FINDING")
    assert all(p.spec.policy_type == "SYSTEM_FINDING" for p in system_policies)
```

### Integration Testing
```python
def test_policy_lifecycle():
    # List existing policies
    policies = policy.list_policies(client, namespace)
    assert len(policies) > 0
    
    # Test policy analysis
    test_policy = policies[0]
    assert test_policy.uuid is not None
    assert test_policy.meta.name is not None
    assert test_policy.spec.policy_type is not None
```

---

## Troubleshooting

<!-- ~400 tokens | Query: "How to troubleshoot policy issues?" -->

### Issue: Policy Not Found (404 Errors)

**Date Discovered**: 2025-10-19

**Symptoms**: 
- 404 errors when accessing individual policies
- Same policy UUIDs work in list but fail in individual retrieval
- API endpoint inconsistency

**Root Cause**: 
- API endpoint inconsistency between list and get operations
- Individual policy retrieval endpoints have fundamental issues
- Policy UUIDs valid in list but invalid for individual access

**Solution**: 
```python
# ❌ INCORRECT - Using get_policy() which fails
policy = policy.get_policy(client, namespace, policy_uuid)

# ✅ CORRECT - Use list_policies() and filter by UUID
policies = policy.list_policies(client, namespace)
target_policy = next((p for p in policies if p.uuid == policy_uuid), None)
```

**Prevention**: Use list_policies() for policy access instead of get_policy().

---

### Issue: Policy Update Failures (404 Errors)

**Date Discovered**: 2025-10-19

**Symptoms**: 
- 404 errors when updating policies via PATCH
- Policy update endpoints have fundamental API issues
- Circular dependency in update_policy() function

**Root Cause**: 
- Policy update endpoints have fundamental API issues
- Circular dependency where update_policy() calls get_policy()
- API inconsistency between list and update operations

**Solution**: 
```python
# ❌ INCORRECT - update_policy() calls get_policy() which fails
updated_policy = policy.update_policy(client, namespace, policy_uuid, payload, update_mask)

# ✅ CORRECT - Use list_policies() to get current policy data
policies = policy.list_policies(client, namespace)
current_policy = next((p for p in policies if p.uuid == policy_uuid), None)
# Then proceed with update using current_policy data
```

**Prevention**: Use list_policies() to get current policy data before updates.

---

### Issue: Inherited Policy Immutability

**Date Discovered**: 2025-10-19

**Symptoms**: 
- Cannot update policies that appear in list_policies()
- 404 errors when attempting to update inherited policies
- Policies inherited from parent namespace are immutable

**Root Cause**: 
- Policies inherited from parent namespace are immutable
- Child namespaces cannot modify inherited policies
- Attempting to update inherited policies fails

**Solution**: 
```python
# ❌ INCORRECT - Trying to update inherited policy
inherited_policy = policy.update_policy(client, namespace, inherited_policy_uuid, payload, update_mask)

# ✅ CORRECT - Create new policy in child namespace for testing
new_policy_payload = CreatePolicyPayload(
    meta=PolicyMeta(
        name="Test Policy",
        description="New policy for testing"
    ),
    spec=PolicySpec(
        policy_type=PolicyType.ML_FINDING,
        rule="package testpolicy\n\nconfigure[result] {\n  result = {\n    \"test_method\": {\n      \"disable\": false\n    }\n  }\n}",
        disable=False
    )
)
new_policy = policy.create_policy(client, namespace, new_policy_payload)
```

**Prevention**: Create new policies in child namespace for testing mutability.

---

### Issue: Policy Creation Failures (OPA/Rego Rule Validation)

**Date Discovered**: 2025-10-19

**Symptoms**: 
- Validation errors when creating policies
- "Unable to detect Finding target kind" errors
- Complex OPA/Rego rule requirements

**Root Cause**: 
- OPA/Rego rules must return specific resource UUIDs
- API validation requires rules to return Endor resource UUIDs
- Complex rule format requirements

**Solution**: 
```python
# ❌ INCORRECT - Simple rule that doesn't return UUIDs
rule = "package testpolicy\n\nconfigure[result] {\n  result = true\n}"

# ✅ CORRECT - Rule that returns specific resource UUIDs
rule = """package testpolicy

configure[result] {
  result = {
    "test_method": {
      "disable": false,
      "parameters": {
        "enable_test": {
          "bool_value": true
        }
      }
    }
  }
}"""
```

**Prevention**: Use existing policies as templates, start with simple rules.

---

### Issue: Schema Drift Warnings

**Date Discovered**: 2025-10-19

**Symptoms**: 
- Warnings about unknown fields in API responses
- "Unknown field detected" log messages
- Schema validation warnings

**Root Cause**: 
- API evolution adding new fields
- Model fields not updated to match API
- New policy metadata fields

**Solution**: 
```python
# Schema drift detection automatically logs warnings
# Update models to include new fields or ignore warnings
# Check logs for specific unknown fields: references, parent_kind, parent_uuid, upsert_time, notification
```

**Prevention**: Monitor schema drift warnings and update models when needed.

---

### Issue: Rule Validation Errors

**Date Discovered**: 2025-10-19

**Symptoms**: 
- "Unable to detect Finding target kind" errors
- "Action policies must return the Endor uuid of a Finding" errors
- Policy creation validation failures

**Root Cause**: 
- OPA/Rego rules must return specific resource UUIDs
- API validation requires rules to return Endor resource UUIDs
- Complex rule format requirements

**Solution**: 
```python
# ❌ INCORRECT - Rule that doesn't return proper UUIDs
rule = "package testpolicy\n\nconfigure[result] {\n  result = {\n    \"test\": true\n  }\n}"

# ✅ CORRECT - Rule that returns proper resource UUIDs
rule = """package testpolicy

configure[result] {
  result = {
    "test_method": {
      "disable": false,
      "parameters": {
        "enable_test": {
          "bool_value": true
        }
      }
    }
  }
}"""
```

**Prevention**: Study existing policy rules for proper format and UUID requirements.

---

## Related Resources

- **[Finding Resource](./finding.md)**: Policies generate findings
- **[Project Resource](./project.md)**: Policies target projects
- **[Namespace Resource](./namespaces.md)**: Policy parent namespaces
- **[SDK Reference](../agents/AGENT_GUIDE.md)**: Complete SDK usage guide