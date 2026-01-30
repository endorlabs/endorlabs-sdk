---
url: https://docs.endorlabs.com/scan-with-endorlabs/language-scanning/rust/
title: Rust | Endor Labs Docs
downloaded: 2026-01-26 10:09:50
---

Rust | Endor Labs Docs



* Type to search...

[Print entire section](/scan-with-endorlabs/language-scanning/rust/_print.html)



# Rust

Learn how to implement Endor Labs in repositories with Rust packages.

Rust is a software programming language widely used by developers. Endor Labs supports scanning and monitoring of Rust projects.

Using Endor Labs, application security engineers and developers can:

* Scan their software for potential security issues and violations of organizational policy.
* Prioritize vulnerabilities in the context of their applications.
* Understand the relationships between software components in their applications.

## System specifications for scan

Make sure that you have a minimum system requirement specification of an 8-core processor with 32 GB RAM.

Use a system equipped with either Mac OS X or Linux operating systems to perform the scans.

## Software prerequisites

* Make sure the following prerequisites are installed:
  - Package Manager Cargo - Any version
  - Rust - Any version,
* Make sure your repository includes one or more files with `.rs` extension.
* Install Rust using the latest [rustup](https://www.rust-lang.org/tools/install) tool.

## Build Rust projects

Ensure your repository has `Cargo.toml` file and run the following command making sure it builds the project successfully.

```
cargo build
```

If the project is not built, endorctl will build the project during the scan and generate the `Cargo.lock` file. If the repository includes a `Cargo.lock` file, endorctl uses this file for dependency resolution and does not create it again.

## Run a scan

Perform a scan to get visibility into your software composition and resolve dependencies.

```
endorctl scan
```

You can perform the scan from within the root directory of the Git project repository, and save the local results to a *results.json* file. The results and related analysis information are available on the Endor Labs user interface.

```
endorctl scan -o json | tee /path/to/results.json
```

You can sign in to the Endor Labs user interface, click the **Projects** on the left sidebar, and find your project to review its results. Refer to [Endor Labs user interface](https://app.endorlabs.com) for more details.

## Understand the scan process

Endor Labs resolves dependencies for the package version when it scans Rust projects.

### Resolving Dependencies

Endor Labs leverages the Cargo.toml file in Rust and uses this file to build the package version using cargo. Endor Labs uses the output from `cargo metadata` to resolve dependencies specified in Cargo.toml files and construct the dependency graph.

### Known Limitations

* Call graphs are not supported for Rust projects.
* Performing Endor Labs scans on the Microsoft Windows operating system is currently unsupported.

## Troubleshoot errors

* **Host system check failure errors**:
  These errors occur when Rust is not installed or not present in the path variable. Install Rust and try again.

## Feedback

Was this page helpful?

Yes
No

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

Thanks for the feedback. Write to us at support@endor.ai to tell us more.
