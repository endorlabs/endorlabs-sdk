# PR comments and GitHub Checks (API-backed findings)

This guide covers **repo-side** PR feedback in CI after an Endor Labs GitHub Action scan. Findings are loaded from the **Endor API** (Project → ScanResult → `Finding`), then posted only to surfaces GitHub renders (issue comments, review comments, Checks annotations).

In [`.github/workflows/ci-pr-main.yml`](.github/workflows/ci-pr-main.yml) (`endorlabs-security-scan` job), **Option B** and **Option C** default to **enabled** on pull requests. Set repository variables to `false` to turn a path off. Both default to **`dry-run`** until you set `ENDOR_INHOUSE_PR_COMMENTS_MODE` / `ENDOR_GITHUB_CHECK_MODE` to `apply`.

## Data flow (Options B and C)

1. The **Endor Labs** action runs a scan and uploads results to the platform.
2. [`.github/scripts/endor_ci_fetch_scan_findings.py`](.github/scripts/endor_ci_fetch_scan_findings.py) resolves the **Project** by `https://github.com/{owner}/{repo}.git` (and a non-`.git` variant), lists **ScanResults** for that project (newest first), prefers a result whose `spec.versions[].sha` matches the PR **head SHA**, and reads finding UUIDs from `spec.findings` (or `blocking_findings` + `warning_findings`). It **GETs** each **Finding** and serializes to dicts for the GitHub scripts.
3. **Option B** / **Option C** map those dicts to GitHub REST payloads (same field expectations as [`.github/scripts/endor_scan_findings.py`](.github/scripts/endor_scan_findings.py) for `file` / `line` in `spec.finding_metadata`).

Short poll (default ~120s, jittered backoff) waits for a **non-running** ScanResult so the job does not race the platform indexer. On failure or empty data, scripts **fail open** (log and exit 0) so cosmetic steps do not break CI.

## Option B — In-house parallel GitHub comments

Workflow step: `Option B - in-house parallel PR comments (dry-run/apply)`

- Script: [`.github/scripts/post_parallel_pr_comments.py`](.github/scripts/post_parallel_pr_comments.py)

Repository variables (optional overrides):

- `ENDOR_ENABLE_INHOUSE_PR_COMMENTS` — omit or `true` to run; set `false` to skip.
- `ENDOR_INHOUSE_PR_COMMENTS_MODE=dry-run` (default) or `apply`

Required secrets and variables:

- `GITHUB_TOKEN` in the job (write perms below)
- `ENDOR_NAMESPACE`, `ENDOR_API` (variable), `ENDOR_API_CREDENTIALS_KEY` / `ENDOR_API_CREDENTIALS_SECRET` (secrets)

Required permissions:

- Workflow job permission `pull-requests: write`

Behavior:

- Posts/updates one deterministic rollup summary comment (`<!-- endorlabs-inhouse-summary -->` marker) with deep links.
- Optional per-line review comments for findings with precise `file` + `line` metadata and GitHub blob links.
- Deterministic per-finding markers to avoid duplicate line comments on reruns.

Repository variables:

- `ENDOR_INHOUSE_POST_REVIEW_COMMENTS` — `true` (default) or `false`. Set to `false` when using Option C to reduce duplicate inline surfaces (rollup issue comment still runs when Option B is enabled).

CLI (optional):

- `--poll-timeout` — seconds to wait for a terminal ScanResult (default `120`).
- `--max-findings` — cap on `Finding.get` calls (default `500`).

## Option C — GitHub Check Run annotations

Workflow step: `Option C - GitHub Check Run annotations (dry-run/apply)`

- Script: [`.github/scripts/post_github_check_run.py`](.github/scripts/post_github_check_run.py)

Repository variables (optional overrides):

- `ENDOR_ENABLE_GITHUB_CHECK_ANNOTATIONS` — omit or `true` to run; set `false` to skip.
- `ENDOR_GITHUB_CHECK_MODE=dry-run` (default) or `apply`

Required permissions:

- `checks: write` and `GITHUB_TOKEN`. Same `ENDOR_*` credentials as Option B.

Behavior:

- Creates a completed **check run** on the PR head commit with `output.annotations` for findings that have `file` + `line` in metadata.
- Maps `spec.level` to GitHub annotation levels (`FINDING_LEVEL_CRITICAL` / `HIGH` → `failure`, `MEDIUM` → `warning`, else `notice`).
- Batches annotations (50 per request) with PATCH for follow-up batches.
- Findings without location still appear in the check run **summary** markdown table.

For **SARIF** upload to Code Scanning, use GitHub’s `github/codeql-action/upload-sarif` separately; Option C uses the Checks API only.

## Embedded UX capability matrix

| Capability | Option B (script) | Option C (Checks API) |
|---|---|---|
| Markdown links in comment body | Supported | In check summary text |
| Snippet line in inline body | When metadata includes text | Message text per annotation |
| File+line deep links in markdown | Blob links from repo + commit SHA | N/A (annotations anchor to path/lines) |
| Inline review comments on PR diff | Supported via review comments API | Not used (annotations instead) |
| Checks tab / structured annotations | Not supported | Supported |
| Deterministic dedupe across reruns | Markers in comment bodies | New check run per workflow run |

## Historical: `PRCommentConfig` (not used in this CI path)

The **`PRCommentConfig`** resource configures **Endor-managed** PR comments (server-side Go templates), not the repo scripts above. Relevant spec fields:

- `spec.platform_type` — SCM platform (e.g. `PLATFORM_SOURCE_GITHUB`).
- `spec.template.findings_summary_template` — Go `text/template` evaluated on the platform when Endor posts PR comments.

This repo **no longer** syncs a custom template from CI. To restore the **vendor default** wording on a tenant after a custom template was applied, run locally (once) with API credentials:

```bash
uv run python .github/scripts/sync_pr_comment_template.py \
  --namespace "$ENDOR_NAMESPACE" \
  --name github-pr-comments-template \
  --template-path .tmp/pr-findings-summary-default-from-endor.tmpl \
  --platform-type PLATFORM_SOURCE_GITHUB
```

Place the stock template text in `.tmp/pr-findings-summary-default-from-endor.tmpl` (that path is typically gitignored). See [`.github/templates/README.md`](.github/templates/README.md).

Endor’s GitHub Action step may still use **`enable_pr_comments: true`** so the platform posts comments using whatever template is configured tenant-side (default after revert).

## Choosing Option B vs Option C

- Use **Option B** when you want an issue-thread rollup and optional review comments with deterministic markers.
- Use **Option C** when you want the **Checks** tab and API-driven annotations. Prefer `ENDOR_INHOUSE_POST_REVIEW_COMMENTS=false` when both run to reduce duplicate inline markers.

## Failure modes

- Missing `ENDOR_API_CREDENTIALS_*` or `ENDOR_NAMESPACE` → API fetch logs errors; scripts skip with exit 0.
- No **Project** for the repository URL → skip (ensure `meta.name` on the Project matches `https://github.com/owner/repo.git` or the same without `.git`).
- ScanResult still **RUNNING** until poll timeout → best-effort pick; may yield empty finding UUIDs.
- Missing finding location metadata → Option B rollup only; Option C summary-only for those rows.
- Outdated PR diff → line comment POST may fail; script logs and continues.
- Option C: missing `checks: write` → apply mode fails; use `dry-run` first.
