# TestPyPI readiness assessment (2026-06-06)

> Generated after executing the TestPyPI readiness plan. See [pypi-publication-draft.md](pypi-publication-draft.md) for ongoing maintainer checklist.

## 1. Verdict

**Ready with manual steps only** — release `v0.1.0` is built and on GitHub; TestPyPI upload requires a maintainer API token (not stored in repo).

## 2. Blockers (resolved)

| Blocker | Status | Fix |
|---------|--------|-----|
| CI unit tests failing on `agent/skills` paths | Fixed | [PR #85](https://github.com/endorlabs/endorlabs-sdk/pull/85) — `test_sast_rule_manager.py`, `test_sso_access_spotcheck.py` |
| Changelog only under Unreleased | Fixed | `docs/changelog.md` → `## 0.1.0` |
| Stale `agent/skills` doc links | Fixed | contributing docs, cursor rule, `validate.py` |
| Reference doc drift blocked release | Fixed | `bf5a1948` — regen before retagging `v0.1.0` |

## 3. Pre-upload checklist

- [x] Merge readiness fixes to `main`
- [x] CI green (PR #85)
- [x] Changelog `## 0.1.0`
- [x] Tag `v0.1.0` on `main` (`bf5a1948`)
- [x] Release Tag Publish workflow succeeded
- [x] GitHub Release artifacts: [v0.1.0](https://github.com/endorlabs/endorlabs-sdk/releases/tag/v0.1.0)
- [x] Local wheel smoke test (`import endorlabs`, `agent_knowledge_manifest()`)
- [x] Unit tests: 968 passed; integration: 113 passed (local, `-m "not long"`)
- [x] `[[tool.uv.index]]` for TestPyPI in `pyproject.toml`
- [ ] **TestPyPI upload** (maintainer token required)
- [ ] **TestPyPI smoke install** (after upload)

## 4. Manual TestPyPI steps

### Credentials

Create a token at [test.pypi.org](https://test.pypi.org/manage/account/token/) (scope: entire account or project `endorlabs-sdk`).

Set for the publish session (do not commit):

```powershell
$env:UV_PUBLISH_USERNAME = "__token__"
$env:UV_PUBLISH_PASSWORD = "<testpypi-api-token>"
```

Or add `TEST_PYPI_API_TOKEN` to local `.env` and export before publish.

### Publish

From repo root, using release artifacts:

```powershell
gh release download v0.1.0 -D dist --pattern "endorlabs_sdk-0.1.0*" --clobber
uv publish --index testpypi dist/endorlabs_sdk-0.1.0*
```

### Smoke install

```powershell
uv venv .tmp/testpypi-smoke --python 3.12 --clear
uv pip install --python .tmp/testpypi-smoke/Scripts/python.exe `
  --index-url https://test.pypi.org/simple/ `
  --extra-index-url https://pypi.org/simple/ `
  "endorlabs-sdk[context]==0.1.0"
.tmp/testpypi-smoke/Scripts/python.exe -c "import endorlabs; print(endorlabs.__version__); print(len(endorlabs.agent_knowledge_manifest()['skills']))"
```

Expected: version `0.1.0`, 16 skills.

## 5. Automation gaps

From [pypi-publication-draft.md](pypi-publication-draft.md) — not yet implemented:

- [ ] TestPyPI publish job in `release-tag-publish.yml` (manual `workflow_dispatch` or trusted publishing)
- [ ] Production PyPI publish (OIDC trusted publishing)
- [ ] `devtools/check_vcs_version.py` in CI PR Main
- [ ] Document whether TestPyPI gets dev builds vs release tags only

## 6. Corrections applied

| File | Change |
|------|--------|
| `tests/unit/tooling/scripts/test_sast_rule_manager.py` | Fallback paths: `agent-knowledge/skills/`, shipped `agent_knowledge/skills/` |
| `tests/unit/tooling/scripts/test_sso_access_spotcheck.py` | Same path pattern |
| `docs/changelog.md` | Versioned `0.1.0` section |
| `docs/contributing/README.md` | Links → `agent-knowledge/skills/` |
| `docs/contributing/integration-resource-tests.md` | Link fix |
| `.cursor/rules/docs-skillbase-consistency.mdc` | Path preference update |
| `src/endorlabs/workflows/policies/validate.py` | Docstring path fix |
| `docs/generated-reference/*` | Regenerated for release gate |
| `pyproject.toml` | `[[tool.uv.index]]` name `testpypi` |

## 7. Suggested release tag

**`v0.1.0`** — first public pre-release on TestPyPI. Tag points at `bf5a1948` on `main`.

Dev-series anchor remains `v0.1.1.dev0` for local/editable builds (`0.1.1.devN` between anchors).

## Local verification snapshot

| Check | Result |
|-------|--------|
| `check_vcs_version.py` | `0.1.1.dev67` (valid PEP 440) |
| `uv build` with `SETUPTOOLS_SCM_PRETEND_VERSION=0.1.0` | Pass |
| Wheel contains `agent_knowledge/`, entry points | Pass |
| TestPyPI package exists | No (404 as of assessment date) |

## Non-blocking notes

- Wheel build may log duplicate `agent_knowledge/` zip entries (packaging warnings only).
- Release workflow uses `softprops/action-gh-release` on Node 20 (deprecation notice in CI).
