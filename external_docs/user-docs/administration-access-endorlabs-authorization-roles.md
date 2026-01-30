---
url: https://docs.endorlabs.com/administration/access-endorlabs/authorization-roles/
title: Authorization roles | Endor Labs Docs
downloaded: 2026-01-26 10:06:31
---

Authorization roles | Endor Labs Docs



* Type to search...

[Print entire section](/administration/access-endorlabs/authorization-roles/_print.html)



# Authorization roles

Learn how to set permissions using authorization roles.

Authorization roles define the permissions on accessing and using Endor Labs and its features. Each authorization role has a set of associated permissions that determine the extent of access to Endor Labs. Ensure that you assign the right role for the right situation and follow the principle of least privilege (PoLP).

You need to assign an authorization role when you create [authorization policies](../../access-endorlabs/authorization-policies/) and [API keys](../../api-keys/#create-an-api-key).

The following roles are available:

| Role | Description | Intended Use | Access |
| --- | --- | --- | --- |
| Admin | Grants full administrative access to all resources. | For system administrators. | Read and write for all resources. |
| Read-Only | Grants read-only access to all resources. | For users who need to view data but not make changes. | Read-only for all resources. |
| Code Scanner | Grants necessary access to scan a project using endorctl. | For users or CI/CD-based service accounts that run scans. | Read and write for projects, repositories, and findings. Read-only for installations and all other resources. |
| Policy Editor | Grants necessary access to manage policies. | For security teams who define and maintain security policies. | Read and write for policies, and policy templates. Read-only for all other resources. |
| On-Prem Scheduler | Grants necessary access to run [Outpost](../../../deployment/monitoring-scans/outpost/) and to use [monitoring scans](../../../deployment/monitoring-scans/) on supported platforms. | For on-premises deployment service accounts. | Read and write for installations, projects, namespaces, and scan requests. Read-only for all other resources. |

## Feedback

Was this page helpful?

Yes
No

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

Thanks for the feedback. Write to us at support@endor.ai to tell us more.
