# Consumer agent discovery fixture

Simulates a Cursor/runtime agent without LSP: **Read** wheel files and grep stub
sections — do not rely on Pyright inheritance from `ProjectFacade`.

## Checks

```powershell
uv run pytest tests/fixtures/consumer_agent/test_agent_bootstrap_discovery.py -q
uv run python -m endorlabs.examples.agent_bootstrap --dry-run
```

## Expected agent Read surface

| File | Must contain |
|------|----------------|
| `discover().stub` | `def search_by_name(` inside `class _ProjectFacade` |
| `discover().bootstrap_paths` | `resource-discovery.md` |
| `discover().agents_guide` | First steps before `Client()` |
