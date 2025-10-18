# Tool Definitions for AI Agents

## 1. Overview

This document provides LLM tool definitions for integrating with the Endor Cockpit SDK. These definitions can be used to create function calling interfaces for AI agents.

## 2. Core API Client Tools

### Initialize Client
```json
{
  "name": "initialize_endor_client",
  "description": "Initialize the Endor Cockpit API client with authentication",
  "parameters": {
    "type": "object",
    "properties": {
      "api_url": {
        "type": "string",
        "description": "Base URL for Endor Labs API (default: from environment)",
        "default": null
      }
    },
    "required": []
  }
}
```

### Test Connection
```json
{
  "name": "test_endor_connection",
  "description": "Test connection to Endor Labs API",
  "parameters": {
    "type": "object",
    "properties": {
      "tenant_namespace": {
        "type": "string",
        "description": "Tenant namespace to test connection"
      }
    },
    "required": ["tenant_namespace"]
  }
}
```

## 3. Namespace Management Tools

### List Namespaces
```json
{
  "name": "list_namespaces",
  "description": "List all namespaces in a tenant",
  "parameters": {
    "type": "object",
    "properties": {
      "tenant_namespace": {
        "type": "string",
        "description": "Parent tenant namespace"
      },
      "include_children": {
        "type": "boolean",
        "description": "Include child namespaces",
        "default": true
      }
    },
    "required": ["tenant_namespace"]
  }
}
```

### Create Namespace
```json
{
  "name": "create_namespace",
  "description": "Create a new namespace",
  "parameters": {
    "type": "object",
    "properties": {
      "parent_namespace": {
        "type": "string",
        "description": "Parent namespace name"
      },
      "name": {
        "type": "string",
        "description": "Name for the new namespace"
      },
      "description": {
        "type": "string",
        "description": "Description for the namespace"
      },
      "labels": {
        "type": "object",
        "description": "Optional labels for the namespace",
        "additionalProperties": {"type": "string"}
      }
    },
    "required": ["parent_namespace", "name", "description"]
  }
}
```

### Get Namespace
```json
{
  "name": "get_namespace",
  "description": "Get details of a specific namespace",
  "parameters": {
    "type": "object",
    "properties": {
      "namespace_uuid": {
        "type": "string",
        "description": "UUID of the namespace"
      }
    },
    "required": ["namespace_uuid"]
  }
}
```

### Delete Namespace
```json
{
  "name": "delete_namespace",
  "description": "Delete a namespace",
  "parameters": {
    "type": "object",
    "properties": {
      "namespace_uuid": {
        "type": "string",
        "description": "UUID of the namespace to delete"
      },
      "force": {
        "type": "boolean",
        "description": "Force deletion even if namespace has children",
        "default": false
      }
    },
    "required": ["namespace_uuid"]
  }
}
```

## 4. Policy Management Tools

### List Policies
```json
{
  "name": "list_policies",
  "description": "List policies for a namespace",
  "parameters": {
    "type": "object",
    "properties": {
      "namespace_uuid": {
        "type": "string",
        "description": "UUID of the namespace"
      },
      "policy_type": {
        "type": "string",
        "description": "Filter by policy type",
        "enum": ["security", "compliance", "access", "all"]
      }
    },
    "required": ["namespace_uuid"]
  }
}
```

### Create Policy
```json
{
  "name": "create_policy",
  "description": "Create a new policy",
  "parameters": {
    "type": "object",
    "properties": {
      "namespace_uuid": {
        "type": "string",
        "description": "UUID of the namespace"
      },
      "name": {
        "type": "string",
        "description": "Name of the policy"
      },
      "description": {
        "type": "string",
        "description": "Description of the policy"
      },
      "policy_type": {
        "type": "string",
        "description": "Type of policy",
        "enum": ["security", "compliance", "access"]
      },
      "rules": {
        "type": "array",
        "description": "Policy rules",
        "items": {
          "type": "object",
          "properties": {
            "action": {"type": "string"},
            "condition": {"type": "string"},
            "effect": {"type": "string"}
          }
        }
      }
    },
    "required": ["namespace_uuid", "name", "description", "policy_type", "rules"]
  }
}
```

