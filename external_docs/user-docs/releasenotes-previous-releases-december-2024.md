---
url: https://docs.endorlabs.com/releasenotes/previous-releases/december-2024/
title: December 2024 | Endor Labs Docs
downloaded: 2025-10-23 23:28:24
---

December 2024 | Endor Labs Docs



* Type to search...
* ---

[Print entire section](/releasenotes/previous-releases/december-2024/_print.html)



# December 2024

We are excited to introduce the latest features and enhancements in Endor Labs.

### Upgrade to endorctl version 1.6.734 or later for container scans Breaking change

Endor Labs has significantly improved container scanning, enhancing the accuracy of findings. As a result, container scans performed with older endorctl versions sometimes yield different or no results.

To ensure accurate scans, upgrade endorctl to version 1.6.734 or higher.

Run `endorctl --version` to check your current version. For instructions on upgrading endorctl, see [Install Endor Labs on your local system](../../../getting-started/quickstart/quickstart-local-system/#Install-Endor-Labs-on-your-local-system).

### Upgrades and remediation support for .NET, Kotlin, and Scala projects Enhancement

Endor Labs upgrade impact analysis now extends its capabilities to support Kotlin, Scala, and .NET projects, complementing the existing support for Python and Java to streamline dependency upgrades across more languages. For more information, see [Remediation support matrix](../../../upgrades-and-remediation/#remediation-support-matrix).

### Configure container finding policies Enhancement

Container base images from untrusted sources may lack proper security audits or fail to comply with organizational standards, increasing the risk of vulnerabilities being exploited. To address this, you can now configure a finding policy to detect unauthorised base images and raise a critical finding. For more information, see [Container policies](../../../managing-policies/finding-policies/container-policies/).

### Export multiple package versions in SBOM Enhancement

You can now export multiple package versions in an SBOM through the Endor Labs user interface. This feature allows aggregating multiple package versions of a project in a single SBOM file. You can choose packages and package versions of a project, which you can export as an SBOM file. For more information, see [Export an SBOM at the project level](../../../managing-sboms/exporting-sboms/#Export-an-SBOM-at-the-project-level).

### My Packages removed from Endor Labs user interface

**My Packages** page is no longer available on the Endor Labs user interface. Instead, you can view packages and package versions associated with a project under **Projects**. Use the package versions filter in **Projects** to filter by specific package criteria.

## Feedback

Was this page helpful?

Yes
No

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

Thanks for the feedback. Write to us at support@endor.ai to tell us more.
