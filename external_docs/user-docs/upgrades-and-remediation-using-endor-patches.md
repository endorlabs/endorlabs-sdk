---
url: https://docs.endorlabs.com/upgrades-and-remediation/using-endor-patches/
title: Endor patches | Endor Labs Docs
downloaded: 2025-10-27 12:57:57
---

Endor patches | Endor Labs Docs



* Type to search...
* ---

[Print entire section](/upgrades-and-remediation/using-endor-patches/_print.html)



# Endor patches

Learn how to use Endor patches and understand why they are beneficial.

Endor patches is a curated repository of software packages with backported vulnerability fixes for your security and convenience. Endor Labs identifies vulnerable functions and the commits that fixed each vulnerability in the open-source community. These fixes, along with necessary supporting commits, are applied to older software versions to create a minimum viable security patch for each library supported by Endor Labs.

Endor patches are a result of extensive research. In security, trust is crucial. Therefore, the patch details are fully transparent. The builds are hermetic ensuring they are consistent, reproducible, and reliable. The exact code changes, along with builds, build steps, and logs, are auditable and available for review.

Customers can access Endor patches through a hosted repository, where each software component has three types of versions.

* A version associated with a specific patch date for build reproducibility. For instance: `v2.9.10.3-endor-2024-07-11`.
* A version with the latest patched version of a library, incorporating all current patches. This can be used by appending `-endor-latest` to a package version. For instance: `v2.9.10.3-endor-latest`.
* A version matching the upstream open-source version, allowing users to use the patched version without code changes. For instance: `v2.9.10.3`.

By minimizing changes to fix known vulnerabilities and providing complete transparency, Endor Patches offer a comprehensive solution to help teams quickly address vulnerabilities, **even when a fix is challenging**.

The following sections provide detailed information on how to use Endor patches.

[### Connect to the Factory

Connect to the Endor Labs Patch Factory and use Endor patches.](./connecting-to-the-factory/)
[### Automatic Patching

Enable automatic patching to seamlessly fix security vulnerabilities.](./auto-patching/)
[### Patch Transparency

Build trust in your Endor patches with full transparency and auditable build processes.](./trust/)

[### Configure JFrog Artifactory

Set up JFrog Artifactory to use Endor patches with proper repository configuration.](./configure-jfrog-artifactory/)
[### Configure Nexus Repository

Configure Sonatype Nexus Repository Manager to prioritize Endor patches.](./configure-nexus-repository/)
[### Access Endor Patch Repository

Learn how to retrieve and use Endor Patches versions using URLs and build tools.](./access-endor-patch-repository/)

## Feedback

Was this page helpful?

Yes
No

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

Thanks for the feedback. Write to us at support@endor.ai to tell us more.
