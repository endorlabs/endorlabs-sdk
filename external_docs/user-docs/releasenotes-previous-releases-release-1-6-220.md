---
url: https://docs.endorlabs.com/releasenotes/previous-releases/release-1-6-220/
title: April 2024 | Endor Labs Docs
downloaded: 2025-10-23 23:28:31
---

April 2024 | Endor Labs Docs



* Type to search...
* ---

[Print entire section](/releasenotes/previous-releases/release-1-6-220/_print.html)



# April 2024

We are excited to introduce you to the latest version of Endor Labs and endorctl - v1.6.220. This release includes new features and enhancements.

## New Features

### Sign artifacts (Beta)

You can now use Endor Labs to sign and verify software artifacts. Enhance your software supply chain security by:

* **Ensuring the authenticity of your software:** Understand the origins of your software and confirm its legitimacy. Verify this through integrity checks and cryptographic validation. Using a cryptographic signature ensures that container images and other build artifacts are genuine and crafted by the organization. This adds an extra layer of security to the software supply chain, making sure that only trusted and unaltered items are scheduled deployed and released.
* **Tracking software origins:** Streamline audits, issue resolution, and ownership attribution by linking your software artifacts to their respective source code repository, version, and additional ownership details. Complete traceability ensures transparency, enabling organizations to validate the entire lifecycle of their software, from creation to deployment.

For more information, see [Artifact Signing](../../../artifact-signing/).

### Reachability analysis for Kotlin and Scala projects (Beta)

Endor Labs is excited to announce the reachability analysis for [**Kotlin**](../../../scan-with-endorlabs/language-scanning/kotlin/) and [**Scala**](../../../scan-with-endorlabs/language-scanning/scala/) projects.

You can now track the exact portion of the code in a dependency that is being reused by a program. Endor Labs generates call graphs for Kotlin and Scala projects to help you:

* Analyze the dependencies and relationships among various functions in Kotlin projects. They help identify functions or methods with known vulnerabilities or potential security issues.
* Users can examine the call graph to identify the functions that directly or indirectly call the vulnerable functions by tracing the paths of execution.
* Users can prioritize the vulnerabilities based on their severity, threat levels, and application importance.

Call graphs assist users in comprehending the potential consequences and enable them to prioritize the resolution of vulnerabilities that are more likely to result in additional exploitation.

### Scan Swift and Objective-C projects (Beta)

We are excited to further extend our language scanning capabilities by incorporating support for the Swift and Objective-C projects. Endor Labs resolves dependencies in your projects by analyzing the *Podfile* and *Podfile.lock* files. Users can view finding policy violations and dependency graphs.

Manage your software risk and better understand the bill of materials associated with your software for Swift and Objective-C projects using CocoaPods.

For more information, see [Endor Labs for Swift/Objective-C.](../../../scan-with-endorlabs/language-scanning/swift-objective-c/)

## Enhancements

### Scan EAR and WAR Java artifacts

You can now run `endorctl` scans on the EAR and WAR package file formats which include a pom.xml configuration file.

For more information, see [Scan artifacts.](../../../scan-with-endorlabs/binary-artifact-scan/)

### Flag name change for detecting dependency reachability

For better clarity, the flag `--disable-phantom` is renamed to `--phantom-dependencies`. The corresponding environmental variable is renamed from `ENDOR_SCAN_DISABLE_PHANTOM` to `ENDOR_SCAN_PHANTOM_DEPS`. Set this flag to `true` to scan and detect dependencies used in source code but not declared in the package’s manifest files.

For more information, see [endorctl scan command.](../../../endorctl/commands/scan/)

## Feedback

Was this page helpful?

Yes
No

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

Thanks for the feedback. Write to us at support@endor.ai to tell us more.
