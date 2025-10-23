# Essential Context for Endor Cockpit Agents

> **Process-oriented operational protocols - must-read before any agent operation**

## 🚨 Operational Protocols

**These 8 protocols are mandatory for all agent operations:**

1. **Query First**: `uv run python -m holocron query "your question"` before coding
2. **Validate Environment**: `python scripts/validate_environment.py` before starting
3. **Security Scan**: `endorctl scan` required before commits
4. **Knowledge Capture**: Log discoveries in `.workspace/logbook.md`, follow promotion protocol
5. **Documentation Sync**: `uv run python -m holocron sync` after doc updates
6. **Check Docstrings**: Read function/class docstrings for API details
7. **Test Pattern**: Follow `test_<resource>.py` convention
8. **Error Recovery**: Check `.workspace/validation.log` for actionable errors

## 🔍 When You Don't Know Something

**Route to the right information source:**

- **Terminology/concepts?** → Query holocron first
- **Process/workflow?** → Check `docs/protocols/`
- **API details?** → Read docstrings, check `.workspace/downloads/openapi-swagger.json`
- **Resource structure?** → Query holocron for resource-specific docs

## 🎯 Rationale

Essential context focuses on **how to operate** (process), not **what things are** (content). Query-first workflow retrieves content on-demand, which then stays in context window when flagged as important.

## 📚 Quick Reference Links

- **Agent Guide**: `docs/agents/README.md`
- **Protocols**: `docs/protocols/`
- **Resource Docs**: `docs/endor-data-model/`
- **Workspace**: `.workspace/README.md`
- **Validation**: `scripts/validate_environment.py`

---

*This file is the single source of truth for essential operational context. All other documentation should reference this file for core protocols.*
