---
url: https://docs.endorlabs.com/best-practices/working-with-monorepos/
title: Best Practices: Working with monorepos | Endor Labs Docs
downloaded: 2025-11-20 11:50:22
---

Best Practices: Working with monorepos | Endor Labs Docs



* Type to search...
* ---

[Print entire section](/best-practices/working-with-monorepos/_print.html)



# Best Practices: Working with monorepos

Learn strategies to best work with large monorepos.

Large monorepos are a reality for many organizations. Since monorepos can have anywhere from tens to even hundreds of packages scanning all packages in a monorepo can take significant periods of time. While the time requirements may vary based on your development team and pipeline times, in general, development teams need quick testing times to improve their productivity while security teams need full visibility across a monorepo. These two needs can conflict without performance engineering or an asynchronous scanning strategy. This documentation outlines some performance engineering and scanning strategies for large monorepos.

See [Bazel documentation](../../scan-with-endorlabs/language-scanning/bazel/) if you use a monorepo with Bazel as your primary build system.

## Asynchronous scanning strategies

When scanning a large monorepo, a common approach taken by security teams is to run an asynchronous cron job outside a CI/CD-based environment. This is often the point of least friction but is prohibitive. With this approach, inline blocking of critical issues is not generally possible. We would be remiss not to mention this as a scanning strategy for monorepos but this approach is NOT recommended beyond a step to get initial visibility into a large monorepo.

## Performance Enhancements for inline scanning strategies

The following performance enhancements may be used with Endor Labs to enable the scanning of large monorepos:

### Scoping scans based on changed files

For many CI/CD systems path filters are readily available. For example, with GitHub Actions, [dorny path filters](https://github.com/dorny/paths-filter) is a readily accessible way to establish a set of filters by a path. This is generally the most effective path to handle monorepo deployments but does require the highest level of investment in terms of human time. The human time investment is made up for by the time saved by reducing the need to scan everything on each change.

Based on the paths that change you can scope scans based on the files that have actually changed. For example, you can scan only the packages in a monorepo that are housed under the `ui/` directory when this path has changed by running a scan such as `endorctl scan --include-path=ui/**` when this path has been modified.

Using a path filtering approach each team working in a monorepo would need to be responsible for the packages that they maintain, but generally, each team may be associated with one to several pre-defined directory paths.

### Parallelizing scans for many packages

When scanning a large monorepo organizations can choose to regularly scan the whole monorepo based on the packages or directories they’d like to scan. Different jobs may be created that scan each directory simultaneously.

#### Parallelizing with scoped scans

Using scoped scans for monorepos with multiple parallel include patterns is a common performance optimization for monorepos.

The following example shows parallel GitHub action scan that you can use as a reference.

```
name: Parallel Actions
on:
  push:
    branches: [main]
jobs:
  scan-ui:
    runs-on: ubuntu-latest
    steps:
      - name: UI Endor Labs Scan
        run: endorctl scan --include-path=ui/
  scan-backend:
    runs-on: ubuntu-latest
    steps:
      - name: Backend Endor Labs Scan
        run: endorctl scan --include-path=backend/
```

In this example, the directories `ui/` and `backend/` are both scanned simultaneously and the results are aggregated by Endor Labs. This approach can improve the overall scan performance across a monorepo where each directory can be scanned independently.

To include or exclude a package based on its directory.

```
endorctl scan --include-path="directory/path/"
```

See [scoping scans](../scoping-scans/) for more information on approaches to scoping scans.

#### Parallelizing across languages

For teams that work out of smaller monorepos, it is often most reasonable to parallelize scanning based on the language that is being scanned and performance optimize for individual languages based on need.

Below is an example parallel GitHub action scan that can be used as a reference. In this example, JavaScript and Java are scanned at the same time and aggregated together by Endor Labs. This approach can improve the overall scan performance across a monorepo with multiple languages.

```
name: Parallel Actions
on:
  push:
    branches: [main]
jobs:
  scan-java:
    runs-on: ubuntu-latest
    steps:
      - name: Java Endor Labs Scan
        run: endorctl scan --languages=java
  scan-javascript:
    runs-on: ubuntu-latest
    steps:
      - name: Javascript Endor Labs Scan
        run: endorctl scan --languages=javascript,typescript
```

Run the following command to scan a project for only packages written in TypeScript or JavaScript.

```
endorctl scan --languages=javascript,typescript
```

Run the following command to scan a project for only packages used for packages written in Java.

```
endorctl scan --languages=java
```

Define supported languages as a comma-separated list of the following languages: `c,c#,go,java,javascript,kotlin,php,python,ruby,rust,scala,swift,typescript,swifturl`

## Feedback

Was this page helpful?

Yes
No

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

Thanks for the feedback. Write to us at support@endor.ai to tell us more.
