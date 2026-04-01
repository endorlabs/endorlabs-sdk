# PR Comment Config and Parallel Comments

This guide covers complementary PR feedback paths in CI:

- **Option A:** Endor-managed PR comments using `PRCommentConfig` template sync.
- **Option B:** In-house issue comments and optional inline review comments from scan metadata.
- **Option C:** GitHub **Checks API** check runs with **annotations** (Checks tab / file annotations), from the same scan artifact.

In [`.github/workflows/ci-pr-main.yml`](.github/workflows/ci-pr-main.yml) (`endorlabs-security-scan` job), **Options A–C default to enabled** on pull requests (`ENDOR_ENABLE_*` falls back to `true`). Set a repository variable to `false` to turn a path off. **Option B** and **Option C** modes default to **`dry-run`** until you set `ENDOR_INHOUSE_PR_COMMENTS_MODE` / `ENDOR_GITHUB_CHECK_MODE` to `apply`.

## Option A - Template sync via `PRCommentConfig`

Workflow step: `Option A - sync Endor PR comment template config`

- Script: `.github/scripts/sync_pr_comment_template.py`
- Template file: `.github/templates/pr-findings-summary.tmpl`
- Resource: `Client.PRCommentConfig` (PascalCase, endorctl semantics)

Repository variables (optional overrides):

- `ENDOR_ENABLE_TEMPLATE_SYNC` — omit or `true` to run; set `false` to skip.
- `ENDOR_NAMESPACE=<tenant.namespace>`
- Optional: `ENDOR_API=<api base URL>`

Required secrets:

- `ENDOR_API_CREDENTIALS_KEY`
- `ENDOR_API_CREDENTIALS_SECRET`

Behavior:

- Creates `github-pr-comments-template` if it does not exist.
- Updates the existing resource when template/platform/propagate drift.
- Emits status through workflow logs and `GITHUB_OUTPUT` (`template_sync_status`, `template_sync_reason`).

Template syntax (Go `text/template` on `GithubCommentData`): use **Go/protobuf struct field names**, not JSON snake_case — e.g. `.CommentHeader.Value`, `.FindingsMap`, `.ApiEndpoint.Value`, `.CommentFooter.Value`, and on each finding `.Spec.Level` with `enumToString`. See `.endorlabs-context/docs/setup-deployment-scm-integrations-gitlab-app-gitlab-mr-scan.md` (default MR template) for the same data shape. Keep the **CommentHeader** block at the top as in the stock templates; Endor uses it to identify generated comments.

## Option B - In-house parallel GitHub comments

Workflow step: `Option B - in-house parallel PR comments (dry-run/apply)`

- Script: `.github/scripts/post_parallel_pr_comments.py`
- Scan artifact input: `.endorlabs-artifacts/scan-output.json`

Repository variables (optional overrides):

- `ENDOR_ENABLE_INHOUSE_PR_COMMENTS` — omit or `true` to run; set `false` to skip.
- `ENDOR_INHOUSE_PR_COMMENTS_MODE=dry-run` (default) or `apply`

Required permissions:

- Workflow job permission `pull-requests: write`
- `GITHUB_TOKEN` available in workflow environment

Behavior:

- Extracts findings from scan JSON recursively.
- Posts/updates one deterministic rollup summary comment (`<!-- endorlabs-inhouse-summary -->` marker) with deep links.
- Attempts line comments for findings with precise `file` + `line` metadata and includes direct GitHub blob links.
- Uses deterministic per-finding markers to avoid duplicate line comments on reruns.
- Gracefully skips line comments when diff hunks are stale or not commentable.

Repository variables:

- `ENDOR_INHOUSE_POST_REVIEW_COMMENTS` — `true` (default) or `false`. Set to `false` when using Option C to avoid duplicate inline markers (rollup issue comment still runs when Option B is enabled).

## Option C - GitHub Check Run annotations

Workflow step: `Option C - GitHub Check Run annotations (dry-run/apply)`

- Script: `.github/scripts/post_github_check_run.py`
- Scan artifact: `.endorlabs-artifacts/scan-output.json` (same as Option B)
- Shared extraction: `.github/scripts/endor_scan_findings.py`

Repository variables (optional overrides):

- `ENDOR_ENABLE_GITHUB_CHECK_ANNOTATIONS` — omit or `true` to run; set `false` to skip.
- `ENDOR_GITHUB_CHECK_MODE=dry-run` (default) or `apply`

Required permissions:

- Workflow job permissions `checks: write` (in addition to `pull-requests: write` if Option B is enabled) and `GITHUB_TOKEN`.

Behavior:

