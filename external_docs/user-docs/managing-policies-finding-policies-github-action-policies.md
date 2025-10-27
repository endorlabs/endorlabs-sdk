---
url: https://docs.endorlabs.com/managing-policies/finding-policies/github-action-policies/
title: GitHub Action policies | Endor Labs Docs
downloaded: 2025-10-27 12:59:33
---

GitHub Action policies | Endor Labs Docs



* Type to search...
* ---

[Print entire section](/managing-policies/finding-policies/github-action-policies/_print.html)



# GitHub Action policies

Learn about the out-of-the-box finding policies for GitHub Actions.

Endor Labs provides the following out-of-the-box policies that help you assess the security posture of GitHub Actions used in your software delivery process.

* [Policies for Repository Security Posture Management (RSPM) in GitHub](#policies-for-rspm).
* [Policies for evaluating configuration settings in workflow file](#policies-for-assessing-configuration-settings-in-workflow-files).

See [Finding Policies](..) for details on how to **enable**, **disable**, or **edit** out-of-the-box policies.

## Policies for RSPM

| Policy template | Description | Severity |
| --- | --- | --- |
| Default workflow token permission should be read only | Set the default GitHub Action workflow token permission to read-only. It is highly recommended to adhere to the principle of least privilege for generating workflow tokens and enforce the workflow authors to explicitly specify the permissions they require. | High |
| Restrict GitHub Actions to selected repositories | Selectively enabling GitHub Actions ensures better resource management and mitigates security risks. Raise findings for organizations where GitHub Actions are enabled for all repositories. | Medium |
| Restrict runner groups to specific repositories | It is recommended to limit the runner groups to specific repositories. Malicious users within an organization can create repositories with workflows designed to exploit vulnerabilities. If such repositories are allowed access to the organization’s hosted runners, they could trigger automated tasks and disrupt your network. | High |
| Restrict the use of runner groups for public repositories | It is recommended to allow only workflows from private or internal repositories to run on GitHub hosted runners. This prevents security risks posed by malicious actors who could exploit workflows from public repositories to gain unauthorized access to your private network. | High |
| Workflows should not be allowed to create and approve pull requests | Do not configure the GitHub Action workflows to create and approve pull requests. Code review is a crucial part of the software development process and must be performed by human reviewers. | High |

## Policies for assessing configuration settings in workflow files

| Policy template | Description | Severity |
| --- | --- | --- |
| Non-OIDC cloud authentication detected in GitHub workflow file | The GitHub Action workflow file authenticates to the cloud without using OIDC. Do not use hardcoded secrets to authenticate with a cloud provider. OpenID Connect (OIDC) is recommended, which provides a short-lived access token directly from the cloud provider. | High |
| Script injection detection in GitHub workflow file | The workflow file contains a bash injection script with an expression that could include user input. As a best practice, assign the value of untrusted input expressions to an intermediate environment variable to mitigate code and command injection vulnerabilities in GitHub workflows. | High |
| Secrets object detected in GitHub workflow file | This GitHub Actions job has access to all repository and organization secrets. As a best practice, avoid using `${{ toJSON(secrets) }}` or `${{ secrets[...] }}` and consider using GitHub Actions environment variables accessing individual secrets to restrict the secrets available to the job. | High |
| Untrusted code checkout detected in workflow file | This repository workflow uses ‘pull\_request\_target’ with an explicit PR checkout and executes build commands like ’npm install’ or ’npm build’. This is risky because the build scripts and referenced packages are controlled by the PR author. | High |

## Feedback

Was this page helpful?

Yes
No

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

Thanks for the feedback. Write to us at support@endor.ai to tell us more.
