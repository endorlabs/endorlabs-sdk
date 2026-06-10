# Release and PyPI publishing

Maintainer guide for version tags, hatch-vcs, OIDC trusted publishing, and release CI.

Configure **pending** Trusted Publishing on TestPyPI and PyPI before the first upload to each index.

## hatch-vcs and dev tags

`hatch-vcs` delegates to **setuptools-scm**. SCM computes post-tag versions as
`{tag_base}.dev{N}` where **N = commits since the tag**.

That only works when the tag ends in **`.dev0`** (dev-series anchor), e.g. `v0.1.1.dev0` →
`0.1.1.dev4` four commits later.

Tags like **`v0.1.1.dev19`** encode “dev 19” in the tag itself. SCM then refuses to bump
(“choosing custom numbers for the `.devX` distance is not supported”) and **`uv sync` /
editable installs fail**—the error in local Endor scans against `pypi://endorlabs@…`.

**Repo fix (in `pyproject.toml`):**

1. **`[tool.hatch.version.raw-options].git_describe_command`** — development trees describe only
   `v*.*.*.dev0` anchors (so `0.1.1.dev23`, not `0.1.1.dev19` from a bad tag).
2. **Release CI** — `.github/workflows/release-tag-publish.yml` sets
   `SETUPTOOLS_SCM_PRETEND_VERSION` from the pushed tag (`v0.1.0` → `0.1.0`) so wheels are
   exactly the release version, not a `.devN` distance.
3. **`local_scheme = "no-local-version"`** — wheels do not get `+g<hash>` suffixes (PyPI-friendly).
4. Do **not** put `tag-pattern` on `[tool.hatch.version]` with a group that includes `.dev0` in the
   captured version (e.g. `0.1.1.dev0`) — setuptools-scm treats that as a custom dev id and fails.

Nearest valid anchor today: **`v0.1.1.dev0`** → working tree versions like `0.1.1.devN`.

**Remote tag hygiene (recommended):** delete or stop creating tags that break SCM
(`v0.1.1.dev19`, `v0.1.0.dev1`, `v0.1.0-test.*`, `v0.1.1.dev-build.*`). The describe command
mitigates them, but cleaning the remote avoids confusion for other tools (Endor scans, `git describe`).

## PEP 440 and PyPI rules (summary)

| Rule | Practice for this package |
|------|---------------------------|
| Public release versions | `X.Y.Z` only on PyPI (e.g. `0.1.0`)—tag `v0.1.0` at the release commit |
| Pre-releases | `X.Y.Za1`, `X.Y.Zb1`, `X.Y.Zrc1` if needed; tag `v0.2.0rc1` |
| Dev series (local/TestPyPI only) | Anchor `vX.Y.Z.dev0`; SCM emits `X.Y.Z.devN` between anchors |
| **Do not** use custom `.devN` in tags | No `v0.1.1.dev19`—use git distance instead |
| Local segments `+gHASH` | Stripped for wheels via `local_scheme = "no-local-version"` in `pyproject.toml` |
| TestPyPI | Same version strings; upload there first, smoke-install, then PyPI |

PyPI rejects many local-version forms on upload; **release builds must be cut from a
release tag** (`vX.Y.Z`), not from a random branch with a `.devN` version.

## Package metadata checklist (PEP-anchored)

| Requirement | Status in `pyproject.toml` |
|-------------|---------------------------|
| `[build-system]` pinned backend (PEP 518/517) | `hatchling==1.30.1`, `hatch-vcs==0.5.0` |
| `[project]` name, description, readme, requires-python, authors (PEP 621) | Present |
| Dependencies as PEP 508 strings | Present (pinned `==` for reproducibility) |
| License SPDX + `license-files` (PEP 639, metadata 2.4) | `license = "MIT"`, `license-files = ["LICENSE"]` |
| `[project.urls]` Homepage, Repository, Documentation, Changelog, Issues | Present |
| Version via PEP 440 tags | Dynamic (`hatch-vcs`); no static version in tree |

## Git tag policy

### Production (PyPI)

```text
vMAJOR.MINOR.PATCH     →  version MAJOR.MINOR.PATCH   (e.g. v0.1.0 → 0.1.0)
vMAJOR.MINOR.PATCHrcN  →  version MAJOR.MINOR.PATCHrcN (publish skipped by default)
```

### Development series (not published to PyPI)

```text
vMAJOR.MINOR.PATCH.dev0   →  anchor only; SCM produces MAJOR.MINOR.PATCH.devN after it
```

After a successful **final** PyPI publish, CI pushes the next dev anchor automatically
(e.g. release `v0.1.1` → anchor `v0.1.2.dev0`).

### Avoid (break SCM or are ignored by git_describe_command)

```text
v0.1.1.dev19
v0.1.0.dev1
v0.1.0-test.20260511.1
v0.1.1.dev-build.20260519.1
```

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
2. Register **both** pending publishers (same project `endorlabs`, environment `pypi`):
   - **Workflow name:** `release-tag-publish.yml` — tag-driven final releases (`vX.Y.Z`)
   - **Workflow name:** `release-pypi.yml` — manual `workflow_dispatch` when needed
3. **Environment name:** `pypi`

### GitHub Environments (Settings → Environments)

| Environment | Used by | Recommended protection |
|-------------|---------|------------------------|
| `testpypi` | `release-testpypi.yml` | Optional reviewers |
| `pypi` | `release-tag-publish.yml`, `release-pypi.yml` | Required reviewers |

