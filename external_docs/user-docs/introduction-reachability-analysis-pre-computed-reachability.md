---
url: https://docs.endorlabs.com/introduction/reachability-analysis/pre-computed-reachability/
title: Pre-computed Reachability analysis | Endor Labs Docs
downloaded: 2025-10-27 12:57:27
---

Pre-computed Reachability analysis | Endor Labs Docs



* Type to search...
* ---

[Print entire section](/introduction/reachability-analysis/pre-computed-reachability/_print.html)



# Pre-computed Reachability analysis

Discover how to identify and prioritize vulnerabilities without relying on code compilation or full call graphs.

Pre-computed reachability is an approximate analysis technique that determines vulnerability exposure by operating directly on dependency relationships and available metadata. This method eliminates the need for code compilation or full call graph generation while automatically treating all direct dependencies as reachable and focusing on analyzing transitive dependencies.

Pre-computed reachability offers a faster alternative to traditional analysis, enabling teams to assess potential risks when a full build or complete call graph is unavailable. It can serve as the primary method for quick scans or as the fallback option when traditional reachability analysis fails after a full scan. However, this approach may produce false positives.

To enable pre-computed reachability analysis, use the `ENDOR_SCAN_ENABLE_PRECOMPUTED_CALLGRAPHS` flag.

```
export ENDOR_SCAN_ENABLE_PRECOMPUTED_CALLGRAPHS=true
```

Once enabled, pre-computed reachability analysis is used in the following scenarios:

* **Quick Scan**: When you run `endorctl scan --quick-scan`, the system uses pre-computed reachability analysis.
* **Full Scan**: When you run `endorctl scan`, the system attempts traditional call graph generation first and switches to pre-computed reachability only if the build fails.

Pre-computed reachability is supported for the following languages: `java`, `javascript`, `typescript`, `kotlin`, `python`, `scala`, and `C#`.

### Scan modes and pre-computed reachability

Endor Labs supports multiple scan modes that can utilize pre-computed reachability analysis. The analysis type depends on whether a call graph is generated and whether pre-computed reachability is available as a fallback.

The following table summarizes how pre-computed reachability is used across different scan modes:

| Scan type | Reachability analysis type | Reachability Coverage | Call graph generated |
| --- | --- | --- | --- |
| Quick scan | None | None | ✗ |
| Quick scan with pre-computed flag | Pre-computed | Transitive dependencies | ✗ |
| Full scan | Full dependency-level and function-level | Direct and transitive dependencies | ✓ |
| Full scan with pre-computed flag | Dependency-level and function-level. If the code build fails, it falls back to pre-computed reachability | Direct and transitive dependencies | ✗ |

### Pre-computed reachability analysis process

Pre-computed reachability analysis evaluates transitive dependencies using available metadata and entry points. This analysis provides an approximate assessment of vulnerability exposure in dependencies.

The analysis uses two key techniques:

* **Direct dependency analysis**: Assesses vulnerability reachability within direct dependencies. Endor Labs pre-computes their call graphs by performing actual reachability analysis on each open source dependency and assumes everything is reachable. This provides an accurate evaluation of vulnerabilities in code your project directly depends on.
* **Dependency flattening**: Addresses situations where call graphs for private or missing dependencies are unavailable. This technique treats direct dependencies as reachable and uses these modules as entry points, allowing the analysis to estimate reachability without full call graph information.

#### Note

If a transitive dependency is called directly in the code, pre-computed analysis will not surface that usage.

### Pre-computed versus traditional reachability analysis

Pre-computed reachability analysis reduces build dependencies, simplifies infrastructure, and expands coverage compared to a traditional vulnerability scan.

* **Build-independent and lightweight operation**: Performs analysis without requiring builds, compilers, or runtime environments, allowing you to scan incomplete or misconfigured projects and resolve dependencies, all while reducing CI/CD complexity.
* **Extended codebase coverage**: Enables you to scan previously inaccessible repositories by bypassing build failures, ensuring visibility into legacy systems, experimental branches, and incomplete implementations.
* **Preserved vulnerability prioritization**: Retains reachability-based risk scoring accuracy by using dependency metadata and entry point analysis, ensuring that critical vulnerabilities remain properly prioritized.

Pre-computed reachability analysis prioritizes speed and broad coverage over precision, which can result in false positives. It assumes that all vulnerabilities and potential functions in direct dependencies are reachable, even if they aren’t actually invoked during execution. The analysis then maps transitive dependencies based on these functions. Though this approach removes the need for code level analysis, it increases the likelihood of flagging vulnerabilities that may not be truly exploitable.

## Feedback

Was this page helpful?

Yes
No

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

Thanks for the feedback. Write to us at support@endor.ai to tell us more.
