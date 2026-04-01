# PR Comment Config and Parallel Comments

This guide covers two complementary PR-comment paths in CI:

- Option A: Endor-managed PR comments using `PRCommentConfig` template sync.
- Option B: In-house parallel PR comments based on scan finding location metadata.

## Option A - Template sync via `PRCommentConfig`

Workflow step: `Option A - sync Endor PR comment template config`

- Script: `.github/scripts/sync_pr_comment_template.py`
- Template file: `.github/templates/pr-findings-summary.tmpl`
- Resource: `Client.PRCommentConfig` (PascalCase, endorctl semantics)

Enable in repository variables:

- `ENDOR_ENABLE_TEMPLATE_SYNC=true`
- `ENDOR_NAMESPACE=<tenant.namespace>`
- Optional: `ENDOR_API=<api base URL>`

Required secrets:

- `ENDOR_API_CREDENTIALS_KEY`
- `ENDOR_API_CREDENTIALS_SECRET`

Behavior:

- Creates `github-pr-comments-template` if it does not exist.
- Updates the existing resource when template/platform/propagate drift.
- Emits status through workflow logs and `GITHUB_OUTPUT`.

## Option B - In-house parallel GitHub comments

Workflow step: `Option B - in-house parallel PR comments (dry-run/apply)`

- Script: `.github/scripts/post_parallel_pr_comments.py`
- Scan artifact input: `.endorlabs-artifacts/scan-output.json`

Enable in repository variables:

- `ENDOR_ENABLE_INHOUSE_PR_COMMENTS=true`
- `ENDOR_INHOUSE_PR_COMMENTS_MODE=dry-run` or `apply`

Required permissions:

- Workflow job permission `pull-requests: write`
- `GITHUB_TOKEN` available in workflow environment

Behavior:

- Extracts findings from scan JSON recursively.
- Posts/updates one deterministic rollup summary comment (`<!-- endorlabs-inhouse-summary -->` marker).
- Attempts line comments for findings with precise `file` + `line` metadata.
- Uses deterministic per-finding markers to avoid duplicate line comments on reruns.
- Gracefully skips line comments when diff hunks are stale or not commentable.

## Choosing Option A vs Option B

- Use **Option A** when you want to stay on Endor-native PR comments and control the summary format.
- Use **Option B** when you need a parallel comment stream with custom dedupe/reporting behavior.
- You can run both: Option A for native comments, Option B for supplemental in-house annotations.

## Failure modes

- Missing template credentials (`ENDOR_API_CREDENTIALS_*`) -> Option A step should be disabled or will fail auth.
- Invalid Go template syntax/content -> Option A create/update returns API validation error.
- Missing finding location metadata (`file`, `line`) -> Option B falls back to rollup only.
- Outdated PR diff/hunks -> line comment POST may fail; script logs and continues.
- Missing write permissions -> Option B comment writes fail; keep `dry-run` for verification.
