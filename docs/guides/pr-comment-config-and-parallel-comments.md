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
- Emits status through workflow logs and `GITHUB_OUTPUT` (`template_sync_status`, `template_sync_reason`).

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
- Posts/updates one deterministic rollup summary comment (`<!-- endorlabs-inhouse-summary -->` marker) with deep links.
- Attempts line comments for findings with precise `file` + `line` metadata and includes direct GitHub blob links.
- Uses deterministic per-finding markers to avoid duplicate line comments on reruns.
- Gracefully skips line comments when diff hunks are stale or not commentable.

## Embedded UX capability matrix

GitHub PR comments do not expose arbitrary widget or iframe embed APIs. The practical “embedded” patterns are:

- **Option A (template):** Markdown **fenced code blocks** for snippets using Endor’s template helpers `getCustomCodeSnippet` and `fixBackticks` (see `.endorlabs-context/docs/scan-pr-scans-pr-comments.md`). This is the platform’s documented way to render Custom metadata snippets safely in comment bodies.
- **Option B (script):** GitHub **REST** payloads with `path`, `line`, `side`, and `commit_id` for **inline review comments** on the diff, built from `file` / `line` in finding metadata (see `.github/scripts/post_parallel_pr_comments.py`).

| Capability | Option A (`PRCommentConfig` template) | Option B (repo-native script) |
|---|---|---|
| Markdown links in comment body | Supported | Supported |
| Snippet “embed” as fenced code in summary | Supported via `getCustomCodeSnippet` + `fixBackticks` | Optional one-line snippet in inline comment body when metadata includes text |
| File+line deep links in markdown | Supported via `getFindingURL` / `getCustomLocation`; no GitHub blob URL in template root | Supported via constructed blob links from repo + commit SHA |
| Inline review comments in PR diff | Platform-dependent scanner behavior | Supported via GitHub review comments API |
| Deterministic dedupe across reruns | Limited to scanner behavior | Supported via marker keys |
| Arbitrary widget/iframe embed in PR comment | Not supported | Not supported |

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
- Use Option B for deterministic inline anchors and blob links when location metadata is present.
- Run both together for best UX parity with GitHub constraints.

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
