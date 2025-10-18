# Endor Cockpit: AI Agent Integration Guide

## 1. Overview

This document provides AI agents with comprehensive guidance for working with the Endor Cockpit project. Endor Cockpit is a foundational workspace designed to administer, operate and scan with Endor Labs tooling through REST APIs.

As an agent, your primary goal is to use this workspace to perform tasks such as:
- **Administration**: Managing Endor Labs platform resources and configurations
- **Operations**: Monitoring, maintenance, and operational tasks
- **Security**: Scanning, compliance, and security workflow automation
- **Development**: Contributing to and extending the SDK capabilities

## 1.1 Project Context

**Endor Cockpit** is a production-ready foundational service that:
- **Data Classification**: Public (no PII handling)
- **Deployment**: Production environment, global region
- **Security**: SOC2 and ISO27001 compliant
- **Architecture**: Resource-oriented SDK pattern
- **Integration**: REST API-based Endor Labs platform interaction

> 📋 **For detailed project context, see [catalog-info.yaml](./catalog-info.yaml)**

## 1.2 Quick Navigation

### 📚 Comprehensive Documentation
- **[docs/agents/](./docs/agents/)** - Complete agent documentation
- **[Core Principles](./docs/agents/core-principles.md)** - Fundamental guidelines
- **[Development Guidelines](./docs/agents/development.md)** - Development best practices
- **[Usage Patterns](./docs/agents/usage-patterns.md)** - Common patterns and examples
- **[Resource Guides](./docs/agents/resource-guides.md)** - Resource-specific API documentation
- **[Security Guidelines](./docs/agents/security.md)** - Security-first practices
- **[Tool Definitions](./docs/agents/tool-definitions.md)** - LLM tool schemas
- **[Agent Insights](./docs/agents/insights.md)** - Critical discoveries and patterns
- **[Quick Reference](./docs/agents/quick-reference.md)** - Essential patterns and fixes

### 🎯 Agent Type Quick Start
- **🤖 Developing the SDK**: Start with [Development Guidelines](./docs/agents/development.md)
- **🔧 Using the SDK**: Start with [Usage Patterns](./docs/agents/usage-patterns.md)
- **🔍 Scanning/Auditing**: Start with [Security Guidelines](./docs/agents/security.md)

## 2. Core Principles for Agents

## 2a. Agents DEVELOPING the SDK

To ensure smooth and reliable operation, please adhere to the following principles:

### Security is Paramount
Follow the instructions at `https://docs.endorlabs.com/endorctl/commands/scan/` to check for security policy violations for all of the following scenarios:
- A package is to be added or modified in this repository, run an SCA scan.
- A change in first-party code that is syntactically correct, and also completes the business logic requirements of a function.

### Declarative & Idempotent Operations
Whenever possible, perform operations that are idempotent. This means that repeated calls with the same parameters will not have unintended side effects. For example, fetching a resource multiple times should always yield the same result without changing the system state.

### Resource-Oriented Interaction
The SDK is organized around API resources (e.g., `namespaces`, `policies`). Each resource has a dedicated module within the `endor_cockpit.resources` package, containing functions to interact with that resource (e.g., `list_namespaces`, `create_namespace`).

### Error Handling
The SDK is designed to be predictable. The `APIClient` will handle standard HTTP errors, retries, and rate limiting. However, you should be prepared to handle potential exceptions, such as:
- `requests.exceptions.HTTPError`: For API-level errors (e.g., 4xx or 5xx status codes). Inspect the response for details.
- `pydantic.ValidationError`: If the data returned by the API does not match the expected Pydantic model, indicating a potential API contract mismatch.

### Environment Configuration
The SDK is configured exclusively through environment variables. You must ensure the following variables are set in your execution environment before initializing the client:
- `ENDOR_API`: The base URL for the Endor Labs API (e.g., `https://api.endorlabs.com`).
- `ENDOR_API_CREDENTIALS_KEY`: Your Endor Labs API key.
- `ENDOR_API_CREDENTIALS_SECRET`: Your Endor Labs API secret.

