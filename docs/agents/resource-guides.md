# Resource-Specific API Guides

This document provides comprehensive, resource-specific documentation for AI agents working with the Endor Cockpit SDK. Each resource type includes critical insights, common patterns, and platform-specific knowledge discovered through integration testing.

## 📚 **Resource Overview**

### **Available Resources**
- **[Namespaces](#namespaces)** - Hierarchical namespace management
- **[Policies](#policies)** - Security and compliance policies
- **[Secrets](#secrets)** - Secret detection and management
- **[Scans](#scans)** - Security scanning operations
- **[Findings](#findings)** - Security findings and results

---

## 🏗️ **Namespaces**

### **Critical Platform Insights**

#### **Namespace Hierarchy: Canonical Naming Pattern**
**CRITICAL**: Endor Labs uses **canonical hierarchical naming** for namespace relationships, not UUIDs.

```python
# ✅ CORRECT: Use canonical naming for parent-child relationships
canonical_parent = f"{tenant_namespace}.{parent_name}"
# Example: "endor-solutions-tgowan.cockpit.integration-test-parent-{timestamp}"

# Create child namespace
child_result = namespaces.create_namespace(client, canonical_parent, child_payload)

# ❌ INCORRECT: Don't use UUIDs as parents - this will fail with 403 Forbidden
parent_namespace.uuid  # "68f3b2956795a2693a0f5bec" - FAILS!
```

#### **API Permission Model**
**DISCOVERY**: The API key permission model is based on **canonical naming**, not UUIDs.

- **✅ ALLOWED Operations**:
  - Tenant-level operations: Use tenant name (`endor-solutions-tgowan.cockpit`)
  - Hierarchy operations: Use canonical parent names (`tenant.namespace.child`)
  - All CRUD operations: Create, read, update, delete within allowed scope

- **❌ FORBIDDEN Operations**:
  - UUID-based parent relationships: Cannot use UUIDs as parents
  - Cross-tenant operations: Cannot access other tenants
  - Unauthorized resource access: Beyond permission scope

### **Required SDK Classes**

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

### **Function Signatures**

```python
# CRITICAL: get_namespace requires parent_namespace parameter
def get_namespace(client: APIClient, parent_namespace: str, namespace_uuid: str) -> Optional[Namespace]

# CRITICAL: update_namespace requires UpdateNamespacePayload
def update_namespace(client: APIClient, parent_namespace: str, namespace_uuid: str, payload: UpdateNamespacePayload) -> Optional[Namespace]
```

### **Common Patterns**

#### **Creating Namespaces**
```python
from endor_cockpit.resources import namespaces
from endor_cockpit.resources.namespaces import CreateNamespacePayload, NamespaceMetaCreate

def create_agent_namespace(client, parent_namespace, name, description):
    """Create a namespace for agent operations."""
    payload = CreateNamespacePayload(
        meta=NamespaceMetaCreate(
            name=name,
            description=f"{description} (Created by AI Agent)"
        )
    )
    
    return namespaces.create_namespace(client, parent_namespace, payload)

# Usage
tenant_namespace = "your-tenant-namespace"
new_namespace = create_agent_namespace(
    client,
    tenant_namespace,
    "agent-task-namespace",
    "Resources for agent task"
)
```

#### **Hierarchical Namespace Management**
```python
def create_child_namespace(client, parent_canonical_name, child_name, description):
    """Create a child namespace using canonical naming."""
    payload = CreateNamespacePayload(
        meta=NamespaceMetaCreate(
            name=child_name,
            description=description
        )
    )
    
    # Use canonical parent name, not UUID
    return namespaces.create_namespace(client, parent_canonical_name, payload)

# Usage
parent_canonical = f"{tenant_namespace}.parent-namespace"
child_namespace = create_child_namespace(
    client,
    parent_canonical,
    "child-namespace",
    "Child namespace description"
)
```

#### **Listing and Discovering Namespaces**
```python
def discover_namespace_hierarchy(client, tenant_namespace):
    """Discover the complete namespace hierarchy."""
    all_namespaces = namespaces.list_namespaces(client, tenant_namespace)
    
    hierarchy = {}
    for ns in all_namespaces:
        print(f"Namespace: {ns.meta.name}")
        print(f"  UUID: {ns.uuid}")
        print(f"  Description: {ns.meta.description}")
        print(f"  Created: {ns.meta.created_at}")
        print(f"  Parent: {ns.meta.parent or 'root'}")
        print()
    
    return all_namespaces
```

### **Error Handling**

```python
def safe_namespace_operation(operation_func, *args, **kwargs):
    """Safely execute namespace operations with proper error handling."""
    try:
        result = operation_func(*args, **kwargs)
        if result:
            print(f"✅ Namespace operation successful")
            return result
        else:
            print("⚠️ Operation completed but returned no result")
            return None
    except ValidationError as e:
        print(f"❌ Validation error: {e}")
        return None
    except HTTPError as e:
        if e.response.status_code == 403:
            print(f"❌ Permission denied: {e}")
            print("💡 Check if you're using canonical naming instead of UUIDs")
        elif e.response.status_code == 404:
            print(f"❌ Resource not found: {e}")
        else:
            print(f"❌ API error: {e}")
        return None
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return None
```

---

## 🔒 **Policies**

### **Critical Platform Insights**

#### **Policy Creation Limitations**
**DISCOVERY**: Direct API policy creation is currently limited. The following endpoints return errors:
- `v1/policy-validator`: 404 Not Found
- `v1/namespaces/{namespace}/policies`: 400 Bad Request (incorrect payload format)
- `v1/policies`: 404 Not Found

#### **Policy Types**
- **Admission Policies**: Control resource creation and modification
- **Exception Policies**: Dismiss findings as false positives
- **System Policies**: Built-in platform policies
- **User Policies**: Custom user-defined policies

### **Common Patterns**

#### **Policy Discovery**
```python
def discover_available_policies(client, namespace):
    """Discover available policies in a namespace."""
    try:
        # List existing policies
        policies = client.get(f"v1/namespaces/{namespace}/policies")
        return policies.json()
    except Exception as e:
        print(f"❌ Failed to discover policies: {e}")
        return None
```

#### **Exception Policy Configuration**
```python
def create_exception_policy_config(secret_pattern, file_patterns, justification):
    """Create configuration for secret exception policy."""
    return {
        "name": f"secret-exception-{secret_pattern}",
        "description": f"Exception policy for secrets matching pattern {secret_pattern}",
        "type": "exception",
        "scope": {
            "secret_patterns": [secret_pattern],
            "file_patterns": file_patterns,
            "secret_types": ["generic_api_key"]
        },
        "action": "dismiss",
        "category": "NOTIFICATION_DISMISS_CATEGORY_FALSE_POSITIVE",
        "reason": "Known test secret pattern for verification",
        "justification": justification,
        "tags": ["test", "false-positive", "secret-detection"],
        "enabled": True,
        "priority": "high"
    }

# Usage
policy_config = create_exception_policy_config(
    "sk-1234567890abcdef",
    ["**/test*.py", "**/tests/**/*.py"],
    "Known test secret pattern used for verification purposes"
)
```

#### **Manual Policy Creation**
```python
def prepare_policy_for_ui_creation(policy_config):
    """Prepare policy configuration for manual UI creation."""
    print("Policy Configuration for Manual Creation:")
    print("=" * 50)
    print(f"Name: {policy_config['name']}")
    print(f"Description: {policy_config['description']}")
    print(f"Type: {policy_config['type']}")
    print(f"Scope: {policy_config['scope']}")
    print(f"Action: {policy_config['action']}")
    print(f"Justification: {policy_config['justification']}")
    print()
    print("Steps for Manual Creation:")
    print("1. Navigate to Endor Labs UI")
    print("2. Go to Policies section")
    print("3. Create new Exception Policy")
    print("4. Use the configuration above")
    
    return policy_config
```

---

## 🔐 **Secrets**

### **Critical Platform Insights**

#### **Secret Detection Patterns**
- **Test Secret Patterns**: Use specific patterns for test secrets
- **False Positive Handling**: Use `endorctl:allow` comments for immediate dismissal
- **Pattern Matching**: Supports regex patterns for secret detection

#### **Secret Categories**
- **FINDING_CATEGORY_SECRETS**: Detected secrets
- **FINDING_TAGS_VALID_SECRET**: Verified active secrets
- **FINDING_TAGS_INVALID_SECRET**: Verified inactive secrets
- **FINDING_TAGS_TEST**: Test-related secrets

### **Common Patterns**

#### **Secret Detection and Management**
```python
def scan_for_secrets(client, namespace_uuid, file_patterns=None):
    """Scan a namespace for secrets."""
    scan_config = {
        "target_namespace": namespace_uuid,
        "scan_type": "secrets",
        "file_patterns": file_patterns or ["**/*.py", "**/*.js", "**/*.ts"]
    }
    
    try:
        result = client.post(f"v1/namespaces/{namespace_uuid}/scans", json=scan_config)
        return result.json()
    except Exception as e:
        print(f"❌ Secret scan failed: {e}")
        return None
```

#### **False Positive Handling**
```python
def add_false_positive_comment(file_path, line_number, secret_pattern, justification):
    """Add endorctl:allow comment to dismiss false positive."""
    comment = f"  # endorctl:allow - {justification}"
    
    print(f"Add this comment to {file_path} at line {line_number}:")
    print(f"  {secret_pattern} {comment}")
    print()
    print("This will automatically dismiss the secret as a false positive.")
    
    return comment

# Usage
add_false_positive_comment(
    "tests/test_integration.py",
    363,
    "sk-1234567890abcdef",
    "Known test secret for verification"
)
```

#### **Secret Pattern Management**
```python
def create_secret_exception_patterns():
    """Create common secret exception patterns."""
    patterns = {
        "test_api_keys": {
            "pattern": "sk-1234567890abcdef",
            "description": "Test API key pattern",
            "file_scope": ["**/test*.py", "**/tests/**/*.py"],
            "justification": "Known test secret for verification"
        },
        "test_tokens": {
            "pattern": "test-token-[a-zA-Z0-9]{32}",
            "description": "Test token pattern",
            "file_scope": ["**/test*.py", "**/tests/**/*.py"],
            "justification": "Test tokens for integration testing"
        }
    }
    
    return patterns
```

---

## 🔍 **Scans**

### **Critical Platform Insights**

#### **Scan Types**
- **Security Scans**: SAST, dependency, and vulnerability scanning
- **Secret Scans**: Secret detection and validation
- **Compliance Scans**: Policy compliance checking
- **Container Scans**: Container image security scanning

#### **Scan Results**
- **Findings**: Security issues discovered
- **Metrics**: Scan performance and coverage
- **Reports**: Detailed scan reports

### **Common Patterns**

#### **Initiating Scans**
```python
def initiate_security_scan(client, namespace_uuid, scan_type="comprehensive"):
    """Initiate a security scan for a namespace."""
    scan_config = {
        "target_namespace": namespace_uuid,
        "scan_type": scan_type,
        "options": {
            "include_dependencies": True,
            "include_secrets": True,
            "include_sast": True
        }
    }
    
    try:
        result = client.post(f"v1/namespaces/{namespace_uuid}/scans", json=scan_config)
        scan_id = result.json().get("scan_id")
        print(f"✅ Scan initiated: {scan_id}")
        return scan_id
    except Exception as e:
        print(f"❌ Scan initiation failed: {e}")
        return None
```

#### **Monitoring Scan Progress**
```python
def monitor_scan_progress(client, scan_id, timeout_minutes=30):
    """Monitor scan progress until completion."""
    import time
    from datetime import datetime, timedelta
    
    start_time = datetime.now()
    timeout = timedelta(minutes=timeout_minutes)
    
    while datetime.now() - start_time < timeout:
        try:
            status = client.get(f"v1/scans/{scan_id}/status")
            scan_status = status.json()
            
            print(f"📊 Scan Status: {scan_status.get('status', 'unknown')}")
            
            if scan_status.get('status') == 'completed':
                print("✅ Scan completed successfully")
                return scan_status
            elif scan_status.get('status') == 'failed':
                print("❌ Scan failed")
                return scan_status
            
            time.sleep(10)  # Check every 10 seconds
            
        except Exception as e:
            print(f"❌ Error checking scan status: {e}")
            break
    
    print("⏰ Scan monitoring timed out")
    return None
```

---

## 📊 **Findings**

### **Critical Platform Insights**

#### **Finding Categories**
- **FINDING_CATEGORY_SECRETS**: Secret-related findings
- **FINDING_CATEGORY_VULNERABILITY**: Vulnerability findings
- **FINDING_CATEGORY_SAST**: Static analysis findings
- **FINDING_CATEGORY_CONTAINER**: Container-related findings

#### **Finding Severity Levels**
- **FINDING_LEVEL_CRITICAL**: Critical security issues
- **FINDING_LEVEL_HIGH**: High severity issues
- **FINDING_LEVEL_MEDIUM**: Medium severity issues
- **FINDING_LEVEL_LOW**: Low severity issues

### **Common Patterns**

#### **Finding Management**
```python
def get_namespace_findings(client, namespace_uuid, severity_filter=None):
    """Get findings for a namespace."""
    try:
        findings = client.get(f"v1/namespaces/{namespace_uuid}/findings")
        all_findings = findings.json()
        
        if severity_filter:
            filtered_findings = [
                f for f in all_findings 
                if f.get('severity') == severity_filter
            ]
            return filtered_findings
        
        return all_findings
    except Exception as e:
        print(f"❌ Failed to get findings: {e}")
        return None
```

#### **Finding Analysis**
```python
def analyze_findings(findings):
    """Analyze findings and provide summary."""
    if not findings:
        return {"total": 0, "by_severity": {}, "by_category": {}}
    
    analysis = {
        "total": len(findings),
        "by_severity": {},
        "by_category": {},
        "critical_issues": []
    }
    
    for finding in findings:
        severity = finding.get('severity', 'unknown')
        category = finding.get('category', 'unknown')
        
        # Count by severity
        analysis["by_severity"][severity] = analysis["by_severity"].get(severity, 0) + 1
        
        # Count by category
        analysis["by_category"][category] = analysis["by_category"].get(category, 0) + 1
        
        # Track critical issues
        if severity == "FINDING_LEVEL_CRITICAL":
            analysis["critical_issues"].append(finding)
    
    return analysis
```

---

## 🔧 **Integration Patterns**

### **Resource Relationship Mapping**
```python
def map_resource_relationships(client, tenant_namespace):
    """Map relationships between all resources in a namespace."""
    relationships = {}
    
    # Get all namespaces
    namespaces_list = namespaces.list_namespaces(client, tenant_namespace)
    
    for ns in namespaces_list:
        # Get policies for this namespace
        try:
            policies = client.get(f"v1/namespaces/{ns.uuid}/policies")
            policies_data = policies.json()
        except:
            policies_data = []
        
        # Get findings for this namespace
        try:
            findings = client.get(f"v1/namespaces/{ns.uuid}/findings")
            findings_data = findings.json()
        except:
            findings_data = []
        
        relationships[ns.uuid] = {
            "namespace": ns,
            "policies": policies_data,
            "findings": findings_data
        }
    
    return relationships
```

### **Comprehensive Resource Audit**
```python
def audit_namespace_resources(client, namespace_uuid):
    """Perform comprehensive audit of namespace resources."""
    audit_report = {
        "namespace": namespace_uuid,
        "timestamp": datetime.now().isoformat(),
        "resources": {},
        "security_status": {},
        "recommendations": []
    }
    
    # Audit policies
    try:
        policies = client.get(f"v1/namespaces/{namespace_uuid}/policies")
        audit_report["resources"]["policies"] = len(policies.json())
    except:
        audit_report["resources"]["policies"] = 0
    
    # Audit findings
    try:
        findings = client.get(f"v1/namespaces/{namespace_uuid}/findings")
        findings_data = findings.json()
        audit_report["resources"]["findings"] = len(findings_data)
        
        # Analyze security status
        critical_findings = [f for f in findings_data if f.get('severity') == 'FINDING_LEVEL_CRITICAL']
        audit_report["security_status"]["critical_findings"] = len(critical_findings)
        
        if critical_findings:
            audit_report["recommendations"].append("Address critical security findings immediately")
        
    except:
        audit_report["resources"]["findings"] = 0
    
    return audit_report
```

---

## 📚 **Quick Reference**

### **Critical Patterns Summary**
1. **Use canonical naming** for namespace hierarchy (not UUIDs)
2. **Handle empty descriptions** in Pydantic models
3. **Use `endorctl:allow` comments** for immediate false positive dismissal
4. **Check API permissions** before operations
5. **Implement proper error handling** for all operations

### **Common Error Codes**
- **403 Forbidden**: Permission denied (check canonical naming)
- **404 Not Found**: Resource not found
- **400 Bad Request**: Invalid payload format
- **429 Too Many Requests**: Rate limited

### **Best Practices**
1. **Always use canonical naming** for parent-child relationships
2. **Implement comprehensive error handling**
3. **Use batch operations** for multiple resources
4. **Monitor scan progress** for long-running operations
5. **Document policy configurations** for manual creation

---

This resource guide consolidates all critical insights discovered through integration testing and provides comprehensive patterns for working with each resource type in the Endor Cockpit SDK.
