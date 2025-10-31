---
url: https://docs.endorlabs.com/managing-policies/tagging-projects/
title: Tag projects | Endor Labs Docs
downloaded: 2025-10-27 12:59:43
---

Tag projects | Endor Labs Docs



* Type to search...
* ---

[Print entire section](/managing-policies/tagging-projects/_print.html)



# Tag projects

Learn about tagging projects to manage policies in Endor Labs

All Endor Labs policies provide the option to define inclusion and exclusion criteria based on project tags. This allows you to implement exception workflows, to onboard new teams or business units, and to set specific policies that only apply to sets of projects, such as those that are mature or the crown jewel applications of an organization.

Most organizations have projects with differing compliance and security requirements. Adopting a single standard for all projects can lead to challenges. While many controls apply equally across an environment, some controls are excessive or irrelevant for projects that don’t need to meet specific regulatory frameworks, or do not process sensitive information.

For example, an organization may want to look for leaked secrets in all repositories, but may not require a robust vulnerability management program and branch protection strategy on projects where internal documentation is developed.

The following reference tagging strategies can help organizations align their policies with their internal control needs.

| Use Case | Rationale | Example Tags |
| --- | --- | --- |
| Data Classification | Apply controls to projects from which applications that process sensitive data are developed. | `Classification_Restricted`, `Classification_HighlySensitive`, `Classification_Public` |
| Application Importance | Apply controls to projects based on the importance of the applications developed in them. | `Application_CrownJewel`, `Application_Critical` |
| Application Exposure | Apply controls to project from which applications that are exposed internally or to the public internet differently. | `Exposure_Public` , `Exposure_Internal` |
| Compliance | Apply controls to projects where specific compliance or regulatory controls may apply. | `Compliance_SOC2`, `Compliance_HIPAA`, `Compliance_PCI`, `Compliance_None` |
| Business Unit | Apply controls to projects based on a business units maturity or onboarding status. Apply different controls to a new acquisition. | `BU_Infrastructure`, `BU_Clinical` |
| Policy Exceptions | Do not apply a control to a repository that has an approved policy exception | `Policy_Exception_Branch_Protection` |

## Tag your projects

Tags add additional metadata to projects and help you identify them. You can also use the project tags to define the scope of a finding or an action policy for a project.

* For more details on finding policies, see [Finding policies](../finding-policies/)
* For more details on action polices, see [Action policies](../action-policies/)

To create tags for a project:

1. Sign in to Endor Labs and select **Projects** from the sidebar.
2. Select a project and click **Settings**.
3. Type a name for the tag in **Custom Tags** and press Enter. Tags can have a maximum length of 63 characters and can contain letters (A-Z), numbers (0-9), and characters (=@-\_).
4. Click **Save Tags**.
5. Use **Reset Tags** to make a new entry.

## Feedback

Was this page helpful?

Yes
No

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

Thanks for the feedback. Write to us at support@endor.ai to tell us more.
