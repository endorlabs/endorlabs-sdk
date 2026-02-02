---
url: https://docs.endorlabs.com/introduction/reachability-analysis/pre-computed-reachability/
title: Pre-computed Reachability analysis | Endor Labs Docs
downloaded: 2026-01-29 22:20:49
---

Pre-computed Reachability analysis | Endor Labs Docs



* Type to search...

[Print entire section](/introduction/reachability-analysis/pre-computed-reachability/_print.html)



# Pre-computed Reachability analysis

Pragmatically assess vulnerability reachability in transitive dependencies without builds. Filter out irrelevant vulnerabilities and focus your team’s time.

## Introduction

Modern applications rely on open-source dependencies, with the vast majority of vulnerabilities (approximately **95%** according to [Endor Labs’ State of Dependency Management report](https://www.endorlabs.com/state-of-dependency-management)) existing in transitive (indirect) dependencies rather than direct ones. This means most security risks come from packages you didn’t explicitly add to your project, making it challenging to assess which vulnerabilities actually pose a threat to your application.

**Pre-computed reachability** is a pragmatic analysis technique that enables you to assess whether vulnerabilities in transitive dependencies could be reachable from your direct dependencies, all without requiring code compilation or builds. It serves two primary purposes: as a fallback mechanism for full scans when builds fail, and as an optional enhancement for quick scans when you want reachability analysis without build requirements. This analysis technique filters out vulnerabilities that affect functions never called within your dependency chain, helping you focus your team’s time and attention on the security issues that truly matter.

The benefits of pre-computed reachability include:

* **Pragmatic and easy**: Results are pre-computed and cached, making it a practical approach to reachability analysis. It works solely from your manifest files (for example, `package.json`, `go.mod`, `pom.xml`, `build.gradle`, and others), requiring no access to your application’s built artifacts.
* **Excellent noise reduction**: By analyzing how your direct dependencies interact with transitive dependencies, pre-computed reachability can filter out a significant portion of irrelevant vulnerabilities, enabling you to focus your team’s time on the security issues that truly matter.
* **Build-independent**: Works without requiring builds or compilation, making it a pragmatic option when you want reachability analysis without build setup.
* **Reliable fallback for full scans**: When builds fail or call graph generation isn’t possible, pre-computed reachability ensures you still get actionable security insights rather than missing out on reachability analysis entirely.

## Getting Started

**Pre-computed reachability is automatically used as the default fallback for full scans** when builds fail or call graph generation isn’t possible, ensuring you always get reachability insights. **For quick scans, pre-computed reachability is optional** and can be enabled using the `ENDOR_SCAN_ENABLE_PRECOMPUTED_CALLGRAPHS` flag.

To enable pre-computed reachability analysis, use the `ENDOR_SCAN_ENABLE_PRECOMPUTED_CALLGRAPHS` flag:

```
export ENDOR_SCAN_ENABLE_PRECOMPUTED_CALLGRAPHS=true
```

The system uses pre-computed reachability analysis in the following scenarios:

* **Full Scan**: When you run `endorctl scan`, the system attempts full call graph generation first for maximum precision. If the build fails or call graph generation isn’t possible, it automatically falls back to pre-computed reachability by default, ensuring you still get valuable reachability insights.
* **Quick Scan**: When you run `endorctl scan --quick-scan`, you can optionally enable pre-computed reachability analysis by setting the `ENDOR_SCAN_ENABLE_PRECOMPUTED_CALLGRAPHS` flag. This provides reachability insights without requiring builds.

Endor Labs supports pre-computed reachability for the following languages: `java`, `javascript`, `typescript`, `kotlin`, `python`, `scala`, and `C#`.

### Scan modes and pre-computed reachability

Endor Labs supports multiple scan modes that can utilize pre-computed reachability analysis. For full scans, pre-computed reachability is automatically used as the default fallback when needed. For quick scans, it is optional and requires the flag to be enabled.

The following table summarizes how pre-computed reachability is used across different scan modes:

| Scan type | Reachability analysis type | Reachability Coverage | Call graph generated |
| --- | --- | --- | --- |
| Quick scan | None | None | ✗ |
| Quick scan with pre-computed flag | Pre-computed | Transitive dependencies | ✗ |
| Full scan | Full dependency-level and function-level. Automatically falls back to pre-computed reachability if build fails | Direct and transitive dependencies | ✓ |
| Full scan with pre-computed flag | Dependency-level and function-level. If the code build fails, it falls back to pre-computed reachability | Direct and transitive dependencies | ✓ |

## How Pre-computed Reachability Works

Pre-computed reachability analysis evaluates transitive dependencies using a simple but effective approach: it assumes that everything in your direct dependencies is reachable, then uses that assumption to assess whether vulnerabilities in transitive dependencies could be called.

### From Manifest to Dependency Graph

The analysis begins with your manifest files (`package.json`, `go.mod`, `Gemfile`, `pom.xml`, `build.gradle`, and others). Endor Labs resolves your dependencies to build a complete list of direct and transitive dependencies—along with the dependency graph that connects them. **Dependency resolution is required to identify all transitive dependencies, but no build or compilation is necessary.**

### Computing Vulnerability Reachability

For every detected CVE in a transitive dependency, the analysis works as follows:

1. **Assume direct dependencies are fully reachable**: Pre-computed reachability assumes that all functions and code in your direct dependencies are reachable. This includes both open-source dependencies and private, non-open source first-party libraries. This conservative assumption ensures comprehensive coverage without needing to analyze your application’s source code.
2. **Assess transitive dependency reachability**: Using pre-computed call graph information from open-source dependencies, the system analyzes how your direct dependencies interact with their transitive dependencies. If a direct dependency can call a vulnerable function in a transitive dependency, that vulnerability is marked as reachable.
3. **Filter unreachable vulnerabilities**: If a vulnerable function in a transitive dependency cannot be reached through any of your direct dependencies (based on the pre-computed call graph information), the CVE is marked as unreachable and can be deprioritized.

The key insight is that pre-computed reachability leverages the fact that Endor Labs has already analyzed how open-source packages interact with their dependencies. By assuming your direct dependencies are fully reachable and using this pre-computed information, the analysis can determine which transitive dependency vulnerabilities could be reachable without needing to build your application or analyze your source code.

### Reachable vs Unreachable CVEs

Based on the analysis:

* **Unreachable CVEs**: If a vulnerable function in a transitive dependency cannot be reached through any of your direct dependencies (based on pre-computed call graph information), the CVE is marked as unreachable. These can be deprioritized, as the vulnerable code cannot be invoked through your dependency chain.
* **Reachable CVEs**: If a vulnerable function in a transitive dependency can be reached through one or more of your direct dependencies, the vulnerability is flagged as *reachable*. For reachable CVEs, Endor Labs shows the list of function calls in your dependencies that may trigger the vulnerability.

Pre-computed reachability assumes all direct dependencies are reachable, so if a direct dependency can call a vulnerable function in a transitive dependency, that vulnerability is marked as reachable. Pre-computed reachability focuses on analyzing dependency relationships rather than your application’s source code usage. For the most precise assessment when builds are successful, [function-level reachability analysis](../) analyzes your application’s source code directly through full call graph generation to determine actual usage.

**Note**

Pre-computed reachability analyzes how your direct dependencies interact with transitive dependencies, but does not analyze direct calls to transitive dependencies from your application code. For complete coverage including direct usage of transitive dependencies, [function-level reachability analysis](../) provides full analysis when builds are successful.

## When Pre-computed Reachability is Used

Pre-computed reachability serves two distinct purposes:

### As a Fallback for Full Scans

For full scans, pre-computed reachability automatically serves as a fallback when:

* **Builds fail**: If your project build fails or encounters errors, pre-computed reachability ensures you still get reachability analysis rather than missing out entirely.
* **Call graph generation isn’t possible**: In cases where full call graph generation isn’t available, pre-computed reachability provides valuable reachability insights.

### As an Option for Quick Scans

For quick scans, you can proactively enable pre-computed reachability when you want reachability analysis without build requirements. This pragmatic approach provides vulnerability assessment based on manifest files alone, making it ideal for:

* **Build-free analysis**: When you want reachability insights without setting up build environments or waiting for compilation.
* **CI/CD pipelines**: In environments where you want reachability analysis without build dependencies.
* **Large-scale scanning**: When scanning multiple repositories or projects, where build setup isn’t practical.

The philosophy behind pre-computed reachability is simple: don’t let perfect get in the way of better. When full call graph analysis isn’t possible or when you want a pragmatic approach without build requirements, pre-computed reachability ensures you still get actionable security insights rather than no analysis at all.

## Comparison with Other Reachability Analysis Types

Pre-computed reachability complements Endor Labs’ other reachability analysis capabilities:

* **[Function-level reachability](../)**: The most precise analysis that examines your application’s source code directly through full call graph generation. This is the primary and preferred method when builds succeed, providing the highest accuracy for production applications.
* **Pre-computed reachability** (this page): A pragmatic, manifest-based analysis that works without builds or source code access. Serves as an automatic fallback for full scans when builds fail, and can be enabled for quick scans when you want reachability analysis without build requirements. Focuses on transitive dependencies.

Endor Labs automatically uses the best available analysis method for your situation. When full call graph generation is possible, it’s used for maximum precision. When it’s not, pre-computed reachability steps in as a reliable fallback, ensuring you always get actionable security insights.

## Limitations

### Direct Dependency Vulnerabilities

Pre-computed reachability analysis is optimized for vulnerabilities in transitive/indirect dependencies, where it can leverage the analysis of how your direct dependencies interact with their dependencies. When full call graph generation is possible, [function-level reachability analysis](../) provides more precise results by analyzing your application’s source code directly.

## Feedback

Was this page helpful?

Yes
No

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

Thanks for the feedback. Write to us at support@endor.ai to tell us more.
