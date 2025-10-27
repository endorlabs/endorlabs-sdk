---
url: https://docs.endorlabs.com/upgrades-and-remediation/using-endor-patches/auto-patching/
title: Automatic patching with Endor Patches | Endor Labs Docs
downloaded: 2025-10-27 12:57:50
---

Automatic patching with Endor Patches | Endor Labs Docs



* Type to search...
* ---

[Print entire section](/upgrades-and-remediation/using-endor-patches/auto-patching/_print.html)



# Automatic patching with Endor Patches

Learn how to minimize changes for an Endor patch.

Upgrading software can be challenging for development teams. **Endor Automatic Patching** allows you to seamlessly fix security vulnerabilities during each software build, minimizing the effort required to maintain a secure codebase.

By enabling automatic patching with Endor Labs for every build, you can automatically address vulnerabilities in both direct and transitive dependencies. This approach helps prevent a growing backlog of security issues.

## Enable Automatic Patching

To start using Endor Lab’s automatic patching, follow these steps:

1. Configure Endor Labs Patch Factory.

   Set **Endor Labs Patch Factory** as the top priority package repository in your package manager or Artifactory virtual repository.
   For detailed instructions, refer to the following documentation:

   * Learn how to [connect to the Endor Labs Patch Factory](../connecting-to-the-factory/).
   * Learn how to [configure JFrog Artifactory](../configure-jfrog-artifactory/).
   * Learn how to [configure a Nexus repository](../configure-nexus-repository/).
2. Enable Auto Patching in Endor Labs. See [Endor patches settings](../../../administration/configure-system-settings/#configure-endor-patches-settings) to activate auto patching.

### Considerations for automatic patching

While automatic patching enhances security by addressing vulnerabilities, it introduces some trade-offs.

#### Build reproducibility

Automatically applied patches may alter the build process or the resulting binaries in unpredictable ways, potentially affecting build reproducibility.

Endor Labs strives to provide the minimal necessary security patches to ensure your software remains secure without introducing significant changes. With automatic patching enabled, new patches are applied automatically as they become available, reducing manual intervention and enhancing your security posture.

## Feedback

Was this page helpful?

Yes
No

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

Thanks for the feedback. Write to us at support@endor.ai to tell us more.
