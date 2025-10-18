# Usage Patterns for AI Agents

## 1. Common Usage Patterns

### Initialization Pattern
```python
from endor_cockpit.api_client import APIClient
from endor_cockpit.resources import namespaces

# Initialize client (auto-authenticates)
client = APIClient()

# Verify connection
try:
    # Test connection with a simple operation
    tenant_namespace = "your-tenant-namespace"
    namespaces.list_namespaces(client, tenant_namespace)
    print("✅ Connected to Endor Labs API")
except Exception as e:
    print(f"❌ Connection failed: {e}")
```

### Resource Discovery Pattern
```python
# Discover available resources
from endor_cockpit.resources import namespaces, policies, secrets

# List all namespaces to understand the hierarchy
tenant_namespace = "your-tenant-namespace"
all_namespaces = namespaces.list_namespaces(client, tenant_namespace)

for ns in all_namespaces:
    print(f"Namespace: {ns.meta.name} (UUID: {ns.uuid})")
    print(f"  Description: {ns.meta.description}")
    print(f"  Created: {ns.meta.created_at}")
```

### Error Handling Pattern
```python
def safe_operation(operation_func, *args, **kwargs):
    """Safely execute an operation with proper error handling."""
    try:
        result = operation_func(*args, **kwargs)
        if result:
            return result
        else:
            print("⚠️ Operation completed but returned no result")
            return None
    except ValidationError as e:
        print(f"❌ Validation error: {e}")
        return None
    except HTTPError as e:
        print(f"❌ API error: {e}")
        return None
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return None

# Usage
namespace = safe_operation(
    namespaces.create_namespace,
    client,
    tenant_namespace,
    payload
)
```

## 2. Resource Management Patterns

### Namespace Management
```python
def create_agent_namespace(client, parent_namespace, name, description):
    """Create a namespace for agent operations."""
    from endor_cockpit.resources.namespaces import CreateNamespacePayload, NamespaceMeta
    
    payload = CreateNamespacePayload(
        meta=NamespaceMeta(
            name=name,
            description=f"{description} (Created by AI Agent)"
        )
    )
    
    return namespaces.create_namespace(client, parent_namespace, payload)

def list_namespace_hierarchy(client, tenant_namespace):
    """List all namespaces in a hierarchical structure."""
    all_namespaces = namespaces.list_namespaces(client, tenant_namespace)
    
    # Group by parent-child relationships
    hierarchy = {}
    for ns in all_namespaces:
        parent = ns.meta.parent or "root"
        if parent not in hierarchy:
            hierarchy[parent] = []
        hierarchy[parent].append(ns)
    
    return hierarchy
```

### Policy Management
```python
def apply_security_policy(client, namespace_uuid, policy_config):
    """Apply a security policy to a namespace."""
    from endor_cockpit.resources import policies
    
    # Create policy payload
    policy_payload = CreatePolicyPayload(
        meta=PolicyMeta(
            name=policy_config["name"],
            description=policy_config["description"]
        ),
        spec=policy_config["spec"]
    )
    
    return policies.create_policy(client, namespace_uuid, policy_payload)

def scan_namespace_security(client, namespace_uuid):
    """Scan a namespace for security issues."""
    from endor_cockpit.resources import scans
    
    scan_payload = CreateScanPayload(
        target_namespace=namespace_uuid,
        scan_type="security"
    )
    
    return scans.create_scan(client, scan_payload)
```

## 3. Agent-Specific Patterns

### Task-Based Resource Creation
```python
def create_task_resources(client, task_name, task_description, tenant_namespace):
    """Create resources for a specific agent task."""
    
    # Create namespace for the task
    task_namespace = create_agent_namespace(
        client,
        tenant_namespace,
        f"agent-task-{task_name}",
        f"Resources for {task_description}"
    )
    
    if not task_namespace:
        return None
    
    # Create service account for the task
    service_account = create_service_account(
        client,
        task_namespace.uuid,
        f"agent-{task_name}",
        f"Service account for {task_description}"
    )
    
    return {
        "namespace": task_namespace,
        "service_account": service_account
    }
```

### Resource Cleanup Pattern
```python
def cleanup_task_resources(client, task_resources):
    """Clean up resources created for a specific task."""
    cleanup_results = []
    
    # Delete service account
    if task_resources.get("service_account"):
        result = delete_service_account(
            client,
            task_resources["service_account"].uuid
        )
        cleanup_results.append(("service_account", result))
    
    # Delete namespace
    if task_resources.get("namespace"):
        result = namespaces.delete_namespace(
            client,
            task_resources["namespace"].uuid
        )
        cleanup_results.append(("namespace", result))
    
    return cleanup_results
```

