# Code Commit Protocol

> **L1 (Essential - Always Required) - Pre-commit workflow and requirements**

## Overview

This protocol ensures all code changes meet quality, security, and documentation standards before being committed to the repository.

## Pre-Commit Checklist

### Code Quality
- [ ] Run `uv run ruff check .` - No linting errors
- [ ] Run `uv run ruff check . --fix` - Auto-fix issues
- [ ] Run `uv run ruff format .` - Code formatting
- [ ] Line length ≤88 characters
- [ ] Imports sorted and unused removed
- [ ] No trailing whitespace

### Testing
- [ ] Run `uv run pytest` - All tests passing
- [ ] Run `uv run pytest --cov=endor_cockpit` - Coverage acceptable
- [ ] CRUD tests written for new resources
- [ ] Integration tests for API interactions

### Security
- [ ] Run `endorctl scan` - Security scan passes
- [ ] No hardcoded secrets in code
- [ ] Secure logging filters in place
- [ ] Input validation implemented

### Documentation
- [ ] Function docstrings with Args/Returns/Raises
- [ ] Resource documentation updated (if applicable)
- [ ] API quirks documented in logbook
- [ ] Knowledge base synced with `uv run python -m holocron sync`

### Knowledge Capture
- [ ] Logbook entries created for troubleshooting sessions
- [ ] API discoveries documented
- [ ] Schema drift logged
- [ ] Follow [Knowledge Capture Workflow](../knowledge-capture-workflow.md)

## Commit Process

### 1. Pre-Commit Validation
```bash
# Run full validation suite
uv run ruff check . --fix
uv run ruff format .
uv run pytest
endorctl scan
uv run python -m holocron sync
```

### 2. Commit Message Format
Use conventional commits:
- `feat(resource): add new functionality`
- `fix(api): resolve authentication issue`
- `docs(readme): update installation guide`
- `test(integration): add CRUD tests`

### 3. Push Requirements
- [ ] All pre-commit checks pass
- [ ] Commit message follows convention
- [ ] No sensitive data in commit
- [ ] Documentation updated

## Success Criteria

- ✅ All linting checks pass
- ✅ All tests pass
- ✅ Security scan clean
- ✅ Documentation current
- ✅ Knowledge base synced
- ✅ Conventional commit format

## Related Protocols

- [Development Protocol](development-protocol.md) - For feature implementation
- [Troubleshooting Protocol](troubleshooting-protocol.md) - For issue resolution
- [Knowledge Capture Workflow](../knowledge-capture-workflow.md) - For learning documentation

---

*This protocol must be followed before any code commit to maintain quality and security standards.*
