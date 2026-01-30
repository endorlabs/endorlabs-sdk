---
url: https://docs.endorlabs.com/releasenotes/previous-releases/release-1-6-92/
title: December 2023 | Endor Labs Docs
downloaded: 2026-01-26 10:09:43
---

December 2023 | Endor Labs Docs



* Type to search...

[Print entire section](/releasenotes/previous-releases/release-1-6-92/_print.html)



# December 2023

We are excited to introduce you to the latest version of Endor Labs and endorctl - v 1.6.92. This release includes several enhancements.

### JavaScript/TypeScript dependency reachability (Beta)

Endor Labs provides superior JavaScript dependency reachability. Apart from analyzing manifest files, Endor Labs enumerates the import statements in your JavaScript code to match the import statements with the pre-installed packages and recursively traverses all files to create a dependency tree with the actual versions that are installed and used in the project.

Endor Labs expertly resolves JavaScript dependencies to identify:

* Dependencies listed in the manifest file but not used by the application
* Dependencies used by the application but not listed in the manifest file
* Dependencies listed in the manifest as transitive but used directly by the application
* Dependencies categorized as test dependencies but used directly by the application

The dependencies used in the source code but not declared in the package’s manifest files are tagged as **Phantom**.

**Note**

Dependency reachability is in the **Beta** phase and is turned off by default. To detect phantom dependencies, run the endorctl scan with the flag `--disable-phantom=false`.

### pnpm package manager support for JavaScript/TypeScript projects (Beta)

Users can now scan the JavaScript projects that have pnpm as their package manager. pnpm 3.0.0 and higher versions are supported.

**Note**

To scan JavaScript projects using pnpm, set the environment variable `ENDOR_PNPM_ENABLED` to `true` and then run the endorctl scan.

### Dependency discovery for Python and Java projects using Bazel

Users can now scan their Java and Python projects using Bazel through the endorctl scan command. You can call the endorctl scan command as a Bazel rule and analyze the dependencies by using the Bazel commands.

You can scan the entire repository or you can only scan specific Java or Python targets using language-specific Bazel rules. You can also use a Bazel query and scan all targets matching your query criteria. This helps in executing incremental scans on your repository and scans only the recently updated targets.

## Feedback

Was this page helpful?

Yes
No

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

Thanks for the feedback. Write to us at support@endor.ai to tell us more.
