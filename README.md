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

# Install dependencies
pip install -e .

# Or with uv (recommended)
uv pip install -e .
```

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
