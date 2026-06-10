# PR review comments from Endor findings (API-backed)

This guide covers **repo-side** PR feedback in CI after an Endor Labs GitHub Action scan. Findings are loaded from the **Endor API** (Project -> ScanResult -> findings scoped by PR context when available), then posted as [**pull request review comments**](https://docs.github.com/en/rest/pulls/comments) inside a [**pull request review**](https://docs.github.com/en/rest/pulls/reviews). These are **not** issue comments, commit comments, or GitHub Checks annotations.

In [`.github/workflows/ci-pr-main.yml`](../../.github/workflows/ci-pr-main.yml) (`endorlabs-security-scan` job), this flow defaults to **enabled** on pull requests. Set repository variable `ENDOR_ENABLE_INHOUSE_PR_COMMENTS` to `false` to skip. Default mode is **`apply`**; set `ENDOR_INHOUSE_PR_COMMENTS_MODE` to **`dry-run`** to log the planned comments only (each planned comment is printed with a code-region fence in the job log).

## Data flow

1. The **Endor Labs** action runs a scan and uploads results to the platform.
2. [`.github/scripts/endor_ci_fetch_scan_findings.py`](../../.github/scripts/endor_ci_fetch_scan_findings.py) resolves the **Project** by `https://github.com/{owner}/{repo}.git` (and a non-`.git` variant), lists **ScanResults** for that project (newest first), and picks a result whose `spec.versions[].sha` matches the PR **head SHA** (preferring `TYPE_PR_SECURITY_REVIEW` when several match). When `spec.environment.config` exposes a PR context id (e.g. `ExecutionID`), findings are loaded with **`Finding.list`** and OpenAPI **`list_parameters.ci_run_uuid`**; otherwise UUIDs from `spec.findings` (or blocking + warning lists) are hydrated via **`Finding.get`**. Dicts are passed to the posting script.
3. [`.github/scripts/post_parallel_pr_comments.py`](../../.github/scripts/post_parallel_pr_comments.py) maps findings to GitHub review payloads. Location resolution is centralized in [`.github/scripts/endor_scan_findings.py`](../../.github/scripts/endor_scan_findings.py) (`extract_location`): `spec.finding_metadata` (including `file_path` / `line_number`, `security_review_data.code_snippet`, and `custom` Semgrep-style `path` + `start.line`), then `spec.dependency_file_paths` and summary fallbacks when needed.

**Field-level crosswalk:** [pr-review-comment-matrix.md](pr-review-comment-matrix.md).

**Validate before pushing:**

- Offline (no credentials): `uv run python .github/scripts/validate_pr_comment_flow.py --fixture tests/unit/github_scripts/fixtures/pr_comment_flow_golden.json`
- Live (same API path as CI): `uv run --env-file .env python .github/scripts/validate_pr_comment_flow.py --repo owner/repo --commit-sha <head-sha>`

Use `--fail-if-zero-located` to exit non-zero when findings load but none have an extractable file+line (common when API shape drifts).

Short poll (default ~120s in the script, workflow may pass `--poll-timeout`) waits for a **non-running** ScanResult so the job does not race the platform indexer. On failure or empty data, the script **fails open** (log and exit 0) so cosmetic steps do not break CI.

## Workflow step and script

Workflow step: **Post Endor findings as PR review comments (dry-run/apply)**

- Script: [`.github/scripts/post_parallel_pr_comments.py`](../../.github/scripts/post_parallel_pr_comments.py)

The script submits a **pull request review** (`POST .../pulls/{n}/reviews`) with `event: COMMENT` and a `comments` array of review comments on the **unified diff** (`path`, `line`, `side: RIGHT`, optional multi-line fields). See [Create a review for a pull request](https://docs.github.com/en/rest/pulls/reviews#create-a-review-for-a-pull-request). Failed batches fall back to per-comment `POST .../pulls/{n}/comments`. Finding paths are matched against `GET .../pulls/{n}/files`, and only lines present in **RIGHT-side** patch hunks are kept so GitHub does not return **422**. That is why comments appear under URLs like `.../pull/N/changes/...#r<comment_id>` only when the finding anchors to a changed line in the PR.

### Repository variables

- `ENDOR_ENABLE_INHOUSE_PR_COMMENTS` — omit or `true` to run; set `false` to skip.
- `ENDOR_INHOUSE_PR_COMMENTS_MODE=apply` (default) or `dry-run`

### Required secrets and variables

- `GITHUB_TOKEN` in the job
- `ENDOR_NAMESPACE`, `ENDOR_API` (variable), `ENDOR_API_CREDENTIALS_KEY` / `ENDOR_API_CREDENTIALS_SECRET` (secrets)

### Required permissions

- Workflow job permission `pull-requests: write`

The job also keeps `checks: write` so the **Endor Labs GitHub Action** (which receives `github_token` on the comprehensive scan step) can continue to register its own check runs (e.g. "Endor Labs Automated Scan"); that is separate from this review-comment flow.

### Behavior

- Paginated fetch of existing pull request review comments to dedupe via hidden HTML markers.
- Skips findings whose path is not in the PR file list (or normalizes path when the file list is empty).
- Optional multi-line anchors when `line_end` is present in metadata (`start_line` / `line` on `RIGHT` side).
- Failed review batches log the **full GitHub error body** then try per-comment fallback.

### CLI (optional)

- `--poll-timeout` — seconds to wait for a terminal ScanResult (default `120` in script; CI may override).
- `--max-findings` — cap on loaded findings (default `500`).
- `--max-inline` — max review comments per run (default `30`).
- `--review-batch-size` — comments per `.../reviews` request (default `25`).

## Historical: `PRCommentConfig` (not used in this CI path)

The **`PRCommentConfig`** resource configures **Endor-managed** PR comments (server-side Go templates), not the repo script above. Relevant spec fields:

- `spec.platform_type` — SCM platform (e.g. `PLATFORM_SOURCE_GITHUB`).
- `spec.template.findings_summary_template` — Go `text/template` evaluated on the platform when Endor posts PR comments.

This repo **no longer** syncs a custom template from CI. To restore the **vendor default** wording on a tenant after a custom template was applied, run locally (once) with API credentials:

```bash
uv run python .github/scripts/sync_pr_comment_template.py \
  --namespace "$ENDOR_NAMESPACE" \
  --name github-pr-comments-template \
  --template-path .endorlabs-context/workspace/sessions/agent/exports/pr-findings-summary-default-from-endor.tmpl \
  --platform-type PLATFORM_SOURCE_GITHUB
```

Place the stock template text in `.endorlabs-context/workspace/sessions/<user>/exports/pr-findings-summary-default-from-endor.tmpl` (gitignored under `.endorlabs-context/`). See [`.github/templates/README.md`](../../.github/templates/README.md).

In **this repo's CI** ([`ci-pr-main.yml`](../../.github/workflows/ci-pr-main.yml)), all Endor Labs Action scan steps set **`enable_pr_comments: false`**. PR feedback on pull requests comes only from **Post Endor findings as PR review comments** (`post_parallel_pr_comments.py`). Tenant-side `PRCommentConfig` templates still apply if other scans or automation enable platform PR comments outside this workflow.

**Deprecated GitHub repository variables (safe to remove in repo settings if set):** `ENDOR_ENABLE_GITHUB_CHECK_ANNOTATIONS`, `ENDOR_GITHUB_CHECK_MODE`, and `ENDOR_GITHUB_CHECK_CONCLUSION` were used by a removed Checks-annotations path and are no longer read by workflows.

## Failure modes

- Missing `ENDOR_API_CREDENTIALS_*` or `ENDOR_NAMESPACE` -> API fetch logs errors; script skips with exit 0.
- No **Project** for the repository URL -> skip (ensure `meta.name` on the Project matches `https://github.com/owner/repo.git` or the same without `.git`).
- ScanResult still **RUNNING** until poll timeout -> best-effort pick; may yield empty finding UUIDs.
- Missing finding location metadata -> nothing posted for those rows.
- Path not in PR diff / line not on RIGHT side of a hunk -> GitHub **422**; batch failure logs response body; per-comment fallback may still skip.

For **SARIF** upload to Code Scanning, use GitHub's `github/codeql-action/upload-sarif` separately; this path does not replace code scanning uploads.
