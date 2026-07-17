# Release and PyPI publishing

Maintainer guide for static `[project].version`, git tag release identity, OIDC trusted publishing, and release CI.

Configure **pending** Trusted Publishing on TestPyPI and PyPI before the first upload to each index.

## Version model (tag identity + TOML projection)

Release identity follows the monorepo pattern: **`vX.Y.Z` git tags** and the workflow `version` input are authoritative. The committed **`[project].version`** field is the Endor-visible projection — endorctl’s uv plugin TOML-parses that field only; it does not run hatch-vcs, uv-dynamic-versioning, or `uv version` to compute a version. When `[project].version` is missing or dynamic, scans fall back to the git ref (e.g. `@main`).

| Layer | Source of truth |
|-------|-----------------|
| Release cut | Git tag `vX.Y.Z` + workflow `version: X.Y.Z` |
| Endor / package firewall scans | Committed `[project].version` in `pyproject.toml` |
| Wheel / PyPI metadata | Same static version at build time (must match workflow input) |
| Runtime `endorlabs.__version__` | `importlib.metadata.version("endorlabs")` from installed package metadata |

**Between releases on `main`:** leave `[project].version` at the **last shipped** `X.Y.Z`. The next release PR bumps TOML + [`docs/changelog.md`](../changelog.md) together. Do not use day-to-day `uv version --bump` as the product workflow; use it only inside a release PR if you prefer the CLI over editing TOML by hand.

Do **not** introduce `uv-dynamic-versioning` or restore hatch-vcs — both leave version out of TOML and break Endor scan identity.

## PEP 440 and PyPI rules (summary)

| Rule | Practice for this package |
|------|---------------------------|
| Public release versions | `X.Y.Z` only on PyPI (e.g. `0.6.0`) — tag `v0.6.0` at the release commit |
| Pre-releases | `X.Y.Za1`, `X.Y.Zb1`, `X.Y.Zrc1` if needed; tag `v0.2.0rc1` |
| **Between releases** | Committed `[project].version` stays at last shipped `X.Y.Z` until the release PR |
| TestPyPI | Same version strings; upload there first, smoke-install, then PyPI |

PyPI versions are immutable. Release CI asserts `[project].version` equals the workflow `version` input before `uv build`.

## Package metadata checklist (PEP-anchored)

| Requirement | Status in `pyproject.toml` |
|-------------|---------------------------|
| `[build-system]` pinned backend (PEP 518/517) | `hatchling==1.30.1` |
| `[project]` name, description, readme, requires-python, authors (PEP 621) | Present |
| `[project].version` static PEP 440 string | Present (committed) |
| Dependencies as PEP 508 strings | Present (pinned `==` for reproducibility) |
| License SPDX + `license-files` (PEP 639, metadata 2.4) | `license = "MIT"`, `license-files = ["LICENSE"]` |
| `[project.urls]` Homepage, Repository, Documentation, Changelog, Issues | Present |

## Git tag policy

### Production (PyPI)

```text
vMAJOR.MINOR.PATCH     →  version MAJOR.MINOR.PATCH   (e.g. v0.6.0 → 0.6.0)
vMAJOR.MINOR.PATCHrcN  →  version MAJOR.MINOR.PATCHrcN (publish skipped by default)
```

### Legacy dev anchors (obsolete)

Historical `vX.Y.Z.dev0` tags existed for hatch-vcs. They are **no longer used** for version computation. Optional: delete remote `.dev0` tags during housekeeping; `check_project_version.py` warns if any remain locally.

## Trusted Publishing setup (OIDC — no API tokens)

Configure **pending** publishers before the first upload to each index.

### TestPyPI (test.pypi.org)

1. Sign in → **Account settings** → **Publishing** → **Add a new pending publisher**
2. **PyPI project name:** `endorlabs`
3. **GitHub owner:** `endorlabs`
4. **Repository name:** `endorlabs-sdk`
5. **Workflow name:** `release-testpypi.yml`
6. **Environment name:** `testpypi`

### PyPI (pypi.org — production)

1. Same steps on pypi.org → **Publishing**
2. Register a pending publisher (project `endorlabs`, environment `pypi`):
   - **Workflow name:** `release-tag-publish.yml` — **required**; all production uploads use this workflow today
3. **Environment name:** `pypi`

`release-pypi.yml` is **not** registered on PyPI for this repo. Runs with `publish: true`
fail OIDC with `invalid-publisher` unless a separate pending publisher is added for that
workflow file. Use `release-pypi.yml` only for **dry-run** builds (`publish: false`) unless
infra registers it.

