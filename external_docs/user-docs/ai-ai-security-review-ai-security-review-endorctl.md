---
url: https://docs.endorlabs.com/ai/ai-security-review/ai-security-review-endorctl/
title: Set up AI security code review with endorctl | Endor Labs Docs
downloaded: 2026-02-03 00:50:07
---

Set up AI security code review with endorctl | Endor Labs Docs



* Type to search...

[Print entire section](/ai/ai-security-review/ai-security-review-endorctl/_print.html)



# Set up AI security code review with endorctl

Use endorctl to run AI security code review with GitHub environment variables.

You can use AI security code review with endorctl and GitHub environment variables without requiring the GitHub App. This approach allows you to integrate AI security code review into your local development workflows. You can use this approach only if you have GitHub as your source control management system.

Complete the following tasks to set up AI security code review with endorctl:

* [Complete the prerequisites to use AI security code review with endorctl.](#prerequisites-to-use-ai-security-code-review-with-endorctl)
* [Set up the environment variables required to run endorctl for AI security code review.](#set-up-environment-variables)
* [Install and authenticate endorctl, build your project, and run a scan.](../../../getting-started/quickstart/quickstart-local-system) Scanning the repository creates the project in Endor Labs that you can use to configure the scan profile.
* Configure a [scan profile](../ai-security-review-settings/#configure-scan-profile-for-ai-security-review) for AI security code review.
* Enable the [security review finding policy](../ai-security-review-settings#enable-finding-policy-for-ai-security-review).
* Configure an [action policy](../ai-security-review-settings#configure-action-policy-for-pull-request-comments) if you want to get comments on your GitHub pull request with the details of the AI security code review.
* [Run scans for AI security code review.](#pull-request-scan-with-ai-security-code-review)
* [View results of the AI security code review.](../ai-security-review-results/)

## Prerequisites to use AI security code review with endorctl

Ensure that the following prerequisites are met before using AI security code review with endorctl:

* An active Endor Labs subscription with Endor Code Pro license.
* Access to configure scan profiles and policies
* Code Segment Embeddings and LLM Processing enabled in Data Privacy settings
* A GitHub token with appropriate permissions.

### Enable Code Segment Embeddings and LLM Processing

Perform the following steps to enable code segment embeddings and LLM processing:

1. Select **Manage** > **Settings** from the left sidebar.
2. Select **SYSTEM SETTINGS** > **Data Privacy**.

   ![Enable Code Segment Embeddings and LLM Processing](/images/enable_embeddings.png)
3. Select **Code Segment Embeddings and LLM Processing**.
4. Click **Save Data Privacy Settings**.

### Verify license and feature access

Perform the following steps to verify your license and feature access:

1. Select **Settings** > **License** from the left sidebar.
2. Verify that you have **Security Review** in **Products** and **Features**.

## Set up environment variables

Configure the following environment variables for GitHub integration:

```
# Required: GitHub token with repo access
export GITHUB_TOKEN=<your-github-token>

# Required: Endor Labs authentication
export ENDOR_API_CREDENTIALS_KEY=<your-api-key>
export ENDOR_API_CREDENTIALS_SECRET=<your-api-secret>
export ENDOR_NAMESPACE=<your-namespace>
```

## Pull request scan with AI security code review

To scan a pull request with AI security code review, fetch the pull request branch locally and checkout the branch.

```
git fetch origin pull/<PR_NUMBER>/head:pr-<PR_NUMBER>
git checkout pr-<PR_NUMBER>
```

For example, to scan pull request 12, you need to run the following commands.

```
git fetch origin pull/12/head:pr-12
git checkout pr-12
```

After you have fetched and checked out the pull request branch, you can run the following command to scan the pull request with AI security code review.

```
endorctl scan \
  -n <namespace> \
  --pr \
  --security-review \
  --scm-pr-id <PR_NUMBER> \
  --github-token $GITHUB_TOKEN \
  --enable-pr-comments
```

The following table describes the flags used in the command.

| Flag | Mandatory | Description |
| --- | --- | --- |
| `-n <namespace>` | ✗ | Your Endor Labs namespace. If you do not specify a namespace, the command uses the default namespace. |
| `--pr` | ✓ | Indicates that this is a pull request scan. |
| `--security-review` | ✓ | Enables AI security code review. |
| `--scm-pr-id <PR_NUMBER>` | ✓ | The GitHub pull request number that you want to scan. Note: You can continue to use `--github-pr-id` flag, but it will be deprecated and removed in the future. |
| `--github-token $GITHUB_TOKEN` | ✓ | GitHub token for authentication. You need to specify this flag if you did not set up the `GITHUB_TOKEN` environment variable. |
| `--enable-pr-comments` | ✗ | Enables comments on the GitHub pull request. Enable this flag if you want to get comments on your GitHub pull request with the details of the AI security code review. You must enable the action policy for pull request comments. |

## Feedback

Was this page helpful?

Yes
No

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

Thanks for the feedback. Write to us at support@endor.ai to tell us more.
