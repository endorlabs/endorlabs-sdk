---
url: https://docs.endorlabs.com/introduction/reachability-analysis/
title: Reachability analysis | Endor Labs Docs
downloaded: 2025-11-20 11:49:26
---

Reachability analysis | Endor Labs Docs



* Type to search...
* ---

[Print entire section](/introduction/reachability-analysis/_print.html)



# Reachability analysis

Learn how Endor Labs helps you identify which vulnerabilities are exploitable, potentially exploitable, and false positives.

Modern software relies on complex code, external libraries, and open-source components (OSS). Managing risks requires understanding where issues come from, such as internal code, OSS, or other external dependencies.

Dependencies in a project can be classified as direct or transitive. Direct dependencies are explicitly added by developers, such as when a specific library is included in a project.
Transitive dependencies are those pulled in indirectly through other libraries. While direct dependencies are easier to track and manage, transitive dependencies can introduce complexity, as they may not be immediately visible in the project’s configuration files.

Categorizing code as reachable, potentially reachable, or unreachable is another important step. Reachable code is actively invoked during normal execution.
Unreachable code, on the other hand, is not used at all and can accumulate over time, leading to unnecessary complexity and potential issues. Identifying and managing these categories ensures that the codebase remains efficient and maintainable.

## Types of Reachability Analysis

Endor Labs offers multiple types of reachability analysis to help you accurately assess vulnerability exposure in your applications. Each type provides different levels of granularity and accuracy depending on your specific use case and available analysis context.

* **[Function-level reachability](#function-level-reachability)** and **[Dependency-level reachability](#dependency-level-reachability)**: These analyses run during a full scan, when the project builds successfully and complete call graphs are generated. They use actual code paths and dependency metadata to provide the most precise vulnerability assessment.
* **[Pre-computed reachability](pre-computed-reachability/)**: This analysis is used as a fallback when project builds fail or call graph generation is not possible. It’s particularly useful for scans where there are complex build processes to prioritize issues without the need for developer intervention or configuration. It provides an approximate analysis of vulnerability reachability based on how your direct dependencies interact with your transitive dependencies irrespective of your application code.

### Function-level reachability

To help developers and security teams make informed decisions for SCA results, Endor Labs leverages a static analysis technique called program analysis to perform **function-level reachability analysis** on direct and transitive dependencies. This is the most accurate way to determine exploitability in the context of your application, which is critical for determining which risks should be remediated.

#### Function-level reachability labels

The different function reachability labels include:

* **Reachable Function**:
  Endor Labs has determined that there is a path from the developer-written code to a vulnerable function, indicating that the finding is exploitable in your environment. This is demonstrated by a call graph that illustrates each step between the source code and the vulnerable library.
* **Unreachable Function**:
  Endor Labs has determined that there is no risk of exploitation, as there is no path from the source code to the vulnerable function. This conclusion is supported by a call graph that demonstrates the absence of such a path.
* **Potentially Reachable Function**:
  Endor Labs is unable to determine whether a finding is reachable or unreachable, typically because call graph analysis is unsupported for a given language or package manager. This means that the function in question may be executable in the context of the dependent project, but the analysis cannot definitively determine if it is reachable or not.

### Dependency-level reachability

Endor Labs supports **dependency-level reachability** by default for all supported languages. This type of reachability analysis is more coarse-grained than function-level reachability. It indicates that the imported package is being used somewhere in the application but does not determine whether the vulnerable package is being called by the source code.

The dependency-level reachability can be used as a good indicator for prioritization. If you’re not actually using the dependency at all, then removing that dependency could be a consideration. Determining whether a dependency is being called or used is another layer of prioritization you can add to your remediation process.

#### Dependency reachability Labels

The different dependency reachability labels include:

* **Reachable Dependency:**
  Endor Labs established that an imported package is being used somewhere in the application.
* **Unreachable Dependency:**
  Endor Labs determined that the imported dependency is not being used. The customer can use this information to remove the dependency, which is helpful for technical debt reduction initiatives.
* **Potentially Reachable Dependency:**
  Endor Labs cannot definitively determine whether a dependency is or is not in use, generally because a given language or package manager is not supported.

### Comparison of reachability analysis types

The following table compares the three types of reachability analysis available in Endor Labs:

| Analysis Type | Requirements | Coverage | Use Case |
| --- | --- | --- | --- |
| Function-level | Successful project build and client call graph generation | Direct and transitive dependencies | Precise vulnerability assessment for production applications |
| Dependency-level | Dependency resolution and import analysis only | Direct and transitive dependencies | Quick dependency prioritization and cleanup |
| Pre-computed | Dependency metadata without compilation or call graphs | Transitive dependencies only | Analysis when builds fail or are unavailable |

## Phantom dependencies

Phantom dependencies are packages utilized in your codebase that are not explicitly declared in your project’s manifest files, for example, `package.json`, or `requirements.txt`. These undeclared dependencies can pose significant security and operational risks, as they may contain vulnerabilities not tracked or assessed during standard dependency analysis. Identifying and managing phantom dependencies is crucial for accurate reachability analysis and comprehensive risk assessment.

### Detection of phantom dependencies

Endor Labs’ reachability analysis conducts thorough scans of your codebase to identify functions and methods invoked from both declared and undeclared dependencies. By analyzing the actual usage of packages in your source code, the system identifies phantom dependencies—those that are in use but not explicitly declared. This detection ensures that all utilized code paths are assessed for potential vulnerabilities, providing a more accurate and comprehensive security evaluation.

---

##### [Pre-computed Reachability analysis](/introduction/reachability-analysis/pre-computed-reachability/)

Discover how to identify and prioritize vulnerabilities without relying on code compilation or full call graphs.

## Feedback

Was this page helpful?

Yes
No

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

Thanks for the feedback. Write to us at support@endor.ai to tell us more.
