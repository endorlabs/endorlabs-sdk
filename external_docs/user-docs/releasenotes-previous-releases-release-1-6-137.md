---
url: https://docs.endorlabs.com/releasenotes/previous-releases/release-1-6-137/
title: February 2024 | Endor Labs Docs
downloaded: 2025-11-20 11:52:04
---

February 2024 | Endor Labs Docs



* Type to search...
* ---

[Print entire section](/releasenotes/previous-releases/release-1-6-137/_print.html)



# February 2024

We are excited to introduce you to the latest version of Endor Labs and endorctl - v 1.6.137. This release includes the following new features.

### Sign up for Endor Labs’ Free trial

Discover the power of Endor Labs and the endorctl CLI with our brand-new 30-day free trial. Secure your open source software by prioritizing open source risk, reducing technical debt, and meeting compliance objectives like SBOMs & VEX. With Endor Labs’ reachability analysis, DevSecOps teams can get to the right context faster, manage risks effectively, and accelerate product development.

What’s in the trial:

* **Complete access**: Enjoy all the features without limitations for an entire month.
* **Getting started**: Use Endor Labs’ guided walkthrough to understand the main features of the application.
* **Quick start**: Use the [quick start](../../../getting-started/quickstart/) to get started with the application.
* **Seamless integration**: Effortlessly integrate Endor Labs into your development workflows.

### Setup namespaces (Beta)

Leverage namespaces to establish a logical and hierarchical structure for your projects, providing enhanced organization and clarity. As an administrator, you can:

* **Organizational logic:** Create logical partitions based on organizational units, business units, project requirements, or teams.
* **Access control:** Define hierarchy and control access to project resources within a namespace, ensuring a tailored and secure project environment.
* **Policy governance:** Establish robust policy governance by defining rules of engagement within namespaces and setting different or identical guardrails across namespaces.

For more information, see [Set up namespaces](../../../administration/namespaces/).

### Scan Kotlin projects (Beta)

Scan your Kotlin projects to perform:

* **Quick Scan:** Quickly assess software composition using `endorctl scan --quick-scan`.
* **Deep Scan:** Conduct comprehensive analysis with dependency resolution, reachability analysis, and call graph generation using the `endorctl scan`.
* **Maven and Gradle Integration:** Seamlessly integrate with Maven and Gradle for efficient builds and dependency resolution.
* **Configuration Flexibility:** Configure Maven private registries and specify Gradle configurations with ease.
* **Static Analysis:** In-depth analysis of Kotlin code for precise insights into dependency reachability.

For more information, see [Endor Labs for Kotlin](../../../scan-with-endorlabs/language-scanning/kotlin/).

### Dependency discovery for Go projects using Bazel (Beta)

Scan Go projects with Bazel integration using the `endorctl scan` command. By leveraging this command as a Bazel rule, you can analyze dependencies while using Bazel commands.

* **Bazel Integration:** Scan Go projects by calling the `endorctl scan` command as a Bazel rule, ensuring smooth integration with Bazel workflows.
* **Targeted Scanning:** Choose between scanning the entire repository or specific Go targets using language-specific Bazel rules. Alternatively, employ a Bazel query to scan targets based on specific criteria.
* **Incremental Scans:** Execute scans with precision by focusing on recently updated targets, optimizing the scanning process for enhanced efficiency.

For more information, see [Language-specific Bazel](../../../scan-with-endorlabs/language-scanning/bazel/).

### Scan binary artifacts (Beta)

Execute `endorctl` scans on binaries and artifacts without the complexities of accessing source code or build systems.

* **Language support:** The scanning functionality extends to Java and Python packages, covering a wide spectrum of pre-built, bundled, or locally downloaded components.
* **Artifact/Package specification:** Easily initiate scans by specifying the file path to their artifact or binary package, streamlining the scanning process.
* **Comprehensive scan:** Scan specified packages to gain insights into resolved dependencies, transitive dependencies, and comprehensive call graphs, providing you with a holistic view of software components.

For more information, see [Binaries and artifacts](../../../scan-with-endorlabs/binary-artifact-scan/).

## Feedback

Was this page helpful?

Yes
No

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

Thanks for the feedback. Write to us at support@endor.ai to tell us more.