No `PYPI_API_TOKEN` or `TEST_PYPI_API_TOKEN` secrets are used. OIDC + PEP 740 attestations
are handled by `pypa/gh-action-pypi-publish` pinned to a release commit SHA (attestations on by default).

Pin the action to the **git commit SHA** for a release (e.g. `@cef22109… # v1.14.0`), not `@release/v1` (moving branch; Endor “Block Misconfigured GHAs”) and not a **tag object SHA** (PyPA publishes `ghcr.io` images keyed by commit SHA only — tag object SHAs cause `manifest unknown`).

## Local verification (before any upload)

```bash
# From repo root, full git history (tags)
git fetch --tags

# Should print a PEP 440 version (no setuptools-scm error)
uv run python devtools/check_vcs_version.py

# Editable install path used by uv sync / Endor scans
uv sync --dev

# Build release artifacts (optional: set SETUPTOOLS_SCM_PRETEND_VERSION=0.1.1 in the environment for local simulation)
uv build
uv run twine check dist/*
uv run python devtools/smoke_test_wheel.py
```

Do not publish wheels built with `SETUPTOOLS_SCM_PRETEND_VERSION` unless CI also sets the
same version from a tag or workflow input.

## CI workflows

### TestPyPI — `.github/workflows/release-testpypi.yml`

- **Trigger:** `workflow_dispatch` with inputs `version` (required) and `ref` (default `main`)
- **Build job:** `check_vcs_version.py`, `uv build`, `twine check`, upload artifact
- **Publish job:** `environment: testpypi`, `permissions: id-token: write`, OIDC publish to TestPyPI
- **Use for:** staging uploads and smoke installs before production; keep available on branches when validating deployment changes

### PyPI (manual) — `.github/workflows/release-pypi.yml`

- **Trigger:** `workflow_dispatch` with inputs `version` (required) and `ref` (default `main`)
- **Build job:** same as TestPyPI manual path (`check_vcs_version.py`, `uv build`, `twine check`)
- **Publish job:** `environment: pypi`, OIDC publish to PyPI with attestations
- **Use for:** manual production uploads when tag-driven release is not appropriate; prefer **`release-tag-publish.yml`** for final `vX.Y.Z` cuts (full quality gate + GitHub Release + dev anchor bump)

### Production PyPI (tag) — `.github/workflows/release-tag-publish.yml`

- **Trigger:** push tag matching `v*`
- **Classify:** final releases match `vX.Y.Z` exactly; dev anchors and pre-releases skip publish
- **Build job (final only):** full quality gate, model-sync drift checks, `uv build`, `twine check`, GitHub Release
- **Publish job (final only):** `environment: pypi`, OIDC publish to PyPI with attestations
- **Post-release bump (final only):** pushes `vX.Y.(Z+1).dev0` dev anchor tag

```mermaid
flowchart TD
  dispatchTest["workflow_dispatch release-testpypi.yml"] --> testBuild[build + twine check]
  testBuild --> pubT["publish-testpypi OIDC → TestPyPI"]
  dispatchProd["workflow_dispatch release-pypi.yml"] --> prodManualBuild[build + twine check]
  prodManualBuild --> pubM["publish-pypi OIDC → PyPI"]
  tag["push vX.Y.Z tag"] --> gate{final version?}
  gate -- yes --> prodBuild[build + gate + GitHub Release]
  prodBuild --> pubP["publish-pypi OIDC → PyPI"]
  pubP --> bump["push vX.Y.Z+1.dev0 anchor"]
  bump -.->|dev anchor| gate
  gate -- no --> skip[skip publish]
```

## TestPyPI smoke install

After a TestPyPI publish via **Release TestPyPI Publish**:

```bash
uv run python devtools/smoke_test_published_install.py --version <version>
```

Or install manually from `https://test.pypi.org/project/endorlabs/`.

## Production release

1. Configure pending publishers on pypi.org for `release-tag-publish.yml` and/or `release-pypi.yml` / environment `pypi`
2. **Recommended (final release):** tag at the release commit: `git tag -a vX.Y.Z -m "Release X.Y.Z" && git push origin vX.Y.Z`
3. Wait for **Release Tag Publish** workflow; confirm PyPI provenance and GitHub Release assets
4. Confirm CI pushed the next dev anchor tag (`vX.Y.(Z+1).dev0`)

**Manual PyPI:** run **Release PyPI Publish** (`release-pypi.yml`) with an explicit `version` and `ref` when you need a dispatch upload without a tag (same OIDC path; no GitHub Release or dev-anchor bump).

## Changelog at release cut

Before tagging `vX.Y.Z`:

1. Open [`docs/changelog.md`](../changelog.md) **Unreleased** — collapse model-sync-only work into one **Changed** footnote or omit.
2. Rename **Unreleased** → **`## X.Y.Z`**; leave fresh empty **Unreleased** subsection headers.
3. Grep removed CLI/API names; durable docs describe **current** behavior only (upgraders read the changelog).

Intake while merging PRs: [`.github/pull_request_template.md`](../../.github/pull_request_template.md) and [`endor-changelog`](../../agent-knowledge/rules/endor-changelog.md). Do not auto-generate the changelog from `git log`.

## Related files

- Version config: `pyproject.toml` → `[tool.hatch.version]`, `[tool.hatch.build.hooks.vcs]`
- Generated at build: `src/endorlabs/_version.py` (gitignored)
- Release CI: `.github/workflows/release-tag-publish.yml`, `.github/workflows/release-pypi.yml`, `.github/workflows/release-testpypi.yml`
- Local helpers: `devtools/check_vcs_version.py`, `devtools/smoke_test_wheel.py`, `devtools/smoke_test_published_install.py`
