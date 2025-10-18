# Security Guidelines for AI Agents

## 1. Security-First Development

### Pre-Development Security Checks
Before making any changes to the codebase:

1. **Run Security Scan**: Always run `endorctl scan` before development
2. **Review Dependencies**: Check for vulnerable dependencies
3. **Validate Inputs**: Ensure all inputs are properly validated
4. **Check Permissions**: Verify required permissions are available

### Security Scanning Requirements
```bash
# Required before any code changes
endorctl scan

# For dependency changes
endorctl scan --dependencies

# For first-party code changes
endorctl scan --sast
```

## 2. Data Protection

### No PII Handling
This project is classified as **public** with **no PII handling**:
- ✅ **Allowed**: Public data, configuration data, API responses
- ❌ **Prohibited**: Personal information, sensitive data, credentials

### Secure Logging
```python
# ✅ Good: Filtered logging
logger.info(f"Processing namespace {namespace_id}")
logger.error(f"Operation failed for resource {resource_type}")

# ❌ Bad: Potential data leakage
logger.info(f"Processing user data: {user_data}")
logger.error(f"Failed with credentials: {credentials}")
```

### Environment Variables
```python
# ✅ Good: Use environment variables
api_key = os.getenv("ENDOR_API_CREDENTIALS_KEY")
api_secret = os.getenv("ENDOR_API_CREDENTIALS_SECRET")

# ❌ Bad: Hardcoded secrets
api_key = "hardcoded-secret-key"
```

## 3. Authentication & Authorization

### Service Account Management
```python
def create_secure_service_account(client, namespace_uuid, task_name, duration_hours):
    """Create a service account with minimal required permissions."""
    
    # Calculate expiration time
    expiration = datetime.now() + timedelta(hours=duration_hours)
    
    # Create service account with minimal permissions
    service_account = create_service_account(
        client=client,
        namespace_uuid=namespace_uuid,
        name=f"agent-{task_name}-{expiration.strftime('%Y%m%d')}",
        description=f"Service account for {task_name} (expires {expiration.isoformat()})",
        permissions=get_minimal_permissions(task_name),
        expiration=expiration
    )
    
    return service_account
```

### Permission Scoping
```python
def get_minimal_permissions(task_type):
    """Get minimal permissions required for specific task types."""
    permission_map = {
        "namespace_read": ["namespaces:read"],
        "namespace_write": ["namespaces:read", "namespaces:write"],
        "policy_management": ["namespaces:read", "policies:read", "policies:write"],
        "security_scan": ["namespaces:read", "scans:read", "scans:write"]
    }
    
    return permission_map.get(task_type, ["namespaces:read"])
```

## 4. Input Validation

### Data Validation Patterns
```python
from pydantic import BaseModel, validator
from typing import Optional

class SecureNamespacePayload(BaseModel):
    name: str
    description: str
    parent_namespace: str
    
    @validator('name')
    def validate_name(cls, v):
        # Ensure name is safe
        if not v or len(v.strip()) == 0:
            raise ValueError("Name cannot be empty")
        if len(v) > 100:
            raise ValueError("Name too long")
        if not v.replace('-', '').replace('_', '').isalnum():
            raise ValueError("Name contains invalid characters")
        return v.strip()
    
    @validator('description')
    def validate_description(cls, v):
        # Sanitize description
        if v:
            # Remove potential script tags
            v = v.replace('<script>', '').replace('</script>', '')
            # Limit length
            if len(v) > 500:
                v = v[:500] + "..."
        return v
```

### API Input Sanitization
```python
def sanitize_api_input(input_data):
    """Sanitize input data before API calls."""
    if isinstance(input_data, dict):
        sanitized = {}
        for key, value in input_data.items():
            # Sanitize keys
            clean_key = key.strip().replace(' ', '_')
            # Sanitize values
            if isinstance(value, str):
                clean_value = value.strip()
                # Remove potential XSS
                clean_value = clean_value.replace('<', '&lt;').replace('>', '&gt;')
            else:
                clean_value = value
            sanitized[clean_key] = clean_value
        return sanitized
    return input_data
```

## 5. Error Handling Security

### Secure Error Messages
```python
def secure_error_handling(operation_func, *args, **kwargs):
    """Handle errors without exposing sensitive information."""
    try:
        return operation_func(*args, **kwargs)
    except HTTPError as e:
        # Log full error for debugging
        logger.error(f"HTTP error in {operation_func.__name__}: {e}")
        
        # Return safe error message
        if e.response.status_code == 401:
            return {"error": "Authentication failed", "code": 401}
        elif e.response.status_code == 403:
            return {"error": "Insufficient permissions", "code": 403}
        elif e.response.status_code == 404:
            return {"error": "Resource not found", "code": 404}
        else:
            return {"error": "API request failed", "code": e.response.status_code}
    
    except ValidationError as e:
        logger.error(f"Validation error in {operation_func.__name__}: {e}")
        return {"error": "Invalid input data", "code": 400}
    
    except Exception as e:
        logger.error(f"Unexpected error in {operation_func.__name__}: {e}")
        return {"error": "Internal error", "code": 500}
```