- Creates a completed **check run** on the PR head commit with `output.annotations` for findings that have `file` + `line` in metadata.
- Maps `spec.level` to GitHub annotation levels (`FINDING_LEVEL_CRITICAL` / `HIGH` → `failure`, `MEDIUM` → `warning`, else `notice`).
- Sends annotations in batches of up to **50** per REST request (additional batches use **Update check run**).
- Findings without location still appear in the check run **summary** markdown table.
- For **SARIF** upload to Code Scanning (alternative native UX), use GitHub’s official `github/codeql-action/upload-sarif` after generating SARIF; this repo’s Option C uses the Checks API only.

## Embedded UX capability matrix

GitHub PR comments do not expose arbitrary widget or iframe embed APIs. The practical “embedded” patterns are:

- **Option A (template):** Markdown **fenced code blocks** for snippets using Endor’s template helpers `getCustomCodeSnippet` and `fixBackticks` (see `.endorlabs-context/docs/scan-pr-scans-pr-comments.md`). This is the platform’s documented way to render Custom metadata snippets safely in comment bodies.
- **Option B (script):** GitHub **REST** payloads with `path`, `line`, `side`, and `commit_id` for **inline review comments** on the diff, built from `file` / `line` in finding metadata (see `.github/scripts/post_parallel_pr_comments.py`).
- **Option C (script):** GitHub **Checks API** (`POST`/`PATCH` check-runs) with `output.annotations` (see `.github/scripts/post_github_check_run.py`).

| Capability | Option A (`PRCommentConfig` template) | Option B (repo-native script) | Option C (Checks API) |
|---|---|---|---|
| Markdown links in comment body | Supported | Supported | In check summary text |
| Snippet “embed” as fenced code in summary | Supported via `getCustomCodeSnippet` + `fixBackticks` | Optional one-line snippet in inline comment body when metadata includes text | Message text per annotation |
| File+line deep links in markdown | Supported via `getFindingURL` / `getCustomLocation`; no GitHub blob URL in template root | Supported via constructed blob links from repo + commit SHA | N/A (annotations anchor to path/lines) |
| Inline review comments in PR diff | Platform-dependent scanner behavior | Supported via GitHub review comments API | Not used (use annotations instead) |
| Checks tab / structured annotations | Not supported | Not supported | Supported |
| Deterministic dedupe across reruns | Limited to scanner behavior | Supported via marker keys | New check run per workflow run |
| Arbitrary widget/iframe embed in PR comment | Not supported | Not supported | Not supported |

## PRCommentConfig gap analysis

`PRCommentConfig` currently exposes only:

- `spec.platform_type`
- `spec.template.findings_summary_template`

Practical gaps for embedded UX:

- No dedicated structured fields for `file`, `line`, `line_end`, or precomputed deep-link URLs **in the template root**; deep links in the threaded summary rely on Endor URLs from helpers such as `getFindingURL` unless the platform extends the data model.
- No controls for line-comment placement behavior (path/line anchoring strategy) from this resource alone.
- No support for custom GitHub UI widgets/cards/iframes; output is still markdown/text rendered by GitHub comments.
- No native dedupe key fields for custom in-house comment update semantics.

Recommended fallback patterns:

- Use Option A for consistent markdown summary formatting and link-heavy output.
- Use Option B for rollup issue comments and optional threaded inline review comments.
- Use Option C for GitHub-native **Checks** UX (annotations on files/lines). Prefer `ENDOR_INHOUSE_POST_REVIEW_COMMENTS=false` when Option B and C are both enabled to reduce duplicate inline surfaces.
- Run A + B, A + C, or all three as needed; align variables so comments and checks do not duplicate the same finding on the diff.

## Choosing Option A vs Option B vs Option C

- Use **Option A** when you want Endor-native PR comments and template-controlled formatting.
- Use **Option B** when you want issue-thread rollup and optional review comments with deterministic markers.
- Use **Option C** when you want the **Checks** tab and API-driven annotations without maintaining raw REST upload code for SARIF (SARIF remains an optional separate path via `upload-sarif`).

## Failure modes

- Missing template credentials (`ENDOR_API_CREDENTIALS_*`) -> Option A step should be disabled or will fail auth.
- Invalid Go template syntax/content -> Option A create/update returns API validation error.
- Missing finding location metadata (`file`, `line`) -> Option B falls back to rollup only.
- Scan artifact exists but is **not valid JSON** (e.g. table-only log, truncated write) -> Option B/C log and **skip** (exit 0) so the job does not fail for cosmetic steps.
- Outdated PR diff/hunks -> line comment POST may fail; script logs and continues.
- Missing write permissions -> Option B comment writes fail; keep `dry-run` for verification.
- Option C: `checks: write` missing or denied -> check run creation fails; use `dry-run` first.
- Option C: GitHub may cap annotations per request (batching implemented); very large result sets may prefer SARIF + `upload-sarif` instead.
