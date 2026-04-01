# GitHub workflow templates

This directory used to hold `pr-findings-summary.tmpl`, which CI synced into Endor `PRCommentConfig`. That flow was removed: in-repo PR feedback uses the Endor API plus [`.github/scripts/post_parallel_pr_comments.py`](../scripts/post_parallel_pr_comments.py) / [`post_github_check_run.py`](../scripts/post_github_check_run.py).

To restore **Endor’s default** PR comment template on your tenant after a custom template was applied, save the stock template text to a **gitignored** path such as `.tmp/pr-findings-summary-default-from-endor.tmpl` and run:

```bash
uv run python .github/scripts/sync_pr_comment_template.py \
  --namespace "$ENDOR_NAMESPACE" \
  --name github-pr-comments-template \
  --template-path .tmp/pr-findings-summary-default-from-endor.tmpl \
  --platform-type PLATFORM_SOURCE_GITHUB
```

See [docs/guides/pr-comment-config-and-parallel-comments.md](../../docs/guides/pr-comment-config-and-parallel-comments.md).