### GitHub Environments (Settings → Environments)

| Environment | Used by | Recommended protection |
|-------------|---------|------------------------|
| `testpypi` | `release-testpypi.yml` | Optional reviewers |
| `pypi` | `release-tag-publish.yml` (publish job); `release-pypi.yml` only if a second publisher is registered | Required reviewers |

The `pypi` environment uses **deployment branch policy: protected branches only**. Deployments
from **tag refs are rejected** even when `PYPI_TAG_PUBLISH_ENABLED=true`. Production publish
must run from a **protected branch** ref (typically `main` via `workflow_dispatch`), then a
reviewer approves the pending deployment.

No `PYPI_API_TOKEN` or `TEST_PYPI_API_TOKEN` secrets are used. OIDC + PEP 740 attestations
are handled by `pypa/gh-action-pypi-publish` pinned to a release commit SHA (attestations on by default).

Pin the action to the **git commit SHA** for a release (e.g. `@cef22109… # v1.14.0`), not `@release/v1` (moving branch; Endor “Block Misconfigured GHAs”) and not a **tag object SHA** (PyPA publishes `ghcr.io` images keyed by commit SHA only — tag object SHAs cause `manifest unknown`).

## Local verification (before any upload)

```bash
# From repo root
uv sync --dev

# Should print the committed [project].version
uv version --short
uv run python devtools/ship/check_project_version.py

# Release simulation (version must already be committed on the branch you build)
uv run python devtools/ship/check_project_version.py --expect 0.6.0
uv run python devtools/ship/verify_ship_artifacts.py --fetch-spec --verify-changelog 0.6.0
uv build
uv run twine check dist/*
uv run python devtools/ship/smoke_test_wheel.py --expect-version 0.6.0
```

## CI workflows

### TestPyPI — `.github/workflows/release-testpypi.yml`

- **Trigger:** `workflow_dispatch` with inputs `version` (required) and `ref` (default `main`)
- **Build job:** composite `release-build-gate` (ruff, pyright, unit tests, `verify_ship_artifacts`, static version assert, `uv build`, `twine check`, wheel smoke)
- **Publish job:** `environment: testpypi`, OIDC publish to TestPyPI, then `smoke_test_published_install.py`
- **Use for:** staging uploads and smoke installs before production

### PyPI (dry-run) — `.github/workflows/release-pypi.yml`

- **Trigger:** `workflow_dispatch` with inputs `version`, `ref` (default `main`), and `publish` (default **`false`**)
- **Build job:** same composite gate as TestPyPI
- **Publish job:** runs only when `publish: true`; `environment: pypi`, OIDC publish to PyPI
- **Supported use today:** `publish: false` — build, gate, and upload artifacts only (no OIDC)
- **Production:** not used for successful PyPI uploads in this repo; OIDC is registered only for `release-tag-publish.yml`

### Production PyPI — `.github/workflows/release-tag-publish.yml`

- **Trigger:** push tag matching `v*`, or `workflow_dispatch` with `version`, `ref`, and `publish` (default **`false`**)
- **Classify:** final releases match `vX.Y.Z` exactly; pre-releases skip build
- **Build job (final only):** composite release build gate; artifacts uploaded (no GitHub Release until publish succeeds)
- **Publish job:** when `publish: true` (dispatch input) or repository variable `PYPI_TAG_PUBLISH_ENABLED=true` on tag push — subject to `pypi` environment branch policy (see above)
- **GitHub Release:** after successful PyPI publish (not before)
- **Canonical production cut:** `workflow_dispatch` with `ref: main`, `version: X.Y.Z`, `publish: true`, then approve the `pypi` environment deployment

```mermaid
flowchart TD
  releasePR["Release PR: changelog + version = X.Y.Z"] --> merge[Merge to main]
  merge --> dispatch["workflow_dispatch release-tag-publish.yml"]
  dispatch --> gate[release-build-gate]
  gate --> assert["Assert TOML version == inputs.version"]
  assert --> build["uv build"]
  build --> approve{pypi env approval}
  approve --> pubP["OIDC PyPI + GitHub Release"]
  dispatchTest["workflow_dispatch release-testpypi.yml"] --> testGate[release-build-gate]
  testGate --> pubT["OIDC TestPyPI + smoke install"]
  dispatchDry["workflow_dispatch release-pypi.yml publish=false"] --> dryGate[release-build-gate]
  dryGate --> dryArtifacts[artifacts only]
```

## Dry-run workflows (no PyPI upload)

Validate the full gate without publishing:

