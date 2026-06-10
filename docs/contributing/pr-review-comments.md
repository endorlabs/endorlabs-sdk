# PR review comments from Endor findings

This repo's CI **does not** post custom pull request review comments. The Endor Labs GitHub Action steps in [`ci-pr-main.yml`](../../.github/workflows/ci-pr-main.yml) set **`enable_pr_comments: false`**.

For PR feedback, use one of:

1. **Platform-managed comments** — set `enable_pr_comments: true` on the [Endor Labs GitHub Action](https://github.com/endorlabs/github-action) and configure tenant **`PRCommentConfig`** (Go templates evaluated server-side).
2. **Manual template sync** — [`.github/scripts/sync_pr_comment_template.py`](../../.github/scripts/sync_pr_comment_template.py) updates `PRCommentConfig` from a local template file (see [`.github/templates/README.md`](../../.github/templates/README.md)).

## Historical note

An in-repo CI path (`post_parallel_pr_comments.py`, API fetch + 300s ScanResult poll) was removed. It duplicated platform behavior, raced scan completion despite polling, and required extra secrets (`ENDOR_API_CREDENTIALS_*`) plus `pull-requests: write` on the security job.

**Deprecated repository variables (safe to remove if set):** `ENDOR_ENABLE_INHOUSE_PR_COMMENTS`, `ENDOR_INHOUSE_PR_COMMENTS_MODE`, `ENDOR_ENABLE_GITHUB_CHECK_ANNOTATIONS`, `ENDOR_GITHUB_CHECK_MODE`, `ENDOR_GITHUB_CHECK_CONCLUSION`.

## Field crosswalk

[pr-review-comment-matrix.md](pr-review-comment-matrix.md) documents how Endor `Finding` fields map to GitHub review comment payloads (conceptual reference for custom tooling).

## SARIF / Code Scanning

For GitHub Code Scanning uploads, use `github/codeql-action/upload-sarif` separately; Endor PR comments and SARIF are independent paths.
