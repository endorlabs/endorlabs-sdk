# Endor Cockpit

[![Python CI](https://github.com/<your-org>/<your-repo>/actions/workflows/ci.yml/badge.svg)](https://github.com/<your-org>/<your-repo>/actions/workflows/ci.yml)

A production-ready Python SDK for integrating Endor Labs security platform with AI-powered IDEs and development tools. Provides comprehensive REST API client capabilities for administering, operating, and scanning with Endor Labs tooling.

## 🚀 Agentic Usage (Quick Start)

**For AI Agents in IDEs**: This toolkit is designed to be seamlessly integrated into AI-powered development environments. See [AGENTS.md](./AGENTS.md) for comprehensive integration guidance.

```python
from endor_cockpit.api_client import APIClient
from endor_cockpit.resources import namespace

# Initialize client (auto-authenticates via environment variables)
client = APIClient()

# List namespaces
namespaces = namespace.list_namespaces(client, "tenant.namespace")
for ns in namespaces:
    print(f"Namespace: {ns.meta.name}")
```

## Features

- **IDE Integration Ready**: Designed for seamless integration with AI-powered development environments
- **Comprehensive API Coverage**: Full REST API client for Endor Labs platform administration and operations
- **Security-First Design**: Built-in security scanning capabilities with `endorctl` integration
- **Modern Python Tooling**: Uses `uv` for dependency management, `ruff` for linting, and `pytest` for testing
- **Type-Safe Operations**: Leverages Pydantic for clear, validated API data structures and operations
- **Resource-Oriented Architecture**: Intuitive structure with modules dedicated to specific API resources
- **Production-Ready**: Robust error handling, authentication, rate limiting, and retry mechanisms

## Installation

It is recommended to use a virtual environment - this project is designed with `uv` and `poetry` in mind.

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

# Optional: Install dependencies for documentation sync scripts
uv pip install -e ".[docs]"
```

## Environment Setup

### Required Environment Variables

The SDK requires the following environment variables to be set:

```bash
export ENDOR_API="https://api.endorlabs.com"
export ENDOR_API_CREDENTIALS_KEY="your-api-key"
export ENDOR_API_CREDENTIALS_SECRET="your-api-secret"
export ENDOR_NAMESPACE="your-tenant-namespace"  # Required for operations
```

### Local Development Setup

For local development, you can use the admin setup script:

```bash
# Initialize environment (creates .env file from template)
uv run python scripts/admin_setup.py init

# Validate environment configuration
uv run python scripts/admin_setup.py validate

# Quick health check
uv run python scripts/admin_setup.py check
```

### Configuration Management

**Local Development**: Use `.env` file or environment variables directly.

**CI/CD**: Environment variables are configured in GitHub repository settings:
- `ENDOR_API` - Repository variable
- `ENDOR_NAMESPACE` - Repository variable  
- `ENDOR_API_CREDENTIALS_KEY` - Repository secret
- `ENDOR_API_CREDENTIALS_SECRET` - Repository secret

The SDK reads configuration from environment variables only - no hardcoded values or configuration files. This follows 12-factor app principles and ensures security and flexibility across different environments.

## Quick Start

### For Human Developers

```python
from endor_cockpit.api_client import APIClient
from endor_cockpit.resources import namespace

# Initialize the client (uses environment variables for auth)
client = APIClient()

# List namespaces
tenant_namespace = "your-tenant-namespace"
all_namespaces = namespace.list_namespaces(client, tenant_namespace)

for ns in all_namespaces:
    print(f"Namespace: {ns.meta.name}, UUID: {ns.uuid}")
```

### For AI Agents in IDEs

This toolkit is specifically designed for integration with AI-powered development environments. See [AGENTS.md](./AGENTS.md) for comprehensive guidance on:

- **Agent Roles**: Developer, Security, and Operations agent definitions
- **Tool Integration**: LLM tool schemas and function definitions
- **Security Protocols**: Built-in security scanning and compliance
- **Best Practices**: Patterns for reliable agent operations

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

## Resource Implementation Status

> **Comprehensive tracking of Endor Labs resource types and their implementation status**

### Implementation Checklist

#### ✅ **COMPLETED RESOURCES**
- **Project** - Implementation: ✅ | Documentation: ✅ | Tests: ✅
- **Finding** - Implementation: ✅ | Documentation: ✅ | Tests: ✅
- **Policy** - Implementation: ✅ | Documentation: ✅ | Tests: ✅
- **Namespace** - Implementation: ✅ | Documentation: ✅ | Tests: ✅

#### 🔄 **SCAFFOLDED RESOURCES**
- **Repository** - Implementation: 🔄 | Documentation: 🔄 | Tests: ❌
- **RepositoryVersion** - Implementation: 🔄 | Documentation: 🔄 | Tests: ❌
- **PackageVersion** - Implementation: 🔄 | Documentation: 🔄 | Tests: ❌

#### ❌ **PENDING RESOURCES**
- **DependencyMetadata** - Implementation: ❌ | Documentation: ❌ | Tests: ❌
- **LinterResult** - Implementation: ❌ | Documentation: ❌ | Tests: ❌
- **Metric** - Implementation: ❌ | Documentation: ❌ | Tests: ❌
- **Scan** - Implementation: ❌ | Documentation: ❌ | Tests: ❌
- **User** - Implementation: ❌ | Documentation: ❌ | Tests: ❌
- **Token** - Implementation: ❌ | Documentation: ❌ | Tests: ❌
- **Installation** - Implementation: ❌ | Documentation: ❌ | Tests: ❌

### Completion Criteria

**Implementation**: CRUD operations validated, model validated and a handful of attributes modeled correctly
**Documentation**: Statements verified to match implementation and tests  
**Tests**: Passes linter, unit tests provided and incorporated into CI

### Status Legend
- ✅ **COMPLETE**: All criteria met
- 🚧 **IN PROGRESS**: Implementation started
- ❌ **NOT STARTED**: No work begun
- 🚫 **BLOCKED**: Blocked by dependencies

---

## Documentation

- **[AI Agent Integration Guide](./AGENTS.md)** - Primary reference for AI agent integration
- **[Rules of Engagement](./docs/rules-of-engagement/)** - Specialized tactical workflows
- **[Rego Policy Guide](./docs/rego_guide.md)** - Complete Rego policy development reference
- **[SDK Docstrings](./src/endor_cockpit/)** - Inline documentation for all resources
- **[External Documentation](./external_docs/)** - Endor Labs API and user documentation

## Workspace Folder

For local testing and development, use the `.workspace/` folder which is excluded from version control. This folder is **unique to each user** and contains:
- Integration test results and configurations
- Temporary policy configurations
- Development scripts and utilities
- Test-specific documentation
- User-specific API configurations
- **Operational context and environment setup guides**

Each user's workspace is isolated and not shared across the team.

For current operational context including environment setup, GitHub CLI configuration, and development workflow, see `.workspace/OPERATIONAL_CONTEXT.md`.

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
