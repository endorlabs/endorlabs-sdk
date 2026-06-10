# Devtools

Contributor setup: [CONTRIBUTORS.md](../CONTRIBUTORS.md).

For syncing external documentation (OpenAPI spec, user docs), use the programmatic API:

```python
import endorlabs
endorlabs.init(sync_skills="cursor")  # or "claude"/"both" as needed
```

See [AGENTS.md](../AGENTS.md#bootstrap) for agent bootstrap details.

For canonical model-sync internals and maintenance responsibilities, see
[`devtools/sync/README.md`](sync/README.md).
