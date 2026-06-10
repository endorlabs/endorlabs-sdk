# PR comment templates (manual)

This directory used to hold `pr-findings-summary.tmpl`, which CI synced into Endor `PRCommentConfig`. That flow was removed.

To restore **Endor's default** PR comment template on your tenant after a custom template was applied, save the stock template text to a **gitignored** path such as `.endorlabs-context/workspace/sessions/agent/exports/pr-findings-summary-default-from-endor.tmpl` and run:

```bash
uv run python .github/scripts/sync_pr_comment_template.py \
  --name github-pr-comments-template \
  --platform-type PLATFORM_SOURCE_GITHUB
```

See [docs/contributing/pr-review-comments.md](../../docs/contributing/pr-review-comments.md).
