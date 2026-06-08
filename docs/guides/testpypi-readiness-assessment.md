# TestPyPI readiness assessment (2026-06-06)

> Generated after executing the TestPyPI readiness plan. See [pypi-publication-draft.md](pypi-publication-draft.md) for ongoing maintainer checklist.

## 1. Verdict

**Ready for first publish under `endorlabs`** — PyPI distribution renamed from `endorlabs-sdk` to `endorlabs` (import unchanged: `import endorlabs`). Stale GitHub Releases removed; re-tag when ready.

## 2. Blockers (resolved)

| Blocker | Status | Fix |
|---------|--------|-----|
| CI unit tests failing on `agent/skills` paths | Fixed | [PR #85](https://github.com/endorlabs/endorlabs-sdk/pull/85) — `test_sast_rule_manager.py`, `test_sso_access_spotcheck.py` |
| Changelog only under Unreleased | Fixed | `docs/changelog.md` → `## 0.1.0` |
| Stale `agent/skills` doc links | Fixed | contributing docs, cursor rule, `validate.py` |
| Reference doc drift blocked release | Fixed | `bf5a1948` — regen before retagging |
| PyPI name vs import mismatch | Fixed | `[project].name = "endorlabs"` in `pyproject.toml` |
| Stale GitHub Release (`v0.1.0`, wrong wheel name) | Fixed | Releases deleted; publish fresh after next tag |

## 3. Pre-upload checklist

- [x] Merge readiness fixes to `main`
- [x] CI green (PR #85)
- [x] Changelog `## 0.1.0`
- [x] `[[tool.uv.index]]` for TestPyPI in `pyproject.toml`
- [x] Package rename: `pip install endorlabs` / `endorlabs[docs]`
- [ ] Tag new release (e.g. `v0.1.0` or next patch) on current `main`
- [ ] Release Tag Publish workflow succeeds
- [ ] **TestPyPI upload** (maintainer token or trusted publishing)
- [ ] **TestPyPI smoke install** (after upload)

## 4. Manual TestPyPI steps

### Credentials

Create a token at [test.pypi.org](https://test.pypi.org/manage/account/token/) (scope: entire account or project `endorlabs`).

Set for the publish session (do not commit):

```powershell
$env:UV_PUBLISH_USERNAME = "__token__"
$env:UV_PUBLISH_PASSWORD = "<testpypi-api-token>"
```

### Publish

After **Release Tag Publish** produces artifacts:

```powershell
gh release download <TAG> -D dist --clobber
uv publish --index testpypi dist/endorlabs-<version>*
```

Wheel/sdist filenames use the distribution name `endorlabs` (underscore in wheel: `endorlabs-0.1.0-...`).

### Smoke install

```powershell
uv venv .endorlabs-context/workspace/sessions/agent/scripts/testpypi-smoke --python 3.12 --clear
uv pip install --python .endorlabs-context/workspace/sessions/agent/scripts/testpypi-smoke/Scripts/python.exe `
  --index-url https://test.pypi.org/simple/ `
  --extra-index-url https://pypi.org/simple/ `
  "endorlabs[docs]==<version>"
.endorlabs-context/workspace/sessions/agent/scripts/testpypi-smoke/Scripts/python.exe -c "import endorlabs; print(endorlabs.__version__); print(len(endorlabs.agent_knowledge_manifest()['skills']))"
```

## 5. Automation gaps

From [pypi-publication-draft.md](pypi-publication-draft.md) — not yet implemented:

- [ ] TestPyPI publish job in `release-tag-publish.yml`
- [ ] Production PyPI publish (OIDC trusted publishing)
- [ ] `devtools/check_vcs_version.py` in CI PR Main

## 6. Package naming

| Layer | Name |
|-------|------|
| PyPI / `pip install` | `endorlabs` |
| Python import | `endorlabs` |
| GitHub repo | `endorlabs/endorlabs-sdk` (unchanged) |

## 7. Suggested release tag

Cut **`v0.1.0`** (or next semver) from current `main` after merge. Dev-series anchor remains `v0.1.1.dev0` for local editable builds (`0.1.1.devN` between anchors).
