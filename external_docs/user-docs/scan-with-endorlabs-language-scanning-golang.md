---
url: https://docs.endorlabs.com/scan-with-endorlabs/language-scanning/golang/
title: Go | Endor Labs Docs
downloaded: 2025-11-20 11:49:15
---

Go | Endor Labs Docs



* Type to search...
* ---

[Print entire section](/scan-with-endorlabs/language-scanning/golang/_print.html)



# Go

Learn how to implement Endor Labs in repositories with Go packages.

Go or Golang is a software development programming language widely used by developers. Endor Labs supports scanning and monitoring of Go projects.

Using Endor Labs, application security engineers and developers can:

* Scan their software for potential security issues and violations of organizational policy.
* Prioritize vulnerabilities in the context of their applications.
* Understand the relationships between software components in their applications.

## System specifications for deep scan

Before you proceed to run a deep scan, ensure that your system meets the following specification.

| Project Size | Processor | Memory |
| --- | --- | --- |
| Small projects | 4-core processor | 16 GB |
| Mid-size projects | 8-core processor | 32 GB |
| Large projects | 16-core processor | 64 GB |

## Software prerequisites

* Make sure that you have Go 1.12 or higher versions.
* Make sure your repository includes one or more files with `.go` extension.

## Build Go projects

You must build your Go projects before running the scan. Additionally, ensure that the packages are downloaded into the local package caches and that *go.mod* file well formed and is available in the standard location.

To ensure that your go.mod file is well formed, run the following command:

```
go mod tidy
```

```
go get ./
```

This removes any dependencies that are not required by your project and ensures to resolve the dependencies without errors.

## Run a scan

Use the following options to scan your repositories. Perform the endorctl scan after building the projects.

### Option 1 - Quick scan

Perform a quick scan to get quick visibility into your software composition. This scan won’t perform reachability analysis to help you prioritize vulnerabilities.

```
endorctl scan --quick-scan
```

You can perform the scan from within the root directory of the Git project repository, and save the local results to a *results.json* file. The results and related analysis information are available on the Endor Labs user interface.

```
endorctl scan --quick-scan -o json | tee /path/to/results.json
```

You can sign into the [Endor Labs user interface](https://app.endorlabs.com), click the **Projects** on the left sidebar, and find your project to review its results.

### Option 2 - Deep scan

Use the deep scan to perform dependency resolution, reachability analysis, and generate call graphs. You can do this after you complete the quick scan successfully.

```
endorctl scan
```

Use the following flags to save the local results to a *results.json* file. The results and related analysis information are available on the Endor Labs user interface.

```
endorctl scan -o json | tee /path/to/results.json
```

You can sign into the [Endor Labs user interface](https://app.endorlabs.com), click the **Projects** on the left sidebar, and find your project to review its results.

## Understand the scan process

Endor Labs resolves your Golang-based dependencies by leveraging built-in Go commands to replicate the way a package manager would install your dependencies.

To discover package names for Go packages Endor Labs uses the command:

```
GOMOD=off go list -e -mod readonly -json -m
```

To analyze the dependency graph of your package Endor Labs uses the command:

```
GOMOD=off go list -e -deps -json -mod readonly all
```

To assess external dependencies, specifically third-party packages or libraries that your Go project relies on, Endor Labs uses the command:

```
GOMOD=off go list -e -deps -json -mod vendor all
```

These commands allow us to assess packages’ unresolved dependencies, analyze the dependency tree, and resolve dependencies for your Go projects.

### Known Limitations

Endor Labs creates go.mod files for you when projects do not have a go.mod file. This can lead to inconsistencies with the actual package created over time and across versions of the dependencies.

## Troubleshoot errors

Here are a few error scenarios that you can check for and attempt to resolve them.

* **Host system check failure errors**:

  + Go is not installed or not present in the PATH environment variable. Install Go and try again.
  + The installed version of Go is lower than 1.12. Install Go version 1.12 or higher and try again.
* **Resolved dependency errors**:

  + A version of a dependency does not exist or it cannot be found. It may have been removed from the repository.
  + If the go.mod file is not well-formed then dependency resolution may return errors. Run `go mod tidy` and try again.
* **Call graph errors**:

  These errors often mean the project won’t build. Please ensure any generated code is in place and verify that `go build ./...` runs successfully.

## Feedback

Was this page helpful?

Yes
No

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

Thanks for the feedback. Write to us at support@endor.ai to tell us more.
