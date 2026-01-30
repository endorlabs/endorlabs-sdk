# Scripts

Contributor setup: [CONTRIBUTORS.md](../CONTRIBUTORS.md).

## sync_external_docs.py

One workflow creates the gitignored `external_docs/` folder with both the OpenAPI spec and user documentation. **Recommended for advanced users** to pull full platform-admin context into the IDE.

### Recommended: sync spec + user docs (full IDE context)

```bash
uv sync --extra docs
uv run python scripts/sync_external_docs.py --all
```

This creates:

- `external_docs/openapi-swagger.json` — API spec (public URL; no credentials needed)
- `external_docs/user-docs/*.md` — User docs from [docs.endorlabs.com](https://docs.endorlabs.com/) (parallel download; worker count from local CPU heuristic)

### Other options

```bash
# OpenAPI spec only (no docs extra needed)
uv run python scripts/sync_external_docs.py --download-openapi

# User docs only, limit pages
uv run python scripts/sync_external_docs.py --download-user-docs --max-pages 50

# Force re-download
uv run python scripts/sync_external_docs.py --all --force
```

See also: [docs/rules-of-engagement/docs-drift-workflow.md](../docs/rules-of-engagement/docs-drift-workflow.md).
