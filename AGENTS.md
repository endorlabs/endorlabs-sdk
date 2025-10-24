# Endor Cockpit: AI Agent Integration Guide

> **Universal Anchor for All AI Agents in IDEs**

## 🚀 **Quick Start (30 seconds)**

### **IDE Integration Ready**
**CRITICAL**: This toolkit is designed for seamless integration with AI-powered development environments. The SDK provides:
- Type-safe API operations with comprehensive error handling
- Built-in security scanning capabilities
- Resource-oriented patterns for consistent operations
- Production-ready authentication and rate limiting

```python
# Initialize client (auto-authenticates via environment variables)
from endor_cockpit.api_client import APIClient
client = APIClient()

# List namespaces
from endor_cockpit.resources import namespace
namespaces = namespace.list_namespaces(client, "tenant.namespace")
```

**Workflow**: Initialize → Authenticate → Operate → Handle Errors

### **Critical Requirements**
- **Security**: Always run `endorctl scan` before code changes
- **Linting**: Max 88 chars/line, sorted imports, no trailing whitespace
- **Dependencies**: Pin exact versions, avoid `latest`
- **Environment**: Set `ENDOR_API`, `ENDOR_API_CREDENTIALS_KEY`, `ENDOR_API_CREDENTIALS_SECRET`

---

## 📋 **Project Context**

**Endor Cockpit** is a production-ready Python SDK for AI-powered IDEs:
- **Purpose**: Integrate Endor Labs security platform with AI development tools
- **Data Classification**: Public (no PII handling)
- **Deployment**: Production environment, global region
- **Security**: Paramount importance
- **Architecture**: Resource-oriented SDK pattern

## 🤖 **Agent Roles & IDE Integration**

### **Developer Agent**
- **Primary Function**: Code analysis, dependency management, vulnerability assessment
- **Key Operations**: Project scanning, finding management, policy evaluation
- **IDE Integration**: Seamless integration with development workflows

### **Security Agent**
- **Primary Function**: Security policy enforcement, compliance monitoring, risk assessment
- **Key Operations**: Policy management, security scanning, finding triage
- **IDE Integration**: Real-time security feedback and policy enforcement

### **Operations Agent**
- **Primary Function**: Infrastructure management, namespace administration, system monitoring
- **Key Operations**: Namespace management, repository administration, system health monitoring
- **IDE Integration**: DevOps workflow integration and infrastructure automation

---

## 🏗️ **Development**

### **Project Structure**
```
endor_cockpit/
├── api_client.py          # Core API client
├── resources/            # Resource modules (namespaces, policies, etc.)
└── models/               # Pydantic data models
```

### **Code Standards**
- **Python**: 3.11-3.13, test on 3.13
- **Dependencies**: `requests==2.32.5`, `pydantic==2.12.3`
- **Tools**: `ruff`, `black`, `pytest`, `endorctl`

### **Function Pattern**
```python
def create_resource(
    client: APIClient,
    parent_namespace: str,
    payload: CreateResourcePayload
) -> Optional[Resource]:
    """Create resource with proper error handling."""
```

---

## 🚨 **Linting & CI Prevention**

### **Pre-Development Checklist**
- [ ] Line length ≤ 88 characters
- [ ] Imports sorted and unused removed
- [ ] No trailing whitespace or blank line whitespace
- [ ] F-strings only with placeholders
- [ ] Dependencies pinned (no `latest`)

### **Quick Linting Commands**
```bash
uv run ruff check .          # Check all issues
uv run ruff check . --fix    # Auto-fix issues
uv run ruff format .         # Format code
uv run pytest               # Test functionality
```

### **Common Fixes**
- **E501**: Break long lines with parentheses/backslashes
- **F401**: Remove unused imports
- **W291/W293**: Remove trailing/blank line whitespace  
- **F541**: Remove `f` prefix from strings without placeholders
- **C901**: Accept for complex but necessary methods