### Error Logging
The SDK's error logging must be secured through the logging filter to ensure no sensitive data or PII are leaked. They should provide sufficient detail to action on fixing the problem (e.g., confirming type variable conforms to the schema then return the relevant section in the API spec). The filters can be through the APIClient class's logger object.

## 2b. Agents leveraging the SDK in tasks or automation.

### Task-based Access Controls
When you are an agent invoking functions in this SDK and are being requested to provide service accounts, create a bespoke API token that matches the intended task. The service account permissions are to be minimally scoped to only provide the necessary operations for the resource that is being modified. 

The expiration date of the provided token is based upon an estimated minimal time for tasks to complete. If the expiration time is less than the minimally allowed time by Endor Labs, then append the suggested expiry date to the service account name.

### Information Richness
When you are creating or modifying resources in an Endor namespace, provide descriptions and naming conventions that provide the current goals, tasks or responsibilities of that resource that can be understood for both developer, administration and security/risk management tasks while still conforming to a standardized pattern to be defined by the user and stored in the AGENTS.md file. 

## 2.c Agents SCANNING the SDK
    Read AGENTS.md for architecture, design decisions, coding style and testing instructions.
    Read the Backstage/Catalog file (e.g., /catalog-info.yaml) to get deployment context (e.g., "This is a public service," or "PII data is processed here").

    Combine both to provide a highly contextual fix: "Refactoring this code (using conventions from AGENTS.md) is critical because the function processes PII (as defined in catalog-info.yaml), and the current code's logging filter is not covering this logging filter."

## 3. Critical Platform Insights

### **Namespace Hierarchy: Canonical Naming Pattern**
**CRITICAL**: Endor Labs uses **canonical hierarchical naming** for namespace relationships, not UUIDs.

#### **✅ CORRECT Pattern**
```python
# Use canonical hierarchical names for parent-child relationships
canonical_parent = f"{tenant_namespace}.{parent_name}"
# Example: "endor-solutions-tgowan.cockpit.integration-test-parent-{timestamp}"

# Create child namespace
child_result = namespaces.create_namespace(client, canonical_parent, child_payload)
```

#### **❌ INCORRECT Pattern**
```python
# DON'T use UUIDs as parents - this will fail with 403 Forbidden
parent_namespace.uuid  # "68f3b2956795a2693a0f5bec" - FAILS!
```

### **API Permission Model**
**DISCOVERY**: The API key permission model is based on **canonical naming**, not UUIDs.

#### **✅ ALLOWED Operations**
- **Tenant-level operations**: Use tenant name (`endor-solutions-tgowan.cockpit`)
- **Hierarchy operations**: Use canonical parent names (`tenant.namespace.child`)
- **All CRUD operations**: Create, read, update, delete within allowed scope

#### **❌ FORBIDDEN Operations**
- **UUID-based parent relationships**: Cannot use UUIDs as parents
- **Cross-tenant operations**: Cannot access other tenants
- **Unauthorized resource access**: Beyond permission scope

### **SDK Implementation Patterns**

#### **Required Classes for Full Functionality**
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

#### **Function Signatures**
```python
# CRITICAL: get_namespace requires parent_namespace parameter
def get_namespace(client: APIClient, parent_namespace: str, namespace_uuid: str) -> Optional[Namespace]

# CRITICAL: update_namespace requires UpdateNamespacePayload
def update_namespace(client: APIClient, parent_namespace: str, namespace_uuid: str, payload: UpdateNamespacePayload) -> Optional[Namespace]
```

## 4. Authentication

Authentication is handled automatically by the `APIClient`. When instantiated, the client will use the environment variables to obtain an auth token and will manage token refreshes. Your only responsibility is to ensure the environment variables are correctly set.

## 5. SDK Usage Patterns

