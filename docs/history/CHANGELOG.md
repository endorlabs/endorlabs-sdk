# Changelog

> **Endor Cockpit project evolution and breaking changes**

## [Unreleased]

### Added
- Enhanced AGENTS.md with persona routing and documentation style guide
- Created docs/SPECIFICATION.md for API discrepancies and corrections
- Migrated developer persona documentation from existing agent docs
- Scaffolded operations and security persona documentation
- Implemented vector DB system with semantic chunking
- Created knowledge base structure for RAG-compatible content
- Added changelog and API evolution tracking system

### Changed
- Restructured documentation from monolithic to persona-based approach
- Migrated content from docs/agents/ to persona-specific locations
- Enhanced AGENTS.md as universal anchor for all personas

### Fixed
- Documented canonical naming requirements for namespace operations
- Added missing API parameter requirements (parent_namespace)
- Corrected Pydantic model definitions for empty descriptions

---

## [0.1.0] - 2025-10-18

### Added
- Initial Endor Cockpit SDK implementation
- Core API client with retry, rate limiting, and logging
- Namespace resource operations
- Pydantic data models for type safety
- Security scanning integration with endorctl
- Comprehensive test suite with integration tests
- CI/CD pipeline with multi-version Python testing
- Documentation structure for AI agents

### Features
- **Comprehensive API Coverage**: Full REST API client for Endor Labs platform
- **Security-First Design**: Built-in security scanning capabilities
- **Modern Python Tooling**: Uses uv for dependency management, ruff for linting
- **Type-Safe Operations**: Leverages Pydantic for validated API operations
- **Resource-Oriented Architecture**: Intuitive structure with dedicated modules
- **Agent-Optimized**: Comprehensive documentation for AI agent integration
- **Production-Ready**: Robust error handling, authentication, rate limiting

### Technical Details
- **Python Support**: 3.11-3.14 (exclusive)
- **Dependencies**: requests==2.32.5, pydantic==2.12.3
- **Development Tools**: pytest==8.4.2, ruff==0.14.1, pytest-cov==6.0.0
- **Security**: endorctl integration for security scanning

---

## [0.0.1] - 2025-10-17

### Added
- Initial project setup
- Basic project structure
- Core dependencies
- Initial documentation

---

## Breaking Changes

### [0.1.0] - 2025-10-18
- **Namespace Operations**: All namespace operations now require `parent_namespace` parameter
- **Canonical Naming**: Parent namespaces must use canonical naming format (not UUIDs)
- **Pydantic Models**: Updated model definitions to allow empty descriptions

### Migration Guide
```python
# Before (0.0.1)
namespace = namespaces.get_namespace(client, namespace_uuid)

# After (0.1.0)
namespace = namespaces.get_namespace(client, parent_namespace, namespace_uuid)
```

---

## Security Updates

### [0.1.0] - 2025-10-18
- **Security Scanning**: Integrated endorctl for comprehensive security scanning
- **Input Validation**: Enhanced input validation and sanitization
- **Error Handling**: Improved error handling to prevent information leakage
- **Authentication**: Secure credential management via environment variables

---

## Performance Improvements

### [0.1.0] - 2025-10-18
- **Rate Limiting**: Implemented intelligent rate limiting with exponential backoff
- **Connection Pooling**: Added HTTP connection pooling for better performance
- **Caching**: Implemented response caching for frequently accessed data
- **Parallel Processing**: Added support for parallel API operations

---

## Documentation Updates

### [0.1.0] - 2025-10-18
- **Persona-Based Documentation**: Restructured documentation for different user personas
- **API Corrections**: Documented known discrepancies between OpenAPI spec and actual API
- **Vector Database**: Implemented semantic search capabilities
- **Knowledge Base**: Created comprehensive knowledge base for RAG systems

---

## Contributors

- **Initial Implementation**: [Contributor Name]
- **Documentation**: [Contributor Name]
- **Testing**: [Contributor Name]
- **Security**: [Contributor Name]

---

## License

This project is licensed under the MIT License - see the [LICENSE](../LICENSE) file for details.

---

*This changelog tracks the evolution of the Endor Cockpit project and provides migration guidance for breaking changes.*
