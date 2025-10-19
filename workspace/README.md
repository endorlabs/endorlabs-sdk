# Workspace Directory

This directory is **user-specific and git-ignored**. It contains files that are unique to each developer or AI agent working with the repository.

## Purpose

The workspace directory serves as a personal workspace for:
- Integration test results and configurations
- Temporary policy configurations
- Development scripts and utilities
- Test-specific documentation
- User-specific API configurations
- **Agent notes and task documentation**
- Vector database files (when initialized)

## Important Security Note

**NEVER commit credentials or sensitive information to this directory.** This directory is git-ignored, but always be cautious with sensitive data.

## Vector Database Location

When initialized, the vector database files are stored in:
- `workflow/vector_db/` - ChromaDB database files
- `workflow/vector_db_manifest.json` - Manifest tracking file hashes

These files are git-ignored to keep the repository clean while allowing each user to have their own knowledge base.

## Task Tracking for AI Agents

For long-living tasks or complex workflows, create markdown checklist files:

### File Naming
- `tasks-<description>.md` - Specific task tracking
- `current-tasks.md` - Current active tasks
- `archive/` - Completed task files

### Format
```markdown
# Task: [Description]
Started: YYYY-MM-DD
Last Updated: YYYY-MM-DD

## Objectives
- [ ] Objective 1
- [ ] Objective 2

## Current Status
- [x] Completed step
- [ ] In progress step
- [ ] Pending step

## Notes
- Important context or decisions
```

## Operational Context

Create `OPERATIONAL_CONTEXT.md` to document your specific environment:
- System information (OS, shell, IDE)
- Environment variables and credentials
- GitHub CLI configuration
- Development workflow preferences
- Troubleshooting notes

## Vector Database Initialization

To initialize the vector database for the first time:

1. **Install RAG dependencies:**
   ```bash
   uv pip install -e ".[rag]"
   ```

2. **Set OpenAI API key:**
   ```bash
   export OPENAI_API_KEY="your-openai-api-key"
   ```

3. **Initialize vector database:**
   ```bash
   python workflow/init_vector_db.py
   ```

4. **Query the knowledge base:**
   ```python
   from endor_cockpit.rag import query_vector_db
   results = query_vector_db("How do I create a namespace?")
   ```

## Best Practices

- Keep workspace files organized and documented
- Archive completed tasks to `archive/` subdirectory
- Update task files as work progresses
- Never commit workspace files to version control
- Use the knowledge base as your first source of information
- Update the knowledge base when you discover contradictions

## Troubleshooting

If you encounter issues:
1. Check that RAG dependencies are installed
2. Verify OPENAI_API_KEY is set
3. Ensure the vector database is initialized
4. Query the knowledge base for existing solutions
5. Update the knowledge base with new learnings