---

## 🔧 **Usage**

### **Client Initialization**
```python
from endor_cockpit.api_client import APIClient
client = APIClient()  # Auto-authenticates via env vars
```

### **Namespace Operations**
```python
from endor_cockpit.resources import namespace
from endor_cockpit.resources.namespace import CreateNamespacePayload

# List namespaces
all_namespaces = namespace.list_namespaces(client, "tenant-namespace")

# Create namespace (CRITICAL: Use canonical naming)
canonical_parent = f"{tenant_namespace}.{parent_name}"
payload = CreateNamespacePayload(meta=NamespaceMetaCreate(name="test", description="Agent created"))
created = namespace.create_namespace(client, canonical_parent, payload)
```

### **Critical Patterns**
- **✅ CORRECT**: Use canonical naming (`tenant.namespace.child`)
- **❌ WRONG**: Don't use UUIDs as parents (403 Forbidden)
- **Required**: `parent_namespace` parameter for all operations
- **Payloads**: Use Pydantic models for type safety

---

## 🛠️ **LLM Tool Integration**

### **Tool Schema Pattern**
```json
{
  "name": "create_namespace",
  "description": "Create a new namespace in the Endor Labs platform",
  "parameters": {
    "type": "object",
    "properties": {
      "parent_namespace": {
        "type": "string",
        "description": "Canonical parent namespace (e.g., 'tenant.namespace')"
      },
      "name": {
        "type": "string",
        "description": "Name of the new namespace"
      },
      "description": {
        "type": "string",
        "description": "Description of the namespace purpose"
      }
    },
    "required": ["parent_namespace", "name", "description"]
  }
}
```

### **Available Resource Operations**
- **Namespace**: `list_namespaces`, `create_namespace`, `get_namespace`, `update_namespace`, `delete_namespace`
- **Project**: `list_projects`, `create_project`, `get_project`, `update_project`, `delete_project`
- **Finding**: `list_findings`, `get_finding`, `update_finding`, `delete_finding`
- **Policy**: `list_policies`, `create_policy`, `get_policy`, `update_policy`, `delete_policy`
- **Repository**: `list_repositories`, `create_repository`, `get_repository`, `update_repository`
- **PackageVersion**: `list_package_versions`, `get_package_version`, `update_package_version`

### **Error Handling**
- **HTTP errors**: Handle 4xx/5xx status codes
- **Validation errors**: Handle Pydantic validation failures
- **Network issues**: Retry logic for transient failures
- **Rate limiting**: Respect API limits

---

## 🔒 **Security**

### **Security-First Development**
- **Always scan**: `endorctl scan` before any code changes
- **Scan scenarios**: Package changes, first-party code, dependency updates
- **No PII**: This project handles no PII data
- **Secure logging**: Filter sensitive data from logs

### **Environment Security**
- **Credentials**: Use environment variables only
- **No hardcoded secrets**: All secrets via env vars
- **Secure logging**: No sensitive data in logs
- **Input validation**: Validate all inputs

### **Git Citizenship**
- **.workspace**: Provide ephemeral scripts in the .workspace folder


---

## 🎯 **Quick Reference**

### **Essential Commands**
```bash
# Development workflow
uv run ruff check .          # Lint
uv run ruff format .         # Format  
uv run pytest               # Test
endorctl scan               # Security

# Environment setup
export ENDOR_API="https://api.endorlabs.com"
export ENDOR_API_CREDENTIALS_KEY="your-key"
export ENDOR_API_CREDENTIALS_SECRET="your-secret"
```

### **Critical Patterns**
- **Canonical naming**: `tenant.namespace.child` (not UUIDs)
- **Line length**: 88 characters max
- **Imports**: Sorted, no unused
- **Security**: Always scan before changes
- **Dependencies**: Pin exact versions

---

*This guide serves as the universal anchor for all AI agents working with Endor Cockpit.*