## 5. Security Scanning Tools

### Run Security Scan
```json
{
  "name": "run_security_scan",
  "description": "Run a security scan on a namespace or resource",
  "parameters": {
    "type": "object",
    "properties": {
      "target": {
        "type": "string",
        "description": "Target namespace UUID or resource identifier"
      },
      "scan_type": {
        "type": "string",
        "description": "Type of security scan",
        "enum": ["vulnerability", "compliance", "secrets", "dependencies", "full"]
      },
      "include_dependencies": {
        "type": "boolean",
        "description": "Include dependency scanning",
        "default": true
      }
    },
    "required": ["target", "scan_type"]
  }
}
```

### Get Scan Results
```json
{
  "name": "get_scan_results",
  "description": "Get results from a security scan",
  "parameters": {
    "type": "object",
    "properties": {
      "scan_id": {
        "type": "string",
        "description": "UUID of the scan"
      },
      "include_details": {
        "type": "boolean",
        "description": "Include detailed scan results",
        "default": false
      }
    },
    "required": ["scan_id"]
  }
}
```

### List Security Findings
```json
{
  "name": "list_security_findings",
  "description": "List security findings for a namespace",
  "parameters": {
    "type": "object",
    "properties": {
      "namespace_uuid": {
        "type": "string",
        "description": "UUID of the namespace"
      },
      "severity": {
        "type": "string",
        "description": "Filter by severity level",
        "enum": ["critical", "high", "medium", "low", "all"]
      },
      "status": {
        "type": "string",
        "description": "Filter by finding status",
        "enum": ["open", "resolved", "ignored", "all"]
      }
    },
    "required": ["namespace_uuid"]
  }
}
```

## 6. Resource Discovery Tools

### Discover API Capabilities
```json
{
  "name": "discover_api_capabilities",
  "description": "Discover available API capabilities and endpoints",
  "parameters": {
    "type": "object",
    "properties": {
      "include_examples": {
        "type": "boolean",
        "description": "Include example requests",
        "default": false
      }
    },
    "required": []
  }
}
```

### Get Resource Schema
```json
{
  "name": "get_resource_schema",
  "description": "Get schema for a specific resource type",
  "parameters": {
    "type": "object",
    "properties": {
      "resource_type": {
        "type": "string",
        "description": "Type of resource",
        "enum": ["namespace", "policy", "secret", "scan", "finding"]
      },
      "operation": {
        "type": "string",
        "description": "Operation type",
        "enum": ["create", "read", "update", "delete", "list"]
      }
    },
    "required": ["resource_type", "operation"]
  }
}
```

## 7. Service Account Management Tools

### Create Service Account
```json
{
  "name": "create_service_account",
  "description": "Create a service account for agent operations",
  "parameters": {
    "type": "object",
    "properties": {
      "namespace_uuid": {
        "type": "string",
        "description": "UUID of the namespace"
      },
      "name": {
        "type": "string",
        "description": "Name of the service account"
      },
      "description": {
        "type": "string",
        "description": "Description of the service account"
      },
      "permissions": {
        "type": "array",
        "description": "List of permissions",
        "items": {"type": "string"}
      },
      "expiration_hours": {
        "type": "integer",
        "description": "Expiration time in hours",
        "default": 24
      }
    },
    "required": ["namespace_uuid", "name", "description", "permissions"]
  }
}
```

### List Service Accounts
```json
{
  "name": "list_service_accounts",
  "description": "List service accounts for a namespace",
  "parameters": {
    "type": "object",
    "properties": {
      "namespace_uuid": {
        "type": "string",
        "description": "UUID of the namespace"
      },
      "include_expired": {
        "type": "boolean",
        "description": "Include expired service accounts",
        "default": false
      }
    },
    "required": ["namespace_uuid"]
  }
}
```

### Revoke Service Account
```json
{
  "name": "revoke_service_account",
  "description": "Revoke a service account",
  "parameters": {
    "type": "object",
    "properties": {
      "service_account_uuid": {
        "type": "string",
        "description": "UUID of the service account"
      }
    },
    "required": ["service_account_uuid"]
  }
}
```

