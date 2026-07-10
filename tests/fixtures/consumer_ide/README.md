# Consumer IDE typing fixture

Minimal script that mimics a downstream project importing `endorlabs` and using
`Client` facades. Use it to validate Pyright/Pylance hovers after stub changes.

## Local Pyright check (SDK repo)

```powershell
uv run pyright tests/fixtures/consumer_ide/main.py --project pyproject.toml
```

Expected: no errors on `c.Project.list`, `search_by_name`, `get_logs`, or
`list_by_project`.

## Expected IDE hovers (editable install)

| Symbol | Expected |
|--------|----------|
| `endorlabs.Client` | Class doc with tenant/transport guidance |
| `Client(...)` | `__init__` params + docstring from stub |
| `c.Project` | `_ProjectFacade` extending `ProjectFacade` |
| `c.Project.list` | Full list kwargs + doc excerpt |
| `c.Project.search_by_name` | Typed signature + doc from `specialized.py` |
| `c.ScanResult.get_logs` | Typed signature + doc from `specialized.py` |

Go to Definition on `Client` opens `client_surface.py`; types come from
`client_surface.pyi`.

## Manual checklist: opengrep-experiments

1. In `../opengrep-experiments/pyproject.toml`, add temporarily:

   ```toml
   [tool.uv.sources]
   endorlabs = { path = "../endorlabs-sdk", editable = true }
   ```

2. `uv sync` and select the project `.venv` interpreter in Cursor/VS Code.

3. Repeat hover checks above in a script that uses `endorlabs.Client`.

4. Optional wheel path: `uv build` in this repo, install wheel in a clean venv,
   repeat hover checks to confirm PyPI consumer packaging.

## Validation results (2026-06-16)

After stub generator changes in this repo:

| Check | Result |
|-------|--------|
| `uv run pyright tests/fixtures/consumer_ide/main.py --project pyproject.toml` | **0 errors** |
| Committed stub | `_ProjectFacade(ProjectFacade)`, explicit `list()`, `Client.__init__` docstring, no orphan attr docstrings, no untyped `list_by_project(*args)` on `_FindingFacade` |
| `uv run python devtools/ship/smoke_test_wheel.py` | **pass** — `py.typed` and `client_surface.pyi` present in installed wheel |
| `from endorlabs import ListParameters` | Exported from `endorlabs.__init__` (SDK repo) |

**opengrep-experiments note:** `uv run` in that project re-syncs `endorlabs>=0.4.0` from PyPI unless you add `[tool.uv.sources]` with an editable path. Use `uv pip install -e ../endorlabs-sdk` and run scripts with `.venv\Scripts\python.exe` directly (not `uv run`) for a quick hover check, or add the path source and `uv sync` for a durable setup.