### Initializing the Client
All interactions begin by creating an instance of the `APIClient`.

```python
from endor_cockpit.api_client import APIClient

# The client will automatically authenticate using environment variables
client = APIClient()
```

### Working with Resources
Here are examples of common CRUD (Create, Read, Update, Delete) operations using the `namespaces` resource.

**Listing Namespaces:**
```python
from endor_cockpit.resources import namespaces

# The tenant namespace is typically the top-level namespace for your organization - referred to as
tenant_namespace = "your-tenant-namespace"
all_namespaces = namespaces.list_namespaces(client, tenant_namespace)

for ns in all_namespaces:
    print(f"Namespace: {ns.meta.name}, UUID: {ns.uuid}")
```

**Creating a Namespace:**
```python
from endor_cockpit.resources import namespaces
from endor_cockpit.resources.namespaces import CreateNamespacePayload, NamespaceMetaCreate

tenant_namespace = "your-tenant-namespace"

# Use Pydantic models for type-safe payloads
new_namespace_payload = CreateNamespacePayload(
    meta=NamespaceMetaCreate(
        name="my-new-agent-namespace",
        description="A namespace created by an AI agent."
    )
)

created_namespace = namespaces.create_namespace(
    client,
    tenant_namespace,
    new_namespace_payload
)

if created_namespace:
    print(f"Successfully created namespace with UUID: {created_namespace.uuid}")
```

**Deleting a Namespace:**
```python
from endor_cockpit.resources import namespaces

tenant_namespace = "your-tenant-namespace"
namespace_uuid_to_delete = "..." # UUID of the namespace to delete

success = namespaces.delete_namespace(
    client,
    tenant_namespace,
    namespace_uuid_to_delete
)

if success:
    print("Namespace deleted successfully.")
```

## 6. Tool Definition & Function Calling

To expose SDK functionality to a Large Language Model (LLM), you should define tools that map directly to the SDK's resource functions.

**Example Tool Definition for `create_namespace`:**

```json
{
  "name": "create_namespace",
  "description": "Creates a new namespace within a specified parent namespace.",
  "parameters": {
    "type": "object",
    "properties": {
      "parent_namespace": {
        "type": "string",
        "description": "The name of the parent (tenant) namespace."
      },
      "name": {
        "type": "string",
        "description": "The name for the new namespace."
      },
      "description": {
        "type": "string",
        "description": "A description for the new namespace."
      }
    },
    "required": ["parent_namespace", "name", "description"]
  }
}
```

## 7. The OpenAPI Specification as a Knowledge Source

The Endor Labs API is defined by an OpenAPI specification. The SDK's `get_openapi_spec()` method on the `APIClient` can be used to retrieve this specification and place it into the /tmp or a provided path to write the file in. 

This specification is the ultimate source of truth for all available API endpoints, parameters, and data schemas. This will allow you, the agent, to perform semantic searches and ask questions about the API, such as:
- "What parameters are required to create a policy?"
- "Show me the data model for a secret."
- "Which endpoints are related to dependency findings?"

By leveraging this vector database, you can dynamically discover and utilize the full range of the Endor Labs API through the SDK.  You are intended to be preserve LLM token bandwidth through narrow queries to capture just the information you need for a specific task.

## 8. Workspace Folder

For local testing and development, use the `workspace/` folder which is excluded from version control. This folder is **unique to each user** and contains:
- Integration test results and configurations
- Temporary policy configurations
- Development scripts and utilities
- Test-specific documentation
- User-specific API configurations
- **Agent notes and task documentation** (like this file)

The workspace folder allows agents to work with project-specific configurations without cluttering the main repository. Each user's workspace is isolated and not shared across the team. If you would like to collaborate in a shared cockpit, consider working in a branch and removing the .gitignore for that workspace.

**Note for AI Agents**: When creating documentation, notes, or task-specific files, place them in the `workspace/` folder rather than the root directory to keep the repository clean and organized.