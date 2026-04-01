# PR comments and GitHub Checks (API-backed findings)

This guide covers **repo-side** PR feedback in CI after an Endor Labs GitHub Action scan. Findings are loaded from the **Endor API** (Project → ScanResult → `Finding`), then posted to **pull request review comments** (Option B) and/or **Checks annotations** (Option C).

In [`.github/workflows/ci-pr-main.yml`](.github/workflows/ci-pr-main.yml) (`endorlabs-security-scan` job), **Option B** and **Option C** default to **enabled** on pull requests. Set repository variables to `false` to turn a path off. Both default to **`apply`** (post inline reviews and check-run annotations). Set `ENDOR_INHOUSE_PR_COMMENTS_MODE` / `ENDOR_GITHUB_CHECK_MODE` to **`dry-run`** to log the plan only (Option B still prints each inline comment with a code-region fence in the job log).

## Data flow (Options B and C)

1. The **Endor Labs** action runs a scan and uploads results to the platform.
2. [`.github/scripts/endor_ci_fetch_scan_findings.py`](.github/scripts/endor_ci_fetch_scan_findings.py) resolves the **Project** by `https://github.com/{owner}/{repo}.git` (and a non-`.git` variant), lists **ScanResults** for that project (newest first), prefers a result whose `spec.versions[].sha` matches the PR **head SHA**, and reads finding UUIDs from `spec.findings` (or `blocking_findings` + `warning_findings`). It **GETs** each **Finding** and serializes to dicts for the GitHub scripts.
3. **Option B** / **Option C** map those dicts to GitHub REST payloads (same field expectations as [`.github/scripts/endor_scan_findings.py`](.github/scripts/endor_scan_findings.py) for `file` / `line` in `spec.finding_metadata`).

Short poll (default ~120s, jittered backoff) waits for a **non-running** ScanResult so the job does not race the platform indexer. On failure or empty data, scripts **fail open** (log and exit 0) so cosmetic steps do not break CI.

## Option B — Inline pull request review comments

Workflow step: `Option B - inline PR review comments (dry-run/apply)`

- Script: [`.github/scripts/post_parallel_pr_comments.py`](.github/scripts/post_parallel_pr_comments.py)

Option B posts **only** [pull request review comments](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/reviewing-changes-in-pull-requests/about-pull-request-reviews) (inline on the diff). GitHub shows the **diff context** for each anchored line. Comments are submitted in batches via `POST .../pulls/{n}/reviews` with `event: COMMENT`; failed batches fall back to per-comment `POST .../pulls/{n}/comments`. Finding paths are matched against `GET .../pulls/{n}/files` so anchors align with the PR.

Repository variables (optional overrides):

- `ENDOR_ENABLE_INHOUSE_PR_COMMENTS` — omit or `true` to run; set `false` to skip.
- `ENDOR_INHOUSE_PR_COMMENTS_MODE=apply` (default) or `dry-run`

Required secrets and variables:

- `GITHUB_TOKEN` in the job (write perms below)
- `ENDOR_NAMESPACE`, `ENDOR_API` (variable), `ENDOR_API_CREDENTIALS_KEY` / `ENDOR_API_CREDENTIALS_SECRET` (secrets)

Required permissions:

- Workflow job permission `pull-requests: write`

Behavior:

- Paginated fetch of existing PR review comments to dedupe via hidden HTML markers.
- Skips findings whose path is not in the PR file list (or normalizes path when the file list is empty).
- Optional multi-line anchors when `line_end` is present in metadata (`start_line` / `line` on `RIGHT` side).
- Failed review batches log the **full GitHub error body** then try per-comment fallback.

CLI (optional):

- `--poll-timeout` — seconds to wait for a terminal ScanResult (default `120`).
- `--max-findings` — cap on `Finding.get` calls (default `500`).
- `--max-inline` — max inline threads (default `30`).
- `--review-batch-size` — comments per `.../reviews` request (default `25`).

## Option C — GitHub Check Run annotations

Workflow step: `Option C - GitHub Check Run annotations (dry-run/apply)`

- Script: [`.github/scripts/post_github_check_run.py`](.github/scripts/post_github_check_run.py)

Repository variables (optional overrides):

- `ENDOR_ENABLE_GITHUB_CHECK_ANNOTATIONS` — omit or `true` to run; set `false` to skip.
- `ENDOR_GITHUB_CHECK_MODE=apply` (default) or `dry-run`

Required permissions:

- `checks: write` and `GITHUB_TOKEN`. Same `ENDOR_*` credentials as Option B.

Behavior:

- Creates a completed **check run** on the PR head commit with `output.annotations` for findings that have `file` + `line` in metadata.
- Maps `spec.level` to GitHub annotation levels (`FINDING_LEVEL_CRITICAL` / `HIGH` → `failure`, `MEDIUM` → `warning`, else `notice`).
- Batches annotations (50 per request) with PATCH for follow-up batches.
- Findings without location still appear in the check run **summary** markdown table.

For **SARIF** upload to Code Scanning, use GitHub’s `github/codeql-action/upload-sarif` separately; Option C uses the Checks API only.

## Embedded UX capability matrix

| Capability | Option B (inline reviews) | Option C (Checks API) |
|---|---|---|
| Native diff snippet on conversation / files | Yes (anchored review comments) | No (Checks / annotations UX) |
| Markdown in comment body | Yes | In check summary text |
| File+line blob links | Yes | N/A (annotations anchor to path/lines) |
| Checks tab | No | Yes |
| Dedupe across reruns | Hidden markers in bodies | New check run per workflow run |

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

- Use **Option B** when you want **inline threads on the PR diff** (same class of UX as native line comments).
- Use **Option C** when you want the **Checks** tab and structured annotations.
- Running **both** can duplicate signals on the same lines; disable one if that is too noisy.

## Failure modes

- Missing `ENDOR_API_CREDENTIALS_*` or `ENDOR_NAMESPACE` → API fetch logs errors; scripts skip with exit 0.
- No **Project** for the repository URL → skip (ensure `meta.name` on the Project matches `https://github.com/owner/repo.git` or the same without `.git`).
- ScanResult still **RUNNING** until poll timeout → best-effort pick; may yield empty finding UUIDs.
- Missing finding location metadata → Option B posts nothing for those rows; Option C lists them in the check summary only.
- Path not in PR diff / line not commentable → GitHub **422**; batch failure logs response body; per-comment fallback may still skip.
- Option C: missing `checks: write` → apply mode fails; use `dry-run` first.
