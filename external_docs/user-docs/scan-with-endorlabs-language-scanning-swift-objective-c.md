---
url: https://docs.endorlabs.com/scan-with-endorlabs/language-scanning/swift-objective-c/
title: Swift/Objective-C | Endor Labs Docs
downloaded: 2025-12-11 11:35:05
---

Swift/Objective-C | Endor Labs Docs



* Type to search...
* ---

[Print entire section](/scan-with-endorlabs/language-scanning/swift-objective-c/_print.html)



# Swift/Objective-C

Learn how to implement Endor Labs in repositories with CocoaPods and Swift Package Manager (SwiftPM) packages.

CocoaPods and SwiftPM are widely adopted package managers for Swift and Objective-C. CocoaPods simplifies integration via `Podfile` declarations and automated installation, while SwiftPM manages dependencies through the `Package.swift` manifest. Endor Labs supports both systems to help secure your applications.

Using Endor Labs, application security engineers and developers can:

* Scan their software for potential security issues and violations of organizational policy.
* Prioritize vulnerabilities in the context of their applications.
* Understand the relationships between software components in their applications.

## Software prerequisites

The following prerequisites must be fulfilled:

* All applications monitored by Endor Labs must be on CocoaPods versions 0.9.0 or higher, or Swift Package Manager versions 5.0.0 or higher.
* A `Podfile` and a `Podfile.lock` must be present in your CocoaPods project.
* A `Package.swift` must be present in your SwiftPM project.
* Make sure your repository includes one or more files with `.swift`, `.h`, or `.m` extension.
* The Swift toolchain must be installed on the system running the scan for SwiftPM projects. To verify the installation, run the `swift --version` command.

## Build CocoaPods projects

If the `Podfile.lock` is not present in your repository, run the following command to create the `Podfile.lock` for your Podfile.

```
pod install
```

## Run a scan

Perform a scan to get visibility into your software composition and resolve dependencies.

```
endorctl scan
```

You can perform the scan from within the root directory of the Git project repository, and save the local results to a *results.json* file. The results and related analysis information are available on the Endor Labs user interface.

```
endorctl scan -o json | tee /path/to/results.json
```

You can sign into the [Endor Labs user interface](https://app.endorlabs.com), click the **Projects** on the left sidebar, and find your project to review its results.

## Understand the scan process for CocoaPods projects

Endor Labs looks for the `Podfile` and `Podfile.lock` files to discover the dependencies used by an application.

* A `Podfile` is a configuration file used in CocoaPods projects to specify the required libraries or packages for the project’s dependencies.
* A `Podfile.lock` file is a CocoaPods specification file used to define the metadata and dependencies.

To successfully discover Swift and Objective-C dependencies, both `Podfile` and `Podfile.lock` files must be present in your project for each Podfile.

## Understand the scan process for SwiftPM projects

Endor Labs scans SwiftPM projects by locating the `Package.swift` manifest file, which defines the Swift package’s dependencies, targets, and metadata. Version-specific manifest files using the format `Package@swift-<version>.swift`, for example `Package@swift-5.7.swift`, are also supported.

### Configure private SwiftPM package repositories

Endor Labs supports fetching and scanning dependencies from private Swift package registries. Endor Labs will fetch resources from authenticated endpoints and perform the scan, allowing you to view the resolved dependencies and findings. See [Swift package manager integrations](../../../integrations/package-manager/swift-private-package-manager/) for more information on configuring private registries.

## Known limitations

* Call graphs are not supported for CocoaPods and SwiftPM projects.
* If a `Podfile.lock` file is not present, Endor Labs will skip analyzing the project and present a warning that the package was skipped.

## Feedback

Was this page helpful?

Yes
No

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

Thanks for the feedback. Write to us at support@endor.ai to tell us more.
