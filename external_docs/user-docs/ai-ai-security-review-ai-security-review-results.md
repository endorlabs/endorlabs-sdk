---
url: https://docs.endorlabs.com/ai/ai-security-review/ai-security-review-results/
title: View AI security code review results | Endor Labs Docs
downloaded: 2025-10-27 12:59:22
---

View AI security code review results | Endor Labs Docs



* Type to search...
* ---

[Print entire section](/ai/ai-security-review/ai-security-review-results/_print.html)



# View AI security code review results

Learn how to view the AI security code review results.

You can view the AI security code review results in the Endor Labs UI. You can also enable PR comments to get a comment on your GitHub PR with the details of the AI security code review. If you use merge queues, Endor Labs provides security review for the PRs until they are added to the merge queue. Endor Labs does a final security review on the merged commit SHA to the default branch.

## View AI security code review results in Endor Labs UI

1. Select **Projects** from the left sidebar.
2. Select the project for which you want to view the AI security code review results.
3. Select **Security Review**.

   ![Security Review](../../../images/ai-security-review-results.png)

   You can view the AI security code review results for all the pull requests raised in the project. You can also search for a specific pull request and view the results.

   You can filter the results by the type of the security issues, the severity of the security issues, the author of the PR, the approvers, and the creation time of the PR. You can select advanced to enter a search query to filter the results.

   For example, you can filter the results to show only the critical security issues that are part of unmerged pull requests:

   `(spec.level in ["SECURITY_REVIEW_LEVEL_CRITICAL"] and spec.repository_pull_request_spec.merged != true)`
4. Click on a pull request to view the detailed report.

   ![Security Review Report](../../../images/ai-security-review-report.png)

   The report appears in the right sidebar. You can view the security analysis of the PR and the list of security risks along with their severities.

   You can click links against the security analysis to go directly to the lines of code that has the security risk.

   You can also click the links to view the pull request and the specific commit that introduced the security risk.
5. Select the arrow next to a security risk to view the details of the security risk.

   ![Security Risk Details](../../../images/ai-security-review-risk-details.png)

   You can view the analysis of the security risk, the code snippet associated with the risk, and the details of the pull request.

## Security review GitHub pull request comment

If you configure the action policy to get comments on your GitHub pull requests, Endor Labs comments on the pull request with the security analysis.

You can view an example pull request with AI security code review comment [here](https://github.com/endorlabs-demos/open-weather-app/pull/8).

![Security Review GitHub pull request comment](../../../images/ai-security-review-github-pr-comment.png)

## Feedback

Was this page helpful?

Yes
No

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

Thanks for the feedback. Write to us at support@endor.ai to tell us more.