## 4. Security Integration Patterns

### Pre-Operation Security Check
```python
def secure_operation_check(client, operation_type, target_resource):
    """Perform security checks before operations."""
    
    # Run security scan
    scan_result = run_security_scan(client, target_resource)
    
    if not scan_result.passed:
        print(f"⚠️ Security scan failed for {target_resource}")
        print(f"   Issues: {scan_result.issues}")
        return False
    
    # Check permissions
    permissions = check_permissions(client, operation_type, target_resource)
    if not permissions.allowed:
        print(f"❌ Insufficient permissions for {operation_type}")
        return False
    
    return True
```

### Security Monitoring Pattern
```python
def monitor_security_events(client, namespace_uuid, duration_minutes=60):
    """Monitor security events for a namespace."""
    from datetime import datetime, timedelta
    
    start_time = datetime.now() - timedelta(minutes=duration_minutes)
    
    # Get security events
    events = get_security_events(client, namespace_uuid, start_time)
    
    # Categorize events
    critical_events = [e for e in events if e.severity == "critical"]
    warning_events = [e for e in events if e.severity == "warning"]
    
    return {
        "total_events": len(events),
        "critical": len(critical_events),
        "warnings": len(warning_events),
        "events": events
    }
```

## 5. Data Processing Patterns

### Batch Operations
```python
def batch_process_resources(client, resources, operation_func, batch_size=10):
    """Process resources in batches to avoid rate limits."""
    results = []
    
    for i in range(0, len(resources), batch_size):
        batch = resources[i:i + batch_size]
        batch_results = []
        
        for resource in batch:
            try:
                result = operation_func(client, resource)
                batch_results.append(result)
            except Exception as e:
                print(f"❌ Failed to process {resource}: {e}")
                batch_results.append(None)
        
        results.extend(batch_results)
        
        # Rate limiting - wait between batches
        if i + batch_size < len(resources):
            time.sleep(1)
    
    return results
```

### Data Validation Pattern
```python
def validate_resource_data(resource_data, schema):
    """Validate resource data against schema."""
    try:
        # Use Pydantic for validation
        validated_data = schema.parse_obj(resource_data)
        return validated_data
    except ValidationError as e:
        print(f"❌ Validation failed: {e}")
        return None
```

## 6. Agent Communication Patterns

### Status Reporting
```python
def report_operation_status(operation_name, status, details=None):
    """Report operation status for agent communication."""
    status_report = {
        "operation": operation_name,
        "status": status,
        "timestamp": datetime.now().isoformat(),
        "details": details or {}
    }
    
    print(f"📊 {operation_name}: {status}")
    if details:
        for key, value in details.items():
            print(f"   {key}: {value}")
    
    return status_report
```

### Error Recovery Pattern
```python
def recover_from_error(client, operation_func, max_retries=3):
    """Attempt to recover from errors with retries."""
    for attempt in range(max_retries):
        try:
            result = operation_func(client)
            return result
        except HTTPError as e:
            if e.response.status_code == 429:  # Rate limited
                wait_time = 2 ** attempt
                print(f"⏳ Rate limited, waiting {wait_time}s...")
                time.sleep(wait_time)
            else:
                print(f"❌ HTTP error: {e}")
                break
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
            break
    
    return None
```

## 7. Integration Patterns

### OpenAPI Discovery
```python
def discover_api_capabilities(client):
    """Discover available API capabilities."""
    spec = client.get_openapi_spec()
    
    # Extract available endpoints
    endpoints = []
    for path, methods in spec.get("paths", {}).items():
        for method, details in methods.items():
            endpoints.append({
                "path": path,
                "method": method.upper(),
                "summary": details.get("summary", ""),
                "description": details.get("description", "")
            })
    
    return endpoints
```

### Resource Relationship Mapping
```python
def map_resource_relationships(client, tenant_namespace):
    """Map relationships between resources."""
    relationships = {}
    
    # Get all namespaces
    namespaces = namespaces.list_namespaces(client, tenant_namespace)
    
    for ns in namespaces:
        # Get policies for this namespace
        policies = policies.list_policies(client, ns.uuid)
        
        # Get secrets for this namespace
        secrets = secrets.list_secrets(client, ns.uuid)
        
        relationships[ns.uuid] = {
            "namespace": ns,
            "policies": policies,
            "secrets": secrets
        }
    
    return relationships
```
