---
url: https://docs.endorlabs.com/managing-policies/finding-policies/managing-scm-configuration/
title: RSPM policies | Endor Labs Docs
downloaded: 2025-10-23 23:26:32
---

RSPM policies | Endor Labs Docs



* Type to search...
* ---

[Print entire section](/managing-policies/finding-policies/managing-scm-configuration/_print.html)



# RSPM policies

Learn about the out-of-the-box finding policies for repository security posture management (RSPM).

Strong information security practices are necessary to secure your open source code used in your development and delivery infrastructure.

## Policies for repository security posture management

Endor Labs comes with the following out-of-the-box policies that help you determine the effectiveness of your security practices.
See [Finding Policies](..) for details on how to **enable**, **disable**, or **edit** out-of-the-box policies.

| Policy | Description | Severity |
| --- | --- | --- |
| Archive inactive repositories | Repositories that are not actively maintained are vulnerable to security breaches. Archiving such repositories helps maintain a cleaner and more organized GitHub environment. Archiving ensures repositories become read-only, thus preventing unauthorized modifications. Raise findings for repositories that have been inactive beyond the duration specified by the user, defaulting to 6 months if not specified. | High |
| At least two administrators should be configured for a repository | Having fewer than two administrators for a repository may cause problems when the administrator is unavailable. A minimum of two administrators must be configured to meet this requirement. | Medium |
| Authorization to push or merge to protected branches should be limited | Limiting the authorization to push or merge code to protected branches is a best practice in software development workflows. By restricting access to protected branches, you maintain control over code changes and ensure that only authorized individuals can make modifications. Raises findings for repositories that do not enforce rules around merging code to protected branches. | Medium |
| Branch protection rules should be enforced on administrators | Enforcing branch protection rules on administrators is a best practice in software development workflows. By applying branch protection rules to administrators, you ensure that even privileged individuals follow the established processes and adhere to the same standards as other team members. Raises findings for repositories that do not enforce branch protection rules. | Medium |
| Branches should be up-to-date before merging | Ensuring that branches are up-to-date before merging is a best practice in software development. It avoids conflicts, helps in the early detection of issues, and maintains code coherence. Raise findings for repositories that do not enforce rules on branches to be up-to-date before merging. | Medium |
| Code owner review is required when a change affects owned code | Code owner review is a practice in software development where specific individuals or teams are designated as code owners for certain parts of the codebase. When a change is proposed that affects code owned by a particular individual or team, a code owner review is required before the change can be merged into the main codebase. | Low |
| Code owner should be configured for sensitive code | Code owner review is a best practice in software development workflows where specific individuals or teams are designated as code owners for certain parts of the codebase. When a change is proposed that affects code owned by a particular individual or team, a code owner review is required before the change can be merged into the main codebase. Raises findings for repositories that do not enforce code owner reviews. | Low |
| Comments should be resolved before merging | Resolving comments ensures that all feedback, questions, and issues raised during the code review process have been addressed satisfactorily before the code is considered ready for integration. Raises findings for repositories that do not resolve comments before merging. | Low |
| Commits should be signed for new changes | Requiring commits to be signed for new changes is a best practice in software development workflows. Commit signing involves using digital signatures to verify the authenticity and integrity of the commit. Raises findings for repositories that do not enforce signed commits. | Medium |
| Contributors should not approve their own changes | Robust code reviews are essential and contributors should not approve their own changes in a collaborative software development environment. Raises findings for repositories that do not enforce code reviews. | High |
| Default member permissions should be restricted | As a best practice, set the base permissions for members in an organization to either “read” or “none” on GitHub. Restricting member permissions controls the access over repositories and prevents misuse. | Medium |
| Dismissing Code Change Reviews should be restricted | Restricting the ability to dismiss code change reviews is a best practice in software development workflows. Dismissing code change reviews should be limited to specific cases and authorized individuals to ensure accountability, maintain code quality, and promote a collaborative and transparent review process. Raises findings for repositories that do not enforce rules around dismissing code reviews. | Medium |
| Ensure branch protection is enforced for the default branch | Branch protection rules allow you to set controls over your software development processes. The default branch for this repository has no branch protection rules and should be protected. | High |
| Force pushing code to protected branches should be restricted | Restricting the ability to force push code to protected branches is a best practice in software development workflows. Restricting this action helps maintain code integrity, accountability, and collaboration. Raises findings for repositories that do not enforce rules around pushing code to protected branches. | Medium |
| Linear commit history should be required | Linear commit history indicates a chronological sequence of commits made to a code repository. It provides a clear and chronological view of the code changes made to a repository, aiding in code navigation, collaboration, and bug tracking. Raises findings for repositories that do not have linear commit history. | Low |
| Missing Source Code | If you cannot audit the source code associated with a software component, there is limited visibility that can result in operational and security risks. Raises findings for packages with missing source code. | Low |
| Multi-Factor Authentication (MFA) should be required for external contributors | Multi-Factor Authentication adds an additional layer of security to access accounts or systems and prevents unauthorized access to code repositories. Raises findings for repositories that do not enforce MFA for external contributors. | High |
| Multi-Factor Authentication (MFA) should be required for organization members | Multi-Factor Authentication adds an additional layer of security to access accounts or systems and prevents unauthorized access to code repositories. Raises findings for repositories that do not enforce MFA for members in their organization. | High |
| Organization webhooks must be configured with a secret | The authenticity of a webhook payload cannot be verified when it is set up without a secret key. Anyone could send forged payloads to the organization’s webhook endpoints leading to security issues. | Medium |
| Organization webhooks should use HTTPS | A webhook URL is used to send notifications, along with a payload, to designated internet endpoints. Given that the payload contains sensitive information, all webhooks must be directed toward endpoints secured by HTTPS. | Medium |
| Organization webhooks should use SSL verification | When Organization webhook SSL verification is disabled, GitHub is explicitly instructed not to verify the identity of the remote server it is sending information to. This configuration bypasses standard security controls in the HTTP protocol, which are designed to prevent attackers from executing man-in-the-middle attacks. | Low |
| Organizations should be verified | The Organization Verified badge on GitHub is a visual indicator that signifies an organization’s authenticity and official status. It helps users identify legitimate and trusted organizations on the GitHub platform. Raise findings for organizations that are not verified. | Low |
| Organizations should have fewer than three owners | Organization administrators have the highest level of permissions, including the ability to add/remove collaborators, create or delete repositories, change branch protection policy, and convert to a publicly accessible repository. Due to the permissive access granted to an organization administrator, it is highly recommended to have at most three administrator accounts. | Medium |
| Private repositories should not permit forking | Allowing forking in repositories within an organization can compromise data security, potentially exposing sensitive information to unauthorized parties. It exposes vulnerabilities in the codebase, making it more susceptible to exploitation. Additionally, tracking changes across multiple forks becomes complicated. | Low |
| Protected Branch Deletion should be blocked | Protecting branch deletion, especially for critical branches, is a best practice in software development workflows. Raises findings for repositories that do not enforce rules around protected branch deletion. | Medium |
| Repository webhooks must be configured with a secret | The authenticity of a webhook payload cannot be verified when it is set up without a secret key. Anyone could send forged payloads to the repository’s webhook endpoints leading to security issues. | Medium |
| Repository webhooks should use HTTPS | A webhook URL is used to send notifications, along with a payload, to designated internet endpoints. Given that the payload contains sensitive information, all webhooks must be directed toward endpoints secured by HTTPS. | Medium |
| Repository webhooks should use SSL verification | When repository webhook SSL verification is disabled, GitHub is explicitly instructed not to verify the identity of the remote server it is sending information to. This configuration bypasses standard security controls in the HTTP protocol, which are designed to prevent attackers from executing man-in-the-middle attacks. | Low |
| Require a SECURITY.md file | A SECURITY.md outlines security practices, reporting procedures, and guidelines for handling security-related issues within a project. It is included in the root directory of software repositories. Raise findings for repositories that do not include a SECURITY.md file. | Low |
| Restrict general action permissions to organization members | Setting general action permissions for the organization to “all” can pose security risks by allowing unrestricted access to repositories to use GitHub Actions. This ensures that actions within the organization are confined to local resources, mitigating the risk of unauthorized access or unintended actions on external resources. | High |
| Restrict the creation of repositories to trusted members | Limiting repository creation to trusted users and teams is advisable for maintaining organizational structure, reducing tracking workload, preventing impersonation, and avoiding overloading the version-control system. | Medium |
| Stale approvals should be dismissed | To prevent malicious code from being introduced into a codebase, it is important to have a robust approval process for code changes. When changes are made to a proposal, outdated approvals must be declined, and previously accepted code changes must be re-evaluated. The approval process should involve multiple reviewers, and organizations should also consider implementing automated code analysis and security testing. | Medium |
| Status checks should pass before merging new code | Ensuring that status checks pass before merging new code is a best practice in software development workflows. Status checks serve as automated checks or validations that assess the quality, integrity, and readiness of the code changes before they are merged into the main codebase. Raises findings for repositories that do not enforce status checks before merging new code. | Medium |
| Two informed reviews should be required for code changes | Requiring two informed reviews for code changes is a best practice in software development. It helps ensure that code changes are thoroughly examined, promotes collaboration, and increases the overall quality of the codebase. Raises findings for repositories that do not enforce two reviews for code changes. | Medium |
| Workflows should not be allowed to create and approve pull requests | Allowing workflows to create and approve pull requests within an organization can enable users to evade code-review protocols. Attackers could exploit this by establishing workflows that autonomously approve their pull requests and merge them discreetly. Consequently, they can introduce potentially harmful code into the production system. | High |

## Feedback

Was this page helpful?

Yes
No

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

Thanks for the feedback. Write to us at support@endor.ai to tell us more.
