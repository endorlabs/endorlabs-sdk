---
url: https://docs.endorlabs.com/scan-with-endorlabs/language-scanning/javascript/
title: JavaScript/TypeScript | Endor Labs Docs
downloaded: 2026-02-03 00:50:09
---

JavaScript/TypeScript | Endor Labs Docs



* Type to search...

[Print entire section](/scan-with-endorlabs/language-scanning/javascript/_print.html)



# JavaScript/TypeScript

Learn how to implement Endor Labs in repositories with JavaScript or TypeScript packages.

JavaScript is a high-level, interpreted programming language primarily used for creating interactive and dynamic web content widely used by developers. Endor Labs supports the scanning and monitoring of JavaScript projects.

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

### Software prerequisites

* Endor Labs requires the following pre-requisite software to be installed to successfully perform a scan:
  + Yarn: Any version
  + npm: 6.14.18 or higher versions
  + pnpm: 3.0.0 or higher versions
* Make sure your repository includes one or more files with `.js` or `.ts` extension.

To run deep scanning for JavaScript and TypeScript projects make sure you have the following prerequisites installed:

* Ensure you have endorctl version 1.7.0 or higher installed.
* Ensure Node.js version 4.2.6 or higher is installed to support TypeScript version 4.9.
* Ensure TypeScript version 4.9 or higher is installed.
* Install `tsserver`. `tsserver` is included with TypeScript, so installing the appropriate TypeScript version automatically installs `tsserver`.

  Install the appropriate TypeScript version based on your Node.js version.

| Nodejs Version | TypeScript Version |
| --- | --- |
| Lower than 12.2 | 4.9 or higher |
| Between 12.2 and 14.17 | 5.0 |
| Higher than or equal to 14.17 | Latest |

* Use the following command based on your Node.js version to install typescript:

* 14.17 or higher
* Between 12.2 and 14.17
* Lower than 12.2

```
npm install -g typescript
```

```
npm install -g typescript@5.0
```

```
npm install -g typescript@4.9
```

* If you’re unsure make sure you check the `tsserver` installation

```
# Run 'which tsserver' to confirm installation
which tsserver
```

If you are running the endorctl scan with `--install-build-tools`, you don’t need to install `tsserver`. See [Configure build tools](../../manage-scan-profiles/build-tools/) for more information.

### Build JavaScript projects

You can choose to build your JavaScript projects before running a scan. This will ensure that either a `package-lock.json`, `yarn.lock`, or `pnpm-lock.yaml` file is created enhancing the scan speed.

Ensure your repository has `package.json` and run the following command making sure it builds the project successfully.

* For npm
* For Yarn
* For pnpm

```
`npm install`
```

```
`yarn install`
```

```
`pnpm install`
```

If the project is not built, endorctl builds the project during the scan and generate either package-lock.json, yarn.lock, or pnpm-lock.yaml file. Make sure that either npm, Yarn, or pnpm is installed on your system. If your repository includes a lock file, endorctl uses the existing file for dependency resolution and does not create it again.

The `npm install` command may fail in a subdirectory if your project is set up with a `package-lock.json` file available at the root of the repository and not in the sub-packages as shown in the following example.

```
 .
 ├── package.json
 ├── package-lock.json
 └── sub-package/
     └── package.json
```

You need to instruct endorctl to use the root-level lock file to avoid scan failures in monorepo setups where dependencies are centrally managed at the root.

Set the following environment variable before you run the scan.

```
export ENDOR_JS_USE_ROOT_DIR_LOCK_FILE=true
```

### Configure call graph generation timeout

When generating call graphs for JavaScript/TypeScript projects, endorctl uses `tsserver` to analyze the code. By default, `tsserver` waits 15 seconds for a response before timing out. For large or complex projects, you may need to increase this timeout.

Set the `ENDOR_JS_TSSERVER_TIMEOUT` environment variable to specify the timeout in seconds.

```
export ENDOR_JS_TSSERVER_TIMEOUT=30
```

Increasing the timeout might be beneficial in the following scenarios:

* Large monorepos with many TypeScript files
* Projects with complex type hierarchies
* Projects with extensive type checking requirements

### Override JavaScript package manager detection

endorctl detects the JavaScript package manager automatically. You can override this detection by setting the `ENDOR_JS_PACKAGE_MANAGER` environment variable to `npm`, `yarn`, `pnpm`, or `lerna`.

For example, to use `npm`as the package manager run the following command.

```
export ENDOR_JS_PACKAGE_MANAGER=npm
```

This setting forces endorctl to use the specified package manager and overrides all other JavaScript package manager configuration variables.

## Run a scan

Perform a scan to get visibility into your software composition and resolve dependencies.

```
endorctl scan
```

### Understand the scan process

Dependency analysis tools analyze the lock file of an npm, yarn, or pnpm based package and attempt to resolve dependencies. To resolve dependencies from private repositories, the settings of the `.npmrc` file in the repository is considered.

Endor Labs surpasses mere manifest file analysis by expertly resolving JavaScript dependencies and identifies:

* Dependencies listed in the manifest file but not used by the application
* Dependencies used by the application but not listed in the manifest file
* Dependencies listed in the manifest as transitive but used directly by the application
* Dependencies categorized as test in the manifest, but used directly by the application

Developers can eliminate the false positives, false negatives, and easily identify test dependencies with this analysis. The dependencies used in source code but not declared in the package’s manifest files are tagged as **Phantom**.

Endor Labs also supports npm, Yarn, and pnpm workspaces out-of-the-box. If your JavaScript frameworks and packages use workspaces, Endor Labs will automatically take the dependencies from the workspace to ensure that the package successfully builds.

Scan speed is enhanced if the lock file exists in the repository. endorctl does not perform a build and uses the existing files in the repository for analysis.

### Configure private npm package repositories

Endor Labs supports fetching and scanning dependencies from private npm package registries. Endor Labs will fetch resources from authenticated endpoints and perform the scan, allowing you to view the resolved dependencies and findings. See [npm package manager integrations](../../../integrations/package-manager/npm-private-package-manager/) for more information on configuring private registries.

### Known Limitations

* Endor Labs doesn’t currently support local package references
* If a dependency can not be resolved in the lock file, building that specific package may be unsuccessful. This package may have been removed from npm or the `.npmrc` file is not properly configured. Other packages in the workspace are scanned as usual.

#### Call graph limitations

* Functions that are passed in as arguments to call expressions might not be included in the call graph.
* Functions that are returned and then called might not be included in the call graph.
* Functions that are assigned to a variable based on a runtime value might not be included in the call graph.
* Functions that are assigned to an array element might not be included in the call graph.

### Troubleshoot errors

* **Unresolved dependency errors**:
  The manifest file `package.json` is not buildable. Try running `npm install`, `yarn install`, or `pnpm install` in the root project to debug this error.
* **Resolved dependency errors**:
  A version of a dependency does not exist or it cannot be found. It may have been removed from the repository.

## Feedback

Was this page helpful?

Yes
No

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

Thanks for the feedback. Write to us at support@endor.ai to tell us more.