## 8. Monitoring and Auditing Tools

### Get Audit Logs
```json
{
  "name": "get_audit_logs",
  "description": "Get audit logs for a namespace or operation",
  "parameters": {
    "type": "object",
    "properties": {
      "namespace_uuid": {
        "type": "string",
        "description": "UUID of the namespace"
      },
      "operation_type": {
        "type": "string",
        "description": "Filter by operation type",
        "enum": ["create", "read", "update", "delete", "scan", "all"]
      },
      "start_time": {
        "type": "string",
        "description": "Start time for logs (ISO format)"
      },
      "end_time": {
        "type": "string",
        "description": "End time for logs (ISO format)"
      }
    },
    "required": ["namespace_uuid"]
  }
}
```

### Get Security Events
```json
{
  "name": "get_security_events",
  "description": "Get security events for a namespace",
  "parameters": {
    "type": "object",
    "properties": {
      "namespace_uuid": {
        "type": "string",
        "description": "UUID of the namespace"
      },
      "severity": {
        "type": "string",
        "description": "Filter by severity",
        "enum": ["critical", "high", "medium", "low", "all"]
      },
      "event_type": {
        "type": "string",
        "description": "Filter by event type",
        "enum": ["scan", "policy_violation", "access", "all"]
      }
    },
    "required": ["namespace_uuid"]
  }
}
```

## 9. Utility Tools

### Validate Configuration
```json
{
  "name": "validate_configuration",
  "description": "Validate Endor Cockpit configuration",
  "parameters": {
    "type": "object",
    "properties": {
      "check_connectivity": {
        "type": "boolean",
        "description": "Check API connectivity",
        "default": true
      },
      "check_permissions": {
        "type": "boolean",
        "description": "Check required permissions",
        "default": true
      }
    },
    "required": []
  }
}
```

### Get System Status
```json
{
  "name": "get_system_status",
  "description": "Get overall system status",
  "parameters": {
    "type": "object",
    "properties": {
      "include_metrics": {
        "type": "boolean",
        "description": "Include performance metrics",
        "default": false
      }
    },
    "required": []
  }
}
```

## 10. Tool Implementation Examples

### Python Implementation
```python
def list_namespaces(tenant_namespace, include_children=True):
    """List namespaces with optional children."""
    from endor_cockpit.api_client import APIClient
    from endor_cockpit.resources import namespaces
    
    client = APIClient()
    return namespaces.list_namespaces(client, tenant_namespace, include_children)
```

### Error Handling
```python
def safe_tool_execution(tool_func, *args, **kwargs):
    """Safely execute a tool with error handling."""
    try:
        result = tool_func(*args, **kwargs)
        return {"success": True, "result": result}
    except Exception as e:
        return {"success": False, "error": str(e)}
```

### Tool Validation
```python
def validate_tool_inputs(schema, inputs):
    """Validate tool inputs against schema."""
    from jsonschema import validate, ValidationError
    
    try:
        validate(instance=inputs, schema=schema)
        return True
    except ValidationError as e:
        return False, str(e)
```

## 11. Tool Integration Patterns

### Batch Operations
```python
def batch_namespace_operations(operations):
    """Execute multiple namespace operations in batch."""
    results = []
    
    for operation in operations:
        try:
            result = execute_operation(operation)
            results.append({"success": True, "result": result})
        except Exception as e:
            results.append({"success": False, "error": str(e)})
    
    return results
```

### Tool Chaining
```python
def create_secure_namespace(parent_namespace, name, description):
    """Create a namespace with security policies."""
    
    # Create namespace
    namespace = create_namespace(parent_namespace, name, description)
    
    # Apply default security policy
    policy = create_policy(namespace.uuid, "default-security", "Default security policy")
    
    # Run initial security scan
    scan = run_security_scan(namespace.uuid, "full")
    
    return {
        "namespace": namespace,
        "policy": policy,
        "scan": scan
    }
```
