---
url: https://docs.endorlabs.com/managing-policies/finding-policies/container-policies/
title: Container policies | Endor Labs Docs
downloaded: 2026-01-16 09:49:12
---

Container policies | Endor Labs Docs



* Type to search...

[Print entire section](/managing-policies/finding-policies/container-policies/_print.html)



# Container policies

Learn about the predefined finding policy templates for containers.

Endor Labs provides the following policies to help assess and improve the security posture of your container images.

| Policy | Description | Severity |
| --- | --- | --- |
| End of Life Container Dependencies | Dependencies marked end of life are no longer maintained or supported. They do not receive security patches, bug fixes, or updates, increasing vulnerability to security threats. Resolution of issues in end of life dependencies must be handled by your organization, which increases the cost of software reuse. Raise findings for end of life container dependencies. | High |

This policy scans container images to detect operating system dependencies or components that have reached end of life (EOL). It is disabled by default and must be enabled in **Finding Policies**.

If a dependency reaches EOL after the initial scan, containers do not need to be re-scanned. The analytics scan automatically detects the change and raises a finding without requiring a rescan.

**Note**

This policy detects end of life status only for OS-level packages and components.

Endor Labs provides the following container image finding policy template to detect if a base image is not permitted by an organization.
See [Finding Policies](..) for details on how to create policies from policy templates.

| Policy template | Description | Severity |
| --- | --- | --- |
| Permit only trusted base images for container images | Raise a finding if a container image uses a base image not approved by the company policy. | Critical |

## Feedback

Was this page helpful?

Yes
No

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

Thanks for the feedback. Write to us at support@endor.ai to tell us more.
