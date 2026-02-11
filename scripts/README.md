# Scripts

Contributor setup: [CONTRIBUTORS.md](../CONTRIBUTORS.md).

For syncing external documentation (OpenAPI spec, user docs), use the programmatic API:

```python
import endorlabs
endorlabs.init()  # downloads to .endorlabs-context/
```

See [AGENTS.md](../AGENTS.md#context-bootstrap-for-ai-agents) for details.

## export_current_af_models.py

One-off script for the OSS model generation experiment (e.g. `G:/temp/endor-oss-model-experiment`). Exports current SDK model field paths to JSON for comparison with generated models.

```bash
uv run python scripts/export_current_af_models.py -o /path/to/current_af_models.json
# Or print to stdout:
uv run python scripts/export_current_af_models.py
```
