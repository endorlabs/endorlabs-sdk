# Scripts

Contributor setup: [CONTRIBUTORS.md](../CONTRIBUTORS.md).

For syncing external documentation (OpenAPI spec, user docs), use the programmatic API:

```python
import endorlabs
endorlabs.init()  # downloads to .endorlabs-context/
```

See [AGENTS.md](../AGENTS.md#context-bootstrap-for-ai-agents) for details.


For canonical model-sync internals and maintenance responsibilities, see
[`scripts/sync/README.md`](sync/README.md).
