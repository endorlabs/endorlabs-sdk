---
url: https://docs.endorlabs.com/scan-with-endorlabs/manage-scan-profiles/configure-scanprofile-yaml/
title: Configure scan profile through scanprofile.yaml | Endor Labs Docs
downloaded: 2025-11-20 11:50:47
---

Configure scan profile through scanprofile.yaml | Endor Labs Docs



* Type to search...
* ---

[Print entire section](/scan-with-endorlabs/manage-scan-profiles/configure-scanprofile-yaml/_print.html)



# Configure scan profile through scanprofile.yaml

Learn how to configure scan profile through scanprofile.yaml file

You can create a build tool profile for your Endor Labs scans in each repository to specify the build tools to automatically download for each scan.

Create a new file `.endorctl/scanprofile.yaml` file in the root directory of your repository and specify the required versions of the tools. You can specify the Operating system, architecture, automated scan parameters, language, tool, and install information in the scanprofile.yaml file:

The following snippet shows the overall structure of a `scanprofile.yaml` file with automated scan parameters. See [automated scan parameters](../build-tools/#configure-automated-scan-parameters) to learn more.

```
kind: "AutomatedScanParameters"
spec:
    languages:
      - java
    call_graph_languages:
      - java
    additional_environment_variables:
      - ENDOR_LOG_VERBOSE=true
      - ENDOR_LOG_LEVEL=debug
    enable_automated_pr_scans: true
    enable_pr_comments: true
    enable_sast_scan: true
    disable_code_snippet_storage: true
    bazel_configuration:
      bazel_show_internal_targets: true
      bazel_workspace_path: "go-bazel-repo/"
      bazel_include_targets:
        - "//cmd:cmd"
```

The following example shows a scan profile to scan `Java` and Bazel projects in CI with `Maven 3.9.4`, custom environment variables, and support for both Linux and macOS toolchains.

```
kind: "AutomatedScanParameters"
spec:
    languages:
      - java
    additional_environment_variables:
      - ENDOR_LOG_VERBOSE=true
      - ENDOR_LOG_LEVEL=debug
    enable_automated_pr_scans: true
    enable_pr_comments: true
    enable_sast_scan: true
    disable_code_snippet_storage: true
    bazel_configuration:
      bazel_show_internal_targets: true
      bazel_workspace_path: "go-bazel-repo/"
      bazel_include_targets:
        - "//cmd:cmd"


---
kind: "ToolchainProfile"
spec:
  os:
    linux:
      arch:
        amd64:
          java_tool_chain:
            version:
              name: "1.8.412"
              urls:
                - "https://builds.openlogic.com/downloadJDK/openlogic-openjdk/8u412-b08/openlogic-openjdk-8u412-b08-linux-x64.tar.gz"
              relative_tool_chain_path: "openlogic-openjdk-8u412-b08-linux-x64/"
              sha256_sum: "eb06c9d62e031e3290f499a828cae66d4fadbf62eb8f490c63c8406b1a80172e"
            maven_version:
              name: "3.9.4"
              urls:
                - "https://repo1.maven.org/maven2/org/apache/maven/apache-maven/3.9.4/apache-maven-3.9.4-bin.tar.gz"
              relative_tool_chain_path: "apache-maven-3.9.4"
              sha256_sum: "ff66b70c830a38d331d44f6c25a37b582471def9a161c93902bac7bea3098319"
    darwin:
      arch:
        arm64:
          java_tool_chain:
            version:
              name: "1.8.412"
              urls:
                - "https://builds.openlogic.com/downloadJDK/openlogic-openjdk/8u412-b08/openlogic-openjdk-8u412-b08-mac-x64.zip"
              relative_tool_chain_path: "openlogic-openjdk-8u412-b08-mac-x64/jdk1.8.0_412.jdk/Contents/Home"
              sha256_sum: "a16d297418f6800dfc5abfd4dfd8a16c0504d7e1f3b6fc9051cf2460f14a955e"
            maven_version:
              name: "3.9.4"
              urls:
                - "https://repo1.maven.org/maven2/org/apache/maven/apache-maven/3.9.4/apache-maven-3.9.4-bin.tar.gz"
              relative_tool_chain_path: "apache-maven-3.9.4"
              sha256_sum: "ff66b70c830a38d331d44f6c25a37b582471def9a161c93902bac7bea3098319"
```

## Feedback

Was this page helpful?

Yes
No

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

Thanks for the feedback. Write to us at support@endor.ai to tell us more.
