---
url: https://docs.endorlabs.com/scan-with-endorlabs/language-scanning/c/
title: C/C++ | Endor Labs Docs
downloaded: 2026-01-26 10:05:38
---

C/C++ | Endor Labs Docs



* Type to search...

[Print entire section](/scan-with-endorlabs/language-scanning/c/_print.html)



# C/C++

Learn how to implement Endor Labs in C and C++ repositories.

Beta

C and C++ are powerful, high-performance programming languages widely used for system programming, application development, and embedded systems. Endor Labs supports scanning and monitoring of C and C++ projects.

Using Endor Labs, application security engineers and developers can:

* Scan their software for potential security issues and violations of organizational policy.
* Prioritize vulnerabilities in the context of their applications.
* Understand the relationships between software components in their applications.

## Run a scan

To scan your C and C++ repositories, run the following command.

```
endorctl scan --languages=c
```

**Important**

* Ensure that the entire source code and all its dependencies are present in the scanned folder.
* Using the `--languages=c` flag will scan only C and C++ projects. For a multi-language repository, ensure that you include all other languages with the flag.
* If you are using a [scan profile](../../manage-scan-profiles/configure-scanprofile-ui/), make sure **C/C++** is selected under **Languages** and included in your profile.

Use the following flags to save the local results to a *results.json* file. The results and related analysis information are available on the Endor Labs user interface.

```
endorctl scan --languages=c -o json | tee /path/to/results.json
```

### View scan results

You can sign in to the [Endor Labs user interface](https://app.endorlabs.com), click the **Projects** on the left sidebar, and find your project to review its results.

![View scan results](../../../images/c_potentially_reachable.png)

## Understand the scan process

Endor Labs detects vulnerabilities by testing your code against its proprietary database, which is regularly updated. Endor Labs does not build your code, so all dependencies and vendor code must be included within the source. If the build process pulls in additional packages, they must also be present in the scanned directory.

Endor Labs analyzes source code using a combination of code signatures and embeddings. The system extracts source code from various data sources and applies language-specific segmentation to break the code into functions and segments. This method facilitates efficient similarity searches, helping to detect duplicated code across repositories and supporting comprehensive software composition analysis.

By comparing file hashes, segment hashes, and embeddings, Endor Labs can query data to identify matches with code segments. This capability streamlines the detection of copied code and the dependency relationships between repositories, providing insights into code components from various sources, including Git repositories, online archives, and other package distributions. Headers and code files are scanned regardless of their file extension.

To optimize performance, Endor Labs caches embeddings and signatures, making subsequent scans faster than the first scan. This means only newly added or modified files require computation, significantly reducing scan times.

### Enable code segment embeddings

Embeddings are disabled by default and require the Endor Labs AI license.

To enable embeddings go to **Settings** near the bottom of the left sidebar, navigate to **Data Privacy** under **System Settings**, check the box for **Code Segment Embeddings and LLM Processing** and click **Save Data Privacy Settings**.

![Enable embeddings](../../../images/enable-embeddings.png)

To override the system-wide configuration for a specific scan, set `ENDOR_SCAN_EMBEDDINGS` to `true` to enable embeddings or `false` to disable them. This setting takes precedence over the system configuration.

```
export ENDOR_SCAN_EMBEDDINGS=false
```

### Limitations

Scanning binary library files such as `.so` and `.a` files is not supported.

## Feedback

Was this page helpful?

Yes
No

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

Thanks for the feedback. Write to us at support@endor.ai to tell us more.
