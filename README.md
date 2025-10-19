# Endor Cockpit

[![Python CI](https://github.com/<your-org>/<your-repo>/actions/workflows/ci.yml/badge.svg)](https://github.com/<your-org>/<your-repo>/actions/workflows/ci.yml)

A foundational workspace to administer, operate and scan with Endor Labs tooling through REST APIs. Designed for both human developers and AI agents working with Endor Labs security platform.

## Features

- **Comprehensive API Coverage**: Full REST API client for Endor Labs platform administration and operations
- **Security-First Design**: Built-in security scanning capabilities with `endorctl` integration
- **Modern Python Tooling**: Uses `uv` for dependency management, `ruff` for linting, and `pytest` for testing
- **Type-Safe Operations**: Leverages Pydantic for clear, validated API data structures and operations
- **Resource-Oriented Architecture**: Intuitive structure with modules dedicated to specific API resources
- **Agent-Optimized**: Comprehensive documentation and patterns specifically designed for AI agent integration
- **Production-Ready**: Robust error handling, authentication, rate limiting, and retry mechanisms

## Installation

It is recommended to use a virtual environment.

```bash
# Clone the repository
git clone https://github.com/endor-solutions-architecture/endor-cockpit.git
cd endor-cockpit

# Create virtual environment
uv venv
source .venv/bin/activate  # Linux/Mac
# or
.venv\Scripts\activate    # Windows

# Install dependencies
uv pip install -e .

# Install RAG dependencies for knowledge base
uv pip install -e ".[rag]"
```

## First Time Setup

### Knowledge Base Initialization

**IMPORTANT**: The vector database knowledge base is the **first step** for any AI agent working with this repository. It contains comprehensive documentation, API patterns, and best practices that should be consulted before making any changes.

#### 1. Install RAG Dependencies
```bash
# Install RAG functionality for semantic search
uv pip install -e ".[rag]"
```

#### 2. Set Environment Variables
```bash
# Required for API access
export ENDOR_API="https://api.endorlabs.com"
export ENDOR_API_CREDENTIALS_KEY="your-api-key"
export ENDOR_API_CREDENTIALS_SECRET="your-api-secret"

# Required for RAG functionality
export OPENAI_API_KEY="your-openai-api-key"
```

#### 3. Initialize Vector Database
```bash
# Initialize the knowledge base
uv run python workflow/init_vector_db.py

# Rebuild after documentation updates
uv run python workflow/init_vector_db.py --rebuild
```

#### 4. Query the Knowledge Base
```python
from endor_cockpit.rag import query_vector_db

# Always query first before making changes
results = query_vector_db("How do I create a namespace?")
print(f"Found {len(results['results'])} relevant documents")
```

### Knowledge Base Workflow

1. **Query First**: Always check the knowledge base before operations
2. **Verify**: Cross-reference with existing documentation
3. **Act**: Make changes based on established patterns
4. **Update**: Incorporate new learnings when contradictions are found

The knowledge base is a **portable shared learning index** that ensures consistency across all AI agents and maintains the freshness of operational knowledge.

## Quick Start

### For Human Developers

```python
from endor_cockpit.api_client import APIClient
from endor_cockpit.resources import namespaces

# Initialize the client (uses environment variables for auth)
client = APIClient()

# List namespaces
tenant_namespace = "your-tenant-namespace"
all_namespaces = namespaces.list_namespaces(client, tenant_namespace)

for ns in all_namespaces:
    print(f"Namespace: {ns.meta.name}, UUID: {ns.uuid}")
```

### For AI Agents

See the comprehensive [AI Agent Integration Guide](./AGENTS.md) for detailed guidance on:
- Core principles and best practices
- Platform-specific insights and patterns
- Tool definitions for LLM integration
- Security and compliance guidelines

## Environment Setup

Set the following environment variables:

```bash
export ENDOR_API="https://api.endorlabs.com"
export ENDOR_API_CREDENTIALS_KEY="your-api-key"
export ENDOR_API_CREDENTIALS_SECRET="your-api-secret"
```

Or use the provided setup scripts:
- **Windows**: `setup_env.ps1` or `setup_env.bat`
- **Linux/macOS**: `setup_env.sh`

## Development

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=endor_cockpit --cov-report=html

# Run integration tests (requires valid credentials)
pytest tests/test_integration.py -v
```

### Code Quality

```bash
# Linting & Formatting
ruff check .

# Type checking
mypy src/
```

### Security Scanning

```bash
# Run endorctl security scan
endorctl scan --path . --namespace "your-namespace"
```

## Documentation

- **[AI Agent Integration Guide](./AGENTS.md)** - Comprehensive guide for AI agents
- **[Agent Documentation](./docs/agents/)** - Detailed agent-specific documentation
- **[API Reference](./docs/)** - Complete API documentation
- **[Examples](./docs/examples/)** - Usage examples and patterns

## Workspace Folder

For local testing and development, use the `workspace/` folder which is excluded from version control. This folder is **unique to each user** and contains:
- Integration test results and configurations
- Temporary policy configurations
- Development scripts and utilities
- Test-specific documentation
- User-specific API configurations
- **Operational context and environment setup guides**

Each user's workspace is isolated and not shared across the team.

For current operational context including environment setup, GitHub CLI configuration, and development workflow, see `workspace/OPERATIONAL_CONTEXT.md`.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests and linting
5. Submit a pull request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

For questions and support:
- **Documentation**: See the [AI Agent Integration Guide](./AGENTS.md)
- **Issues**: Create an issue in the repository
- **Security**: Follow the security guidelines in the documentation
