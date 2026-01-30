---
url: https://docs.endorlabs.com/scan-with-endorlabs/language-scanning/bazel/
title: Bazel | Endor Labs Docs
downloaded: 2026-01-26 10:08:58
---

Bazel | Endor Labs Docs



* Type to search...

[Print entire section](/scan-with-endorlabs/language-scanning/bazel/_print.html)



# Bazel

Learn how to implement Endor Labs in monorepos using Bazel

Bazel is an open-source build and test tool commonly used in monorepos to quickly build software across multiple languages.

You can use Endor Labs and Bazel to scan software for potential security issues and policy violations, prioritize vulnerabilities in the context of your applications, and understand relationships between software components.

## Prerequisites for scanning Bazel projects

Ensure that the following prerequisites are in place for a successful scan:

* `WORKSPACE` file exists in your repository
* `bazel` command installed and available
* Bazel version `5.x.x`, `6.x.x`, or `7.x.x`
* Supported target types in your project

### System specifications for deep scans of Bazel projects

Before you proceed to run a deep scan, ensure that your system meets the following specification.

| Project Size | Processor | Memory |
| --- | --- | --- |
| Small projects | 4-core processor | 16 GB |
| Mid-size projects | 8-core processor | 32 GB |
| Large projects | 16-core processor | 64 GB |

### Build process for Bazel projects

You can choose to build the targets before running the scan. Use the `bazel build` commands to do this by passing a comma-separated list of targets. For example, for targets `//:test` and `//:test2`, run `bazel build //:test,//:test2`.

endorctl will automatically build targets if they are not already built. endorctl uses `bazel build //:target` and `bazel query 'deps(//:target)' --output graph` to build each target and analyze its dependency tree.

## Supported Bazel rules and features

The following table lists the supported Bazel rules and Endor Labs features for each language.

