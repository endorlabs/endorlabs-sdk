# PyPI / TestPyPI publication draft (maintainer checklist)

> **Status:** Draft for a future `chore/pypi-release` branch—not enforced in CI yet.
> Goal: stable `uv sync`, `uv build`, and Endor scan editable installs before enabling publish automation.

## Root cause of the hatch-vcs failure

`hatch-vcs` delegates to **setuptools-scm**. SCM computes post-tag versions as
`{tag_base}.dev{N}` where **N = commits since the tag**.

That only works when the tag ends in **`.dev0`** (dev-series anchor), e.g. `v0.1.1.dev0` →
`0.1.1.dev4` four commits later.

Tags like **`v0.1.1.dev19`** encode “dev 19” in the tag itself. SCM then refuses to bump
(“choosing custom numbers for the `.devX` distance is not supported”) and **`uv sync` /
editable installs fail**—the error in local Endor scans against `pypi://endorlabs-sdk@…`.

**Repo fix (in `pyproject.toml`):**

1. **`[tool.hatch.version.raw-options].git_describe_command`** — development trees describe only
   `v*.*.*.dev0` anchors (so `0.1.1.dev23`, not `0.1.1.dev19` from a bad tag).
2. **Release CI** — `.github/workflows/release-tag-publish.yml` sets
   `SETUPTOOLS_SCM_PRETEND_VERSION` from the pushed tag (`v0.1.0` → `0.1.0`) so wheels are
   exactly the release version, not a `.devN` distance.
3. **`local_scheme = "no-local-version"`** — wheels do not get `+g<hash>` suffixes (PyPI-friendly).
3. Do **not** put `tag-pattern` on `[tool.hatch.version]` with a group that includes `.dev0` in the
   captured version (e.g. `0.1.1.dev0`) — setuptools-scm treats that as a custom dev id and fails.

Nearest valid anchor today: **`v0.1.1.dev0`** → working tree versions like `0.1.1.dev23`.

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

## Git tag policy

### Production (PyPI)

```text
vMAJOR.MINOR.PATCH     →  version MAJOR.MINOR.PATCH   (e.g. v0.1.0 → 0.1.0)
vMAJOR.MINOR.PATCHrcN  →  version MAJOR.MINOR.PATCHrcN
```

### Development series (optional; not for first PyPI unless intentional)

```text
vMAJOR.MINOR.PATCH.dev0   →  anchor only; SCM produces MAJOR.MINOR.PATCH.devN after it
```

### Avoid (break SCM or are ignored by tag-pattern)

```text
v0.1.1.dev19
v0.1.0.dev1
v0.1.0-test.20260511.1
v0.1.1.dev-build.20260519.1
```

Consider deleting misleading tags on the remote after team agreement, or leave them
in history but rely on `tag-pattern` (current approach).

## Local verification (before any upload)

```bash
# From repo root, full git history (tags)
git fetch --tags

# Should print a PEP 440 version (no setuptools-scm error)
uv run python devtools/check_vcs_version.py
# or: uv run hatch version

# Editable install path used by uv sync / Endor scans
uv sync --dev
uv build
ls dist/
```

Optional override for emergency debugging only:

```bash
# Windows PowerShell
$env:SETUPTOOLS_SCM_PRETEND_VERSION = "0.1.1.dev0"
uv sync --dev
```

Do not publish wheels built with `PRETEND_VERSION`.

## Release workflow (aligns with `.github/workflows/release-tag-publish.yml`)

Today the workflow on **`v*` tag push**:

1. Full history checkout
2. Quality gate (ruff, pyright, unit tests)
3. Model-sync + stub + reference doc drift checks
4. `uv build` → `dist/*.whl` + `dist/*.tar.gz`
5. GitHub Release attaches artifacts

**Not yet in workflow:** TestPyPI or PyPI upload (intentional—stabilize versioning first).

### Proposed publish sequence (manual → automated later)

1. Merge release candidate to `main`.
2. Confirm `uv run hatch version` at `main` tip is acceptable (or tag first).
3. Create annotated tag: `git tag -a v0.1.0 -m "Release 0.1.0"` and push.
4. Wait for **Release Tag Publish** workflow; download `dist/` from the GitHub Release.
5. **TestPyPI:** `uv publish --index testpypi dist/*` (API token / trusted publishing).
6. Smoke test: `pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ endorlabs-sdk==0.1.0`
7. **PyPI:** `uv publish dist/*` (production index).
8. Verify [PyPI project page](https://pypi.org/project/endorlabs-sdk/) and README links (`endorlabs/endorlabs-sdk`).

### Credentials (your accounts)

- Store tokens in GitHub Actions secrets when automating: `PYPI_API_TOKEN`, `TEST_PYPI_API_TOKEN`.
- Prefer **PyPI trusted publishing** (OIDC) from `endorlabs/endorlabs-sdk` over long-lived tokens.
- Never commit tokens; use `uv publish` env or `~/.pypirc` locally only.

## Future `chore/pypi-release` branch scope

- [ ] Enable TestPyPI publish job (manual `workflow_dispatch` or tag suffix `v*.*.*-test`—decide one scheme).
- [ ] PyPI trusted publishing + production publish job gated on GitHub Release.
- [ ] `devtools/check_vcs_version.py` in CI (fail if `hatch version` errors).
- [ ] Document first public version (0.1.0 vs 0.1.1) and whether TestPyPI gets dev builds.
- [ ] Align `release-tag-publish.yml` with `local_scheme` / tag-pattern (build at tag already clean).
- [ ] Retire or document legacy git tags on the remote.

## Related files

- Version config: `pyproject.toml` → `[tool.hatch.version]`, `[tool.hatch.build.hooks.vcs]`
- Generated at build: `src/endorlabs/_version.py` (gitignored)
- Release CI: `.github/workflows/release-tag-publish.yml`