1. **Release Tag Publish** — `workflow_dispatch`, `version: X.Y.Z`, `ref: main`, `publish: false` (preferred dry-run; same workflow as production)
2. **Release PyPI Publish** — `workflow_dispatch`, `version: X.Y.Z`, `publish: false` (alternate dry-run only)

Tag pushes run **build-only** by default until `PYPI_TAG_PUBLISH_ENABLED=true`. Even with that
variable set, **tag-push publish still fails** under the current `pypi` environment protected-branch
policy — use `workflow_dispatch` from `main` instead.

## Rollback and TestPyPI hygiene

| Action | When |
|--------|------|
| **Yank** on TestPyPI | Trial uploads are expendable; yank before re-uploading the same version |
| **Yank + patch** on production PyPI | Bad release shipped **and** the installable artifact is dirty (wheel or default install path) — yank `X.Y.Z`, publish `X.Y.(Z+1)` from a fix commit |
| **Supersede without yank** | Prefer a clean `X.Y.(Z+1)` when older artifacts are superseded; yank is optional if installable paths were already clean |
| **Do not** rewrite published prod versions | PyPI versions are immutable; yank only |

**Artifact surfaces:** hatchling wheels and sdists both ship package content only (`[tool.hatch.build.targets.wheel] packages = ["src/endorlabs"]`; `[tool.hatch.build.targets.sdist] only-packages = true`). Neither includes `tests/`, `devtools/`, or authoring `agent-knowledge/`.

## TestPyPI smoke install

After a TestPyPI publish via **Release TestPyPI Publish**:

```bash
uv run python devtools/ship/smoke_test_published_install.py --version <version>
```

Or install manually from the TestPyPI project page for `endorlabs`.

## Production release

1. Ensure PyPI pending publisher is registered for **`release-tag-publish.yml`** / environment **`pypi`**
2. **Release PR on `main`:** promote [`docs/changelog.md`](../changelog.md) **Unreleased** → **`## X.Y.Z`** and set **`[project].version = "X.Y.Z"`** in `pyproject.toml` (see [Changelog at release cut](#changelog-at-release-cut) below).
3. **Actions → Release Tag Publish** → `workflow_dispatch`:
   - `version`: `X.Y.Z`
   - `ref`: `main`
   - `publish`: `true`
4. **Approve** the pending **`pypi`** environment deployment (required reviewers)
5. Confirm the PyPI project page for `endorlabs` and GitHub Release assets
6. **Optional:** push annotated tag `vX.Y.Z` at the release commit for consumers (`git tag -a vX.Y.Z -m "Release X.Y.Z" && git push origin vX.Y.Z`). Tag push alone does **not** publish under current environment rules

Do **not** use **Release PyPI Publish** (`release-pypi.yml`) with `publish: true` for production unless a matching PyPI pending publisher is registered for that workflow.

## Changelog at release cut

Before publishing `X.Y.Z`:

1. Open [`docs/changelog.md`](../changelog.md) **Unreleased** — collapse model-sync-only work into one **Changed** footnote or omit.
2. Rename **Unreleased** → **`## X.Y.Z`**; leave fresh empty **Unreleased** subsection headers.
3. Set **`[project].version = "X.Y.Z"`** in `pyproject.toml` (same PR as the changelog cut).
4. Grep removed CLI/API names; durable docs describe **current** behavior only (upgraders read the changelog).
5. Merge to **`main`** before running the release workflow (`ref: main`).

**CI note:** `.github/workflows/ci-pr-main.yml` ignores `docs/**`. A changelog-only PR does not run
**Branch Protection CI Gate** unless you also change a non-ignored path (for example bumping
`[project].version` in `pyproject.toml`).

Intake while merging PRs: [`.github/pull_request_template.md`](../../.github/pull_request_template.md) and [`endor-changelog`](../../agent-knowledge/rules/endor-changelog.md). Do not auto-generate the changelog from `git log`.

## Related files

- Version config: `pyproject.toml` → `[project].version` (static)
- Build backend: `pyproject.toml` → `[tool.hatch.build.targets.*]`
- Release CI: `.github/workflows/release-tag-publish.yml` (production), `.github/workflows/release-testpypi.yml` (staging), `.github/workflows/release-pypi.yml` (dry-run builds only unless a second PyPI publisher is registered)
- Local helpers: `devtools/ship/check_project_version.py`, `devtools/ship/smoke_test_wheel.py`, `devtools/ship/smoke_test_published_install.py`
- Release gate: `.github/actions/release-build-gate/action.yml`
