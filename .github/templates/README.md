# GitHub workflow templates

This directory used to hold `pr-findings-summary.tmpl`, which CI synced into Endor `PRCommentConfig`. That flow was removed: in-repo PR feedback uses the Endor API and [`.github/scripts/post_parallel_pr_comments.py`](../scripts/post_parallel_pr_comments.py) to post pull request review comments.

To restore **Endor's default** PR comment template on your tenant after a custom template was applied, save the stock template text to a **gitignored** path such as `.endorlabs-context/workspace/sessions/agent/exports/pr-findings-summary-default-from-endor.tmpl` and run:

```bash
uv run python .github/scripts/sync_pr_comment_template.py \
  --namespace "$ENDOR_NAMESPACE" \
  --name github-pr-comments-template \
  --template-path .endorlabs-context/workspace/sessions/agent/exports/pr-findings-summary-default-from-endor.tmpl \
  --platform-type PLATFORM_SOURCE_GITHUB
```

See [docs/guides/pr-comment-config-and-parallel-comments.md](../../docs/guides/pr-comment-config-and-parallel-comments.md).
