# PR comments and GitHub Checks (API-backed findings)

This guide covers **repo-side** PR feedback in CI after an Endor Labs GitHub Action scan. Findings are loaded from the **Endor API** (Project → ScanResult → findings scoped by PR context when available), then posted as [**pull request review comments**](https://docs.github.com/en/rest/pulls/comments) inside a [**pull request review**](https://docs.github.com/en/rest/pulls/reviews) (Option B) and/or **Checks annotations** (Option C). These are **not** issue comments or commit comments.

In [`.github/workflows/ci-pr-main.yml`](.github/workflows/ci-pr-main.yml) (`endorlabs-security-scan` job), **Option B** and **Option C** default to **enabled** on pull requests. Set repository variables to `false` to turn a path off. Both default to **`apply`** (submit reviews with diff-anchored comments and check-run annotations). Set `ENDOR_INHOUSE_PR_COMMENTS_MODE` / `ENDOR_GITHUB_CHECK_MODE` to **`dry-run`** to log the plan only (Option B still prints each planned review comment with a code-region fence in the job log).

## Data flow (Options B and C)

1. The **Endor Labs** action runs a scan and uploads results to the platform.
2. [`.github/scripts/endor_ci_fetch_scan_findings.py`](.github/scripts/endor_ci_fetch_scan_findings.py) resolves the **Project** by `https://github.com/{owner}/{repo}.git` (and a non-`.git` variant), lists **ScanResults** for that project (newest first), and picks a result whose `spec.versions[].sha` matches the PR **head SHA** (preferring `TYPE_PR_SECURITY_REVIEW` when several match). When `spec.environment.config` exposes a PR context id (e.g. `ExecutionID`), findings are loaded with **`Finding.list`** and OpenAPI **`list_parameters.ci_run_uuid`**; otherwise UUIDs from `spec.findings` (or blocking + warning lists) are hydrated via **`Finding.get`**. Dicts are passed to the GitHub scripts.
3. **Option B** / **Option C** map those dicts to GitHub REST payloads. Location resolution is centralized in [`.github/scripts/endor_scan_findings.py`](.github/scripts/endor_scan_findings.py) (`extract_location`): it reads `spec.finding_metadata` (including `file_path` / `line_number`, `security_review_data.code_snippet`, and `custom` Semgrep-style `path` + `start.line`), then `spec.dependency_file_paths` and a summary fallback when needed.

**Validate before pushing (golden flow):**

- Offline (no credentials): `uv run python .github/scripts/validate_pr_comment_flow.py --fixture tests/unit/github_scripts/fixtures/pr_comment_flow_golden.json`
- Live (same API path as CI): `uv run --env-file .env python .github/scripts/validate_pr_comment_flow.py --repo owner/repo --commit-sha <head-sha>`

Use `--fail-if-zero-located` to exit non-zero when findings load but none have an extractable file+line (common when API shape drifts).

Short poll (default ~120s, jittered backoff) waits for a **non-running** ScanResult so the job does not race the platform indexer. On failure or empty data, scripts **fail open** (log and exit 0) so cosmetic steps do not break CI.

## Option B — Pull request review comments (diff-anchored)

Workflow step: `Option B - pull request review comments (dry-run/apply)`

- Script: [`.github/scripts/post_parallel_pr_comments.py`](.github/scripts/post_parallel_pr_comments.py)

Option B submits a **pull request review** whose **`comments`** array holds [**pull request review comments**](https://docs.github.com/en/rest/pulls/comments) on the **unified diff** (`path`, `line`, `side: RIGHT`, optional multiline fields). See [Create a review for a pull request](https://docs.github.com/en/rest/pulls/reviews#create-a-review-for-a-pull-request). Failed batches fall back to per-comment `POST .../pulls/{n}/comments` ([create a review comment](https://docs.github.com/en/rest/pulls/comments#create-a-review-comment-for-a-pull-request)). Finding paths are matched against `GET .../pulls/{n}/files`, and only lines present in the patch hunks are kept so GitHub does not return 422.

Repository variables (optional overrides):

- `ENDOR_ENABLE_INHOUSE_PR_COMMENTS` — omit or `true` to run; set `false` to skip.
- `ENDOR_INHOUSE_PR_COMMENTS_MODE=apply` (default) or `dry-run`

Required secrets and variables:

- `GITHUB_TOKEN` in the job (write perms below)
- `ENDOR_NAMESPACE`, `ENDOR_API` (variable), `ENDOR_API_CREDENTIALS_KEY` / `ENDOR_API_CREDENTIALS_SECRET` (secrets)

Required permissions:

- Workflow job permission `pull-requests: write`

Behavior:

- Paginated fetch of existing pull request review comments to dedupe via hidden HTML markers.
- Skips findings whose path is not in the PR file list (or normalizes path when the file list is empty).
- Optional multi-line anchors when `line_end` is present in metadata (`start_line` / `line` on `RIGHT` side).
- Failed review batches log the **full GitHub error body** then try per-comment fallback.

CLI (optional):

- `--poll-timeout` — seconds to wait for a terminal ScanResult (default `120`).
- `--max-findings` — cap on loaded findings (`Finding.list` or `Finding.get`, default `500`).
- `--max-inline` — max review comments per run (default `30`).
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

- Creates a completed **check run** named **Endor Labs findings** (GitHub Actions app) on the PR head commit with `output.annotations` for findings that have a valid repo-relative `file` + `line`. It is **not** the CodeQL workflow; GitHub may show its annotations near other **Security** / code-scanning style UI, but the failing red check you saw was this run’s **`conclusion`**, not CodeQL registering the step.
- **Check conclusion** defaults to **`success`** (green) so publishing findings does not duplicate a failing gate; annotation rows still use `failure` / `warning` / `notice` for severity. Override with repo variable **`ENDOR_GITHUB_CHECK_CONCLUSION`**: `neutral`, or `from_findings` (fail the check if any finding is HIGH/CRITICAL).
- Invalid anchor paths such as **`.`** (repo root) are skipped so the Checks API does not attach bogus dots to the tree.
- Maps `spec.level` to GitHub annotation levels (`FINDING_LEVEL_CRITICAL` / `HIGH` → `failure`, `MEDIUM` → `warning`, else `notice`).
- Batches annotations (50 per request) with PATCH for follow-up batches.
- Findings without location still appear in the check run **summary** markdown table.

For **SARIF** upload to Code Scanning, use GitHub’s `github/codeql-action/upload-sarif` separately; Option C uses the Checks API only.

## Embedded UX capability matrix

| Capability | Option B (pull request review comments) | Option C (Checks API) |
|---|---|---|
| Native diff snippet on conversation / files | Yes (diff-anchored) | No (Checks / annotations UX) |
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

- Use **Option B** when you want **pull request review comments on the unified diff** (GitHub’s native review-comment UX).
- Use **Option C** when you want the **Checks** tab and structured annotations.
- Running **both** can duplicate signals on the same lines; disable one if that is too noisy.

## Failure modes

- Missing `ENDOR_API_CREDENTIALS_*` or `ENDOR_NAMESPACE` → API fetch logs errors; scripts skip with exit 0.
- No **Project** for the repository URL → skip (ensure `meta.name` on the Project matches `https://github.com/owner/repo.git` or the same without `.git`).
- ScanResult still **RUNNING** until poll timeout → best-effort pick; may yield empty finding UUIDs.
- Missing finding location metadata → Option B posts nothing for those rows; Option C lists them in the check summary only.
- Path not in PR diff / line not commentable → GitHub **422**; batch failure logs response body; per-comment fallback may still skip.
- Option C: missing `checks: write` → apply mode fails; use `dry-run` first.
