# Endor Labs SDK: A Guide for AI Agents

## 1. Overview

This document provides AI agents with the necessary information to effectively utilize the Endor Labs Python SDK. The SDK is designed to be a robust, predictable, and agent-friendly interface for interacting with the Endor Labs API.

As an agent, your primary goal is to use this SDK to perform tasks on behalf of a user, such as managing resources, retrieving data, and automating security workflows within the Endor Labs platform.

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
The SDK is organized around API resources (e.g., `namespaces`, `policies`). Each resource has a dedicated module within the `endor_sdk.resources` package, containing functions to interact with that resource (e.g., `list_namespaces`, `create_namespace`).

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
The SDK's error logging must be secured through the logging filter to ensure no sensitive data or PII are leaked. They should provide sufficient detail to action on fixing the problem (e.g., confirming type variable conforms to the schema then return the relevant section in the API spec). The API specification is retrieved during first creation of the APIClient class.The filters can be through the APIClient class's logger object.

## 2b. Agents leveraging the SDK in tasks or automation.

### Task-based Access Controls
When you are an agent invoking functions in this SDK and are being requested to provide service accounts, create a bespoke API token that matches the intended task. The service account permissions are to be minimally scoped to only provide the necesasary operations for the resource that is being modified. 

The expiration date of the provided token is based upon an estimated minimal time for tasks to complete. If the expiration time is less than the minimally allowed time by Endor Labs, then append the suggested expiry date to the service account name.

### Information Richness
When you are creating or modifying resources in an Endor namespace, provide descriptions and naming conventions that provide the current goals, tasks or responsibilites of that resource that can be understood for both developer, administration and security/risk management tasks while still conforming to a standardized pattern to be defined by the user and stored in the AGENTS.md file. 

## 2.c Agents SCANNING the SDK
    Read AGENTS.md for architecture, design decisions, coding style and testing instructions.
    Read the Backstage/Catalog file (e.g., /catalog-info.yaml) to get deployment context (e.g., "This is a public service," or "PII data is processed here").

    Combine both to provide a highly contextual fix: "Refactoring this code (using conventions from AGENTS.md) is critical because the function processes PII (as defined in catalog-info.yaml), and the current code's logging filter is not covering this logging filter."


## 3. Authentication

Authentication is handled automatically by the `APIClient`. When instantiated, the client will use the environment variables to obtain an auth token and will manage token refreshes. Your only responsibility is to ensure the environment variables are correctly set.

## 4. SDK Usage Patterns

### Initializing the Client
All interactions begin by creating an instance of the `APIClient`.

```python
from endor_sdk.api_client import APIClient

# The client will automatically authenticate using environment variables
client = APIClient()
```

### Working with Resources
Here are examples of common CRUD (Create, Read, Update, Delete) operations using the `namespaces` resource.

**Listing Namespaces:**
```python
from endor_sdk.resources import namespaces

# The tenant namespace is typically the top-level namespace for your organization - referred to as
tenant_namespace = "your-tenant-namespace"
all_namespaces = namespaces.list_namespaces(client, tenant_namespace)

for ns in all_namespaces:
    print(f"Namespace: {ns.meta.name}, UUID: {ns.uuid}")
```

**Creating a Namespace:**
```python
from endor_sdk.resources import namespaces
from endor_sdk.resources.namespaces import CreateNamespacePayload, NamespaceMeta

tenant_namespace = "your-tenant-namespace"

# Use Pydantic models for type-safe payloads
new_namespace_payload = CreateNamespacePayload(
    meta=NamespaceMeta(
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
from endor_sdk.resources import namespaces

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

## 5. Tool Definition & Function Calling

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

## 6. The OpenAPI Specification as a Knowledge Source

The Endor Labs API is defined by an OpenAPI specification. The SDK's `get_openapi_spec()` method on the `APIClient` can be used to retrieve this specification and place it into the /tmp or a provided path to write the file in. 

This specification is the ultimate source of truth for all available API endpoints, parameters, and data schemas. This will allow you, the agent, to perform semantic searches and ask questions about the API, such as:
- "What parameters are required to create a policy?"
- "Show me the data model for a secret."
- "Which endpoints are related to dependency findings?"

By leveraging this vector database, you can dynamically discover and utilize the full range of the Endor Labs API through the SDK.  You are intended to be preserve LLM token bandwidth through narrow queries to capture just the information you need for a specific task.
