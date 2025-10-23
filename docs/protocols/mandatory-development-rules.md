# Mandatory Development Rules

> **L1 (Essential - Always Required) - Core operational requirements for all development operations**

## Quick Reference

### Environment Requirements
- [ ] Set `ENDOR_API`, `ENDOR_API_CREDENTIALS_KEY`, `ENDOR_API_CREDENTIALS_SECRET`
- [ ] Python >=3.12, <3.16
- [ ] Run `python scripts/validate_environment.py` before operations
- [ ] Initialize RAG with `uv run python -m holocron sync`

### Code Standards
- [ ] Line length ≤88 characters
- [ ] Imports sorted and unused removed
- [ ] No trailing whitespace or blank line whitespace
- [ ] F-strings only with placeholders
- [ ] Dependencies pinned (no `latest` or `>=`)
- [ ] PEP8 compliance
- [ ] Return `Optional[Resource]` for consistency
- [ ] Use canonical naming (tenant.namespace format, never UUIDs in paths)

### API Validation Requirements (CRITICAL)
- [ ] **MANDATORY**: Complete API validation before any resource implementation
- [ ] Extract complete schema from OpenAPI specification
- [ ] Test with live API data using endorctl and direct API calls
- [ ] Create validation matrix mapping OpenAPI spec to live data
- [ ] Validate all field types, required fields, and nested objects
- [ ] Test all available CRUD operations before implementation
- [ ] Document any API discrepancies or quirks found
- [ ] Verify operation availability by checking OpenAPI spec and testing endpoints

### Security Requirements
- [ ] Run `endorctl scan` before any commits
- [ ] No hardcoded secrets (use environment variables)
- [ ] Secure logging filters (no PII or sensitive data)
- [ ] Input validation on all user inputs

### Testing Requirements
- [ ] Write CRUD tests for all resource operations
- [ ] Integration tests required for API interactions
- [ ] Use pytest markers (slow/integration)
- [ ] Test coverage for new functionality

### Knowledge Capture Requirements
- [ ] Create logbook entries during troubleshooting (link to knowledge-capture-workflow.md)
- [ ] Query holocron first before implementing features
- [ ] Document all API quirks and learnings
- [ ] Follow conventional commit format (feat/fix/docs/test)

### Quick-Access Commands
```bash
# Linting
uv run ruff check .              # Check all issues
uv run ruff check . --fix        # Auto-fix issues  
uv run ruff format .             # Format code

# Testing  
uv run pytest                    # Run all tests
uv run pytest --cov=endor_cockpit  # With coverage
uv run pytest -m "not slow"      # Skip slow tests

# Security
endorctl scan                    # Security scan
endorctl scan --dependencies    # Dependency scan
endorctl scan --sast            # SAST scan

# Development
python scripts/validate_environment.py  # Validate environment
uv run python -m holocron query "..."    # RAG query
uv run python -m holocron sync          # Rebuild vector DB

# Environment Setup
export ENDOR_API="https://api.endorlabs.com"
export ENDOR_API_CREDENTIALS_KEY="your-key"
export ENDOR_API_CREDENTIALS_SECRET="your-secret"
```

## Protocol Architecture

### Root Protocols (L1)
- [Code Commit Protocol](development/code-commit-protocol.md) - Pre-commit workflow and requirements
- [Development Protocol](development/development-protocol.md) - Feature implementation workflow
- [Troubleshooting Protocol](development/troubleshooting-protocol.md) - Issue resolution workflow

### Nested Protocols (L2)
- [Resource Implementation Protocol](development/resource-implementation-protocol.md) - When implementing new resources
- [Testing Protocol](development/testing-protocol.md) - When writing tests

## Repository Structure
```
endor-cockpit/
├── src/
│   ├── endor_cockpit/         # SDK implementation
│   │   ├── api_client.py      # Core API client
│   │   ├── resources/         # Resource modules (CRUD)
│   │   ├── models/            # Pydantic models
│   │   └── utils/             # Utilities
│   └── holocron/              # RAG knowledge base
├── docs/
│   ├── protocols/             # L1 mandatory protocols
│   ├── personas/              # Persona-specific guides  
│   ├── endor-data-model/      # Resource documentation
│   └── agents/                # Agent guides
├── tests/                     # Test suite
├── .workspace/                # Local workspace (gitignored)
└── holocron_data/             # Vector database (gitignored)
```

## Success Criteria
- ✅ All tests passing
- ✅ No linting errors
- ✅ Security scan clean
- ✅ Resource operations working
- ✅ Error handling graceful
- ✅ Documentation updated
- ✅ Knowledge base synced

---

*These rules are mandatory for all development operations. Reference this document in all development contexts.*
