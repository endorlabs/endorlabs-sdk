# Endor Cockpit: AI Agent Integration Guide

> **Universal Anchor for All AI Agents**

## 🚀 **Quick Start (30 seconds)**

### **Knowledge Base First**
**CRITICAL**: Always query the Holocron knowledge base before any operations. This portable shared learning index contains:
- API patterns and best practices
- Known quirks and workarounds
- Security guidelines and compliance requirements
- Operational procedures and troubleshooting

```bash
# Query before any operation
uv run python -m holocron query "How do I create a namespace?"
# Review results, then proceed with confidence
```

**Workflow**: Query → Verify → Act → Update if contradictions found

**Reference**: See [docs/holocron/README.md](docs/holocron/README.md) for comprehensive Holocron documentation and [docs/protocols/holocron-setup.md](docs/protocols/holocron-setup.md) for initialization workflows.

### **Critical Requirements**
- **Security**: Always run `endorctl scan` before code changes
- **Linting**: Max 88 chars/line, sorted imports, no trailing whitespace
- **Dependencies**: Pin exact versions, avoid `latest`
- **Environment**: Set `ENDOR_API`, `ENDOR_API_CREDENTIALS_KEY`, `ENDOR_API_CREDENTIALS_SECRET`

---

## 📋 **Project Context**

**Endor Cockpit** is a production-ready foundational service:
- **Purpose**: Administer, operate and scan with Endor Labs tooling through REST APIs
- **Data Classification**: Public (no PII handling)
- **Deployment**: Production environment, global region
- **Security**: Paramount importance
- **Architecture**: Resource-oriented SDK pattern

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

## 🛠️ **Tools**

### **LLM Tool Schema**
```json
{
  "name": "create_namespace",
  "description": "Create a new namespace",
  "parameters": {
    "type": "object",
    "properties": {
      "parent_namespace": {"type": "string"},
      "name": {"type": "string"},
      "description": {"type": "string"}
    },
    "required": ["parent_namespace", "name", "description"]
  }
}
```

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

---

## 📊 **Examples**

### **Complete Workflow**
```python
# 1. Initialize client
from endor_cockpit.api_client import APIClient
client = APIClient()

# 2. List existing namespaces
namespaces_list = namespaces.list_namespaces(client, "endor-solutions-tgowan.cockpit")

# 3. Create new namespace
canonical_parent = "endor-solutions-tgowan.cockpit"
payload = CreateNamespacePayload(
    meta=NamespaceMetaCreate(
        name="agent-created-namespace",
        description="Created by AI agent"
    )
)
new_namespace = namespaces.create_namespace(client, canonical_parent, payload)

# 4. Verify creation
if new_namespace:
    print(f"Created: {new_namespace.uuid}")
```

### **Error Handling Pattern**
```python
try:
    result = namespaces.create_namespace(client, parent, payload)
    if result:
        return f"Success: {result.uuid}"
    else:
        return "Failed: No result returned"
except Exception as e:
    return f"Error: {str(e)}"
```

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
