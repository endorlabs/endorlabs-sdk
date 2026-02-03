---
url: https://docs.endorlabs.com/introduction/reachability-analysis/
title: Reachability analysis | Endor Labs Docs
downloaded: 2026-02-03 00:50:03
---

Reachability analysis | Endor Labs Docs



* Type to search...

[Print entire section](/introduction/reachability-analysis/_print.html)



# Reachability analysis

Learn how Endor Labs helps you identify which vulnerabilities are exploitable, potentially exploitable, and false positives.

Modern software relies on complex code, external libraries, and open-source components (OSS). Managing risks requires understanding where issues come from, such as internal code, OSS, or other external dependencies.

Projects contain two types of dependencies, direct and transitive. Developers explicitly add direct dependencies, such as when they include a specific library in a project.
Transitive dependencies enter the project indirectly through other libraries. While direct dependencies are easier to track and manage, transitive dependencies can introduce complexity, as they may not be immediately visible in the project’s configuration files.

Categorizing code as reachable, potentially reachable, or unreachable is another important step. Reachable code is actively invoked during normal execution. Unreachable code, on the other hand, is not used and can accumulate over time, leading to unnecessary complexity and potential issues. Identifying and managing these categories ensures that the codebase remains efficient and maintainable.

## Types of Reachability Analysis

Endor Labs offers multiple types of reachability analysis to help you accurately assess vulnerability exposure in your applications. Each type provides different levels of granularity and accuracy depending on your specific use case and available analysis context.

* **[Function-level reachability](#function-level-reachability)** and **[Dependency-level reachability](#dependency-level-reachability)**: These analyses run during a full scan, when the project builds successfully and Endor Labs generates complete call graphs. They use actual code paths and dependency metadata to provide the most precise vulnerability assessment.
* **[Pre-computed reachability](pre-computed-reachability/)**: A pragmatic, manifest-based analysis technique that enables you to assess whether vulnerabilities in transitive dependencies could be reachable from your direct dependencies—all without requiring code compilation, builds, or full call graph generation. With approximately **95%** of vulnerabilities existing in transitive dependencies according to [Endor Labs’ State of Dependency Management report](https://www.endorlabs.com/state-of-dependency-management), pre-computed reachability helps you deprioritize security issues that can’t be called by your application by filtering out vulnerabilities that affect functions in transitive dependencies that are not used by your direct dependencies. This approach works by analyzing how your direct dependencies interact with their transitive dependencies, providing valuable reachability insights as a fallback for full scans when builds fail, or as an optional enhancement for quick scans when you want reachability analysis without build requirements. [Learn more about pre-computed reachability](pre-computed-reachability/).

### Function-level reachability

To help developers and security teams make informed decisions for SCA results, Endor Labs uses a static analysis technique called program analysis to perform **function-level reachability analysis** on direct and transitive dependencies. This is the most accurate way to determine exploitability in the context of your application, which is critical for determining which risks you should remediate.

#### Function-level reachability labels

The different function reachability labels include:

* **Reachable Function**:
  Endor Labs has determined that there is a path from the developer-written code to a vulnerable function, indicating that the finding is exploitable in your environment. This is demonstrated by a call graph that illustrates each step between the source code and the vulnerable library.
* **Unreachable Function**:
  Endor Labs determines that no risk of exploitation exists, as no path exists from the source code to the vulnerable function. A call graph supports this conclusion by demonstrating the absence of such a path.
* **Potentially Reachable Function**:
  Endor Labs is unable to determine whether a finding is reachable or unreachable, typically because call graph analysis is unsupported for a given language or package manager. This means that the function in question may be executable in the context of the dependent project, but the analysis cannot definitively determine if it is reachable or not.

### Dependency-level reachability

Endor Labs supports **dependency-level reachability** by default for all supported languages. This type of reachability analysis is more coarse-grained than function-level reachability. It indicates that the application uses the imported package somewhere but does not determine whether the source code calls the vulnerable package.

Dependency-level reachability serves as a good indicator for prioritization. If you’re not actually using the dependency at all, consider removing that dependency. Determining whether your code calls or uses a dependency provides another layer of prioritization you can add to your remediation process.

#### Dependency reachability labels

The different dependency reachability labels include:

* **Reachable Dependency:**
  Endor Labs established that an imported package is being used somewhere in the application.
* **Unreachable Dependency:**
  Endor Labs determined that the imported dependency is not being used. The customer can use this information to remove the dependency, which is helpful for technical debt reduction initiatives.
* **Potentially Reachable Dependency:**
  Endor Labs cannot definitively determine whether the application uses a dependency, generally because Endor Labs does not support the given language or package manager.

### Comparison of reachability analysis types

The following table compares the three types of reachability analysis available in Endor Labs:

| Analysis Type | Requirements | Coverage | Use Case |
| --- | --- | --- | --- |
| Function-level | Successful project build and client call graph generation | Direct and transitive dependencies | Precise vulnerability assessment for production applications |
| Dependency-level | Dependency resolution and import analysis only | Direct and transitive dependencies | Quick dependency prioritization and cleanup |
| Pre-computed | Dependency metadata without compilation or call graphs | Transitive dependencies only | Pragmatic analysis as a fallback when builds fail, and when you want reachability analysis without build requirements |

## Phantom dependencies

Phantom dependencies are packages that your codebase uses but does not explicitly declare in your project’s manifest files, for example, `package.json`, or `requirements.txt`. These undeclared dependencies can pose significant security and operational risks, as they may contain vulnerabilities that standard dependency analysis does not track or assess. Identifying and managing phantom dependencies is crucial for accurate reachability analysis and comprehensive risk assessment.

### Detection of phantom dependencies

Endor Labs’ reachability analysis conducts thorough scans of your codebase to identify functions and methods that both declared and undeclared dependencies invoke. By analyzing the actual usage of packages in your source code, the system identifies phantom dependencies—those that your code uses but does not explicitly declare. This detection ensures that all utilized code paths are assessed for potential vulnerabilities, providing a more accurate and comprehensive security evaluation.

---

##### [Pre-computed Reachability analysis](/introduction/reachability-analysis/pre-computed-reachability/)

Pragmatically assess vulnerability reachability in transitive dependencies without builds. Filter out irrelevant vulnerabilities and focus your team’s time.

## Feedback

Was this page helpful?

Yes
No

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

Thanks for the feedback. Write to us at support@endor.ai to tell us more.
