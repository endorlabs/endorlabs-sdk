# Endor Labs Python SDK

[![Python CI](https://github.com/<your-org>/<your-repo>/actions/workflows/ci.yml/badge.svg)](https://github.com/<your-org>/<your-repo>/actions/workflows/ci.yml)

A Python SDK for interacting with the Endor Labs API, designed for both human developers and AI agents.

## Features

- **Modern Tooling**: Uses `uv` for dependency management and `ruff` for linting.
- **Robust API Client**: Handles authentication, rate limiting, and retries automatically.
- **Type-Safe Data Models**: Leverages Pydantic for clear, validated API data structures.
- **Resource-Oriented Design**: An intuitive structure with modules dedicated to specific API resources.
- **Agent-Friendly**: Comes with detailed documentation (`AGENTS.md`) specifically for AI agent integration.

## Installation

It is recommended to use a virtual environment.

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/<your-org>/<your-repo>.git
    cd <your-repo>
    ```

2.  **Install dependencies with `uv`:**
    ```bash
    pip install uv
    uv pip install -e .[dev]
    ```

## Quick Start

Ensure your environment variables are set before running the application:

```bash
export ENDOR_API="https://api.endorlabs.com"
export ENDOR_API_CREDENTIALS_KEY="your-api-key"
export ENDOR_API_CREDENTIALS_SECRET="your-api-secret"
```

Here's a simple example of listing namespaces:

```python
from endor_sdk.api_client import APIClient
from endor_sdk.resources import namespaces

# Initialize the client (authenticates automatically)
client = APIClient()

# Your organization's top-level namespace
tenant_namespace = "your-tenant-namespace"

# List all namespaces
try:
    all_namespaces = namespaces.list_namespaces(client, tenant_namespace)
    for ns in all_namespaces:
        print(f"Found namespace: {ns.meta.name} (UUID: {ns.uuid})")
except Exception as e:
    print(f"An error occurred: {e}")

```

## For AI Agent Integration

This SDK was built with AI agents in mind. For detailed instructions on how agents should interact with the SDK, including core principles, usage patterns, and tool definitions, please see the **[AI Agent Guide](./AGENTS.md)**.

## Contributing

We welcome contributions! Please ensure your code adheres to our quality standards by running the linters before submitting a pull request.

- **Check formatting with Black:**
  ```bash
  uv run black --check .
  ```
- **Check for linting issues with Ruff:**
  ```bash
  uv run ruff check .