## 6. Resource Security

### Namespace Security
```python
def secure_namespace_creation(client, parent_namespace, name, description):
    """Create a namespace with security best practices."""
    
    # Validate inputs
    if not name or not description:
        raise ValueError("Name and description are required")
    
    # Check for existing namespace
    existing = namespaces.get_namespace_by_name(client, parent_namespace, name)
    if existing:
        raise ValueError(f"Namespace '{name}' already exists")
    
    # Create with security metadata
    payload = CreateNamespacePayload(
        meta=NamespaceMeta(
            name=name,
            description=description,
            labels={
                "created_by": "ai_agent",
                "security_level": "standard",
                "created_at": datetime.now().isoformat()
            }
        )
    )
    
    return namespaces.create_namespace(client, parent_namespace, payload)
```

### Policy Security
```python
def apply_security_policy(client, namespace_uuid, policy_config):
    """Apply security policy with validation."""
    
    # Validate policy configuration
    if not policy_config.get("rules"):
        raise ValueError("Policy must have rules")
    
    # Check for dangerous rules
    for rule in policy_config["rules"]:
        if rule.get("action") == "allow_all":
            logger.warning("Policy contains 'allow_all' rule - review required")
    
    # Create policy
    policy = create_policy(client, namespace_uuid, policy_config)
    
    # Log policy creation
    logger.info(f"Security policy created: {policy.uuid}")
    
    return policy
```

## 7. Monitoring & Auditing

### Security Event Logging
```python
def log_security_event(event_type, details, severity="info"):
    """Log security events with appropriate detail."""
    event = {
        "timestamp": datetime.now().isoformat(),
        "event_type": event_type,
        "severity": severity,
        "details": details,
        "agent_id": os.getenv("AGENT_ID", "unknown")
    }
    
    # Log to security log
    logger.info(f"SECURITY_EVENT: {json.dumps(event)}")
    
    # Alert on critical events
    if severity == "critical":
        send_security_alert(event)
```

### Audit Trail
```python
def create_audit_trail(operation, resource, result):
    """Create audit trail for operations."""
    audit_entry = {
        "timestamp": datetime.now().isoformat(),
        "operation": operation,
        "resource": resource,
        "result": "success" if result else "failure",
        "agent_id": os.getenv("AGENT_ID", "unknown")
    }
    
    # Store audit entry
    store_audit_entry(audit_entry)
    
    return audit_entry
```

## 8. Compliance & Standards

### SOC2 Compliance
- **Access Control**: Implement proper authentication and authorization
- **Data Protection**: Ensure no PII handling
- **Audit Logging**: Maintain comprehensive audit trails
- **Security Monitoring**: Monitor for security events
- **Incident Response**: Have procedures for security incidents

### ISO27001 Compliance
- **Information Security**: Protect information assets
- **Risk Management**: Identify and mitigate security risks
- **Security Controls**: Implement appropriate security controls
- **Continuous Improvement**: Regularly review and improve security

## 9. Security Testing

### Automated Security Tests
```python
def test_security_controls():
    """Test security controls."""
    
    # Test authentication
    assert test_authentication()
    
    # Test authorization
    assert test_authorization()
    
    # Test input validation
    assert test_input_validation()
    
    # Test error handling
    assert test_error_handling()
    
    # Test logging security
    assert test_logging_security()
```

### Security Scan Integration
```python
def run_security_scan():
    """Run comprehensive security scan."""
    
    # Run endorctl scan
    scan_result = subprocess.run(
        ["endorctl", "scan"],
        capture_output=True,
        text=True
    )
    
    if scan_result.returncode != 0:
        raise SecurityScanError(f"Security scan failed: {scan_result.stderr}")
    
    return scan_result.stdout
```

## 10. Incident Response

### Security Incident Response
```python
def handle_security_incident(incident_type, details):
    """Handle security incidents."""
    
    # Log incident
    log_security_event("incident", {
        "type": incident_type,
        "details": details
    }, severity="critical")
    
    # Take immediate action
    if incident_type == "unauthorized_access":
        revoke_all_tokens()
        notify_security_team()
    elif incident_type == "data_breach":
        isolate_affected_systems()
        notify_compliance_team()
    
    # Document incident
    document_incident(incident_type, details)
```

### Recovery Procedures
```python
def recover_from_security_incident(incident_id):
    """Recover from security incident."""
    
    # Get incident details
    incident = get_incident(incident_id)
    
    # Implement recovery procedures
    if incident.type == "unauthorized_access":
        reset_authentication()
        verify_system_integrity()
    elif incident.type == "data_breach":
        restore_from_backup()
        verify_data_integrity()
    
    # Update incident status
    update_incident_status(incident_id, "recovered")
```
