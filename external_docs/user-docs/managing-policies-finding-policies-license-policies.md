---
url: https://docs.endorlabs.com/managing-policies/finding-policies/license-policies/
title: License policies | Endor Labs Docs
downloaded: 2025-11-20 11:49:57
---

License policies | Endor Labs Docs



* Type to search...
* ---

[Print entire section](/managing-policies/finding-policies/license-policies/_print.html)



# License policies

Learn about the predefined finding policy templates for open source license risk management.

## Policy templates for open source license detection

Endor Labs provides the following policy templates for detecting open source license usage.
See [Finding Policies](..) for details on how to create policies from policy templates.

| Policy template | Description | Severity |
| --- | --- | --- |
| Permit only specified software licenses | Use this template to define an allowed list of software licenses permitted within your organization or a subset of projects. Endor Labs will raise findings when dependencies in packages or projects have licenses that are not on the allowed list. | Medium |
| Restricted software licenses | Use this template to define a blocked list of software licenses that should be restricted from use or only used within specific contexts within your organization. Endor Labs will raise findings when dependencies in packages or projects have licenses that are on the blocked list. | Medium |
| Restricted software license types | Use this template to create an organizational policy to restrict certain license types or limit a license type to specific contexts within an organization. This is useful to identify license risks and violations in 3rd party open source packages. The license type classification in this policy follows the industry best practice rules defined by [Google license types](https://opensource.google/documentation/reference/thirdparty/licenses#types). If no license types are specified using the input parameter, only “restricted” and “FORBIDDEN” license types are flagged. | Medium |

## Feedback

Was this page helpful?

Yes
No

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

Thanks for the feedback. Write to us at support@endor.ai to tell us more.