| Language | Supported Rules | Version Requirements |
| --- | --- | --- |
| [Java](https://github.com/bazelbuild/rules_jvm_external) | [java\_library](https://bazel.build/reference/be/java#java_library), [java\_binary](https://bazel.build/reference/be/java#java_binary)  📝 While dependency scanning is supported for `java_binary` targets, call graph generation requires an uber jar containing all dependencies. The `java_binary` rule itself does not produce an uber jar, but its `deploy.jar` output provides the necessary consolidated dependencies for call graph analysis. | 4.1+ |
| [Python](https://github.com/bazelbuild/rules_python) | [py\_binary](https://bazel.build/reference/be/python#py_binary), [py\_library](https://bazel.build/reference/be/python#py_library), [py\_image](https://github.com/bazelbuild/rules_docker/blob/master/README.md#py3_image)  🛑 `py_image` only supports PY3 toolchain (`py3_image`) | 0.9.0+ |
| [Go](https://github.com/bazelbuild/rules_go) | [go\_binary](https://github.com/bazelbuild/rules_go/blob/master/docs/go/core/rules.md#go_binary), [go\_library](https://github.com/bazelbuild/rules_go/blob/master/docs/go/core/rules.md#go_library), [go\_image](https://github.com/bazelbuild/rules_docker/blob/master/README.md#go_image) | 0.40.1+ (Bazel 5.x-6.x), 0.42.0+ (Bazel 7.x)  📝 For [Bazel with Gazelle in vendored mode](https://github.com/bazelbuild/bazel-gazelle?tab=readme-ov-file#bazel-rule), see [Go with Gazelle](#scan-bazel-projects-with-go-with-gazelle-vendored-mode). |
| [Scala](https://github.com/bazelbuild/rules_scala) | [scala\_binary](https://github.com/bazelbuild/rules_scala/blob/master/docs/scala_binary.md), [scala\_library](https://github.com/bazelbuild/rules_scala/blob/master/docs/scala_library.md) | 5.0.0 - 6.6.0 |
| [Rust](https://github.com/bazelbuild/rules_rust) (Beta) | [rust\_binary](https://bazelbuild.github.io/rules_rust/rust.html#rust_binary), [rust\_library](https://bazelbuild.github.io/rules_rust/rust.html#rust_library) | 0.40.0+ |

## Quick target discovery for Bazel projects

Use the following commands to find scannable targets in your repository.

* Java
* Python
* Go
* Scala
* Rust
* All binary targets

```
bazel query 'kind(java_binary, //...)'
```

```
bazel query 'kind(py_binary, //...)'
```

```
bazel query 'kind(go_binary, //...)'
```

```
bazel query 'kind(scala_binary, //...)'
```

```
bazel query 'kind(rust_binary, //...)'
```

```
bazel query 'kind(".*_binary", //...)'
```

### Common query patterns for Bazel projects

Use these common query patterns to find targets.

Run the following command to find all targets in a specific package.

```
bazel query '//your-package:*'
```

Run the following command to find all binary targets across languages.

```
bazel query 'kind(".*_binary", //...)'
```

Run the following command to find targets with specific attributes.

```
bazel query 'attr(visibility, "//visibility:public", //...)'
```

Run the following command to find dependencies of a target.

```
bazel query 'deps(//your-target:name)'
```

Run the following command to find reverse dependencies of a target.

```
bazel query 'rdeps(//..., //your-target:name)'
```

## Scan commands for Bazel projects

The following table lists the common flags and options to scan Bazel projects.

| Flag | Purpose | Example |
| --- | --- | --- |
| `--bazel-include-targets` | Specify targets to scan | `--bazel-include-targets=//app:main` |
| `--bazel-exclude-targets` | Exclude specific targets | `--bazel-exclude-targets=//test:*` |
| `--bazel-targets-query` | Use Bazel query to select targets | `--bazel-targets-query='kind(java_binary, //...)'` |
| `--bazel-workspace-path` | Non-root workspace location | `--bazel-workspace-path=./src/java` |
| `--bazel-vendor-manifest-path` | Go vendored mode `go.mod` path | `--bazel-vendor-manifest-path=./go.mod` |
| `--disable-private-package-analysis` | Skip private package analysis | `--disable-private-package-analysis` |
| `--quick-scan` | Fast scan mode | `--quick-scan` |
| `--bazel-rc-path` | Specify custom paths for Bazel configuration files | `--bazel-rc-path=.custom.bazelrc.user` |
| `—-bazel-flags` | Specify additional command-line flags that should be passed to Bazel when running a scan | `-—bazel-flags=“config=ci, config=dev ,remote_retries=5"` |
| `-o json` | Output format | `-o json | tee results.json` |

### Target selection for Bazel scans

To scan with Endor Labs, you need to specify which targets to analyze using one of two approaches:

* **Specific target list**: Provide a comma-separated list of exact targets using `--bazel-include-targets`.
* **Query-based selection**: Use the Bazel query language to select all targets matching your criteria with `--bazel-targets-query`.

### Quick scan for Bazel projects

Run a fast scan for software composition visibility without reachability analysis.

```
endorctl scan --use-bazel --bazel-include-targets=//your-target-name --quick-scan
```

### Deep scan for Bazel projects

Perform a full analysis with dependency resolution, reachability analysis, and call graphs.

```
endorctl scan --use-bazel --bazel-include-targets=//your-target-name
```

**Private Package Analysis**

When a deep scan is performed, all private software dependencies are completely analyzed by default if they have not been previously scanned. This is a one-time operation and will slow down initial scans, but won’t impact subsequent scans.

### Scan specific targets for Bazel projects

You can scan specific targets in your Bazel project using the `--bazel-include-targets` flag.

Run the following command to scan a single target.

```
endorctl scan --use-bazel --bazel-include-targets=//your-target-name
```

To scan multiple targets, provide a comma-separated list.

```
endorctl scan --use-bazel --bazel-include-targets=//target1,//target2,//target3
```

### Scan using queries for Bazel projects

Use these commands to scan targets based on queries.

* Java
* Python
* Go
* Scala
* Rust
* All binary targets

```
endorctl scan --use-bazel --bazel-targets-query='kind(java_binary, //...)'
```

```
endorctl scan --use-bazel --bazel-targets-query='kind(py_binary, //...)'
```

```
endorctl scan --use-bazel --bazel-targets-query='kind(go_binary, //...)'
```

```
endorctl scan --use-bazel --bazel-targets-query='kind(scala_binary, //...)'
```

```
endorctl scan --use-bazel --bazel-targets-query='kind(rust_binary, //...)'
```

```
endorctl scan --use-bazel --bazel-targets-query='attr(visibility, "//visibility:public", //...)'
```

### Scan Bazel projects with non-root workspace

If your `WORKSPACE` file isn’t at the repository root.

```
endorctl scan --use-bazel \
  --bazel-targets-query='kind(java_binary, //...)' \
  --bazel-workspace-path=./src/java
```

### Scan Bazel projects with Go with Gazelle (Vendored Mode)

For Go projects using Bazel with Gazelle in vendored mode.

```
endorctl scan --use-bazel \
  --bazel-include-targets=//your-go-target \
  --bazel-vendor-manifest-path=./go.mod
```

### Scan Bazel projects with performance optimization

For large codebases, disable private package analysis.

```
endorctl scan --use-bazel \
  --bazel-include-targets=//your-target-name \
  --disable-private-package-analysis
```

### Language-specific information for Endor Labs scans

For detailed information about scanning specific languages:

* [Java](../java/)
* [Python](../python/)
* [Go](../golang/)
* [Scala](../scala/)
* [Rust](../rust/)

## Results of Bazel projects scans

You can save the findings of your scans to a local file or view the findings in the Endor Labs user interface.

### Save findings locally

Run the following command to save the results of a quick scan to a local file.

```
endorctl scan --use-bazel --bazel-include-targets=//your-target-name --quick-scan -o json | tee results.json
```

Run the following command to save the results of a deep scan to a local file.

```
endorctl scan --use-bazel --bazel-include-targets=//your-target-name -o json | tee results.json
```

### View findings in the Endor Labs user interface

To view your scan results in the Endor Labs user interface:

1. Sign in to [Endor Labs user interface](https://app.endorlabs.com) and select **Projects** from the left sidebar.
2. Select the project you want to view and click **Findings** to view your scan results.

For more information, see [Viewing findings in the Endor Labs user interface](../../../managing-projects/view-findings/).

## Troubleshooting Bazel projects scans

Check the following common issues and solutions for Bazel projects scans.

No targets found

Check your query syntax and target types.




Workspace not found

Use `--bazel-workspace-path` flag.




Build failures

Pre-build targets with `bazel build`.




Slow scans

Use `--disable-private-package-analysis`




Go vendored issues

Specify `--bazel-vendor-manifest-path`.

## Feedback

Was this page helpful?

Yes
No

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

Thanks for the feedback. Write to us at support@endor.ai to tell us more.
