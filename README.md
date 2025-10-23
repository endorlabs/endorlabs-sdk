# Endor Cockpit

[![Python CI](https://github.com/<your-org>/<your-repo>/actions/workflows/ci.yml/badge.svg)](https://github.com/<your-org>/<your-repo>/actions/workflows/ci.yml)

A foundational workspace to administer, operate and scan with Endor Labs tooling through REST APIs. Designed for both human developers and AI agents working with Endor Labs security platform.

## META: Documentation Guidelines

**Before adding files, check for presence of related files for suitability first.**

- **Related files**: Search for existing files with similar content using `glob_file_search` or `grep`
- **Suitability check**: Verify if existing files are more appropriate for the content
- **Consolidation**: Prefer updating existing files over creating new ones
- **Examples**: 
  - Chunking strategy → `docs/agents/rag_usage.md` (RAG-specific)
  - API patterns → `docs/agents/api-patterns.md` (agent-focused)
  - Development setup → `docs/agents/development.md` (development-focused)

## Features

- **Comprehensive API Coverage**: Full REST API client for Endor Labs platform administration and operations
- **Security-First Design**: Built-in security scanning capabilities with `endorctl` integration
- **Modern Python Tooling**: Uses `uv` for dependency management, `ruff` for linting, and `pytest` for testing
- **Type-Safe Operations**: Leverages Pydantic for clear, validated API data structures and operations
- **Resource-Oriented Architecture**: Intuitive structure with modules dedicated to specific API resources
- **Agent-Optimized**: Comprehensive documentation and patterns specifically designed for AI agent integration
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

# Install RAG dependencies for knowledge base
uv pip install -e ".[holocron]"
```

## First Time Setup

### Knowledge Base Initialization

**IMPORTANT**: The Holocron knowledge base is the **first step** for any AI agent working with this repository. It contains comprehensive documentation, API patterns, and best practices that should be consulted before making any changes.

#### Quick Start
```bash
# Install RAG functionality for semantic search
uv pip install -e ".[holocron]"

# Set required environment variables
export OPENAI_API_KEY="your-openai-api-key"

# Initialize the knowledge base
uv run python -m holocron init

# Query the knowledge base
uv run python -m holocron query "How do I create a namespace?"
```

#### Knowledge Base Workflow

1. **Query First**: Always check the knowledge base before operations
2. **Verify**: Cross-reference with existing documentation
3. **Act**: Make changes based on established patterns
4. **Update**: Incorporate new learnings when contradictions are found

**Complete Guide**: See [docs/holocron/README.md](docs/holocron/README.md) for comprehensive Holocron documentation, including configuration, architecture, and troubleshooting.

**Setup Workflows**: See [docs/protocols/holocron-setup.md](docs/protocols/holocron-setup.md) for detailed initialization procedures.

The knowledge base is a **portable shared learning index** that ensures consistency across all AI agents and maintains the freshness of operational knowledge.

## Quick Start

### For Human Developers

```python
from endor_cockpit.api_client import APIClient
from endor_cockpit.resources import namespace

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

- **[AI Agent Integration Guide](./AGENTS.md)** - Comprehensive guide for AI agents
- **[Agent Documentation](./docs/agents/)** - Detailed agent-specific documentation
- **[API Reference](./docs/)** - Complete API documentation
- **[Examples](./docs/examples/)** - Usage examples and patterns

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
