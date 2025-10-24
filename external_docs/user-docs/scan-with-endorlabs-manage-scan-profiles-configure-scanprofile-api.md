---
url: https://docs.endorlabs.com/scan-with-endorlabs/manage-scan-profiles/configure-scanprofile-api/
title: Configure scan profile through Endor Labs API | Endor Labs Docs
downloaded: 2025-10-23 23:26:15
---

Configure scan profile through Endor Labs API | Endor Labs Docs



* Type to search...
* ---

[Print entire section](/scan-with-endorlabs/manage-scan-profiles/configure-scanprofile-api/_print.html)



# Configure scan profile through Endor Labs API

Learn how to configure scan profile through Endor Labs API

You can use the `endorctl api` command to configure the toolchains for your project.

1. Run the endorctl scan to create a project in Endor Labs.

   ```
   endorctl scan
   ```
2. Fetch the UUID of the project. For example, to fetch the UUID of `app-java-demo` project, you can use:

   ```
   UUID=$(endorctl api list -r Project --filter="meta.name matches https://github.com/endorlabs/app-java-demo" --field-mask=uuid | jq -r '.list.objects[].uuid')
   ```
3. Create a `ScanProfile` object using the following command. Set the environment variable using `set EDITOR=vim` before executing the following command.

   ```
   endorctl api create -i -r ScanProfile
   ```

   You can configure automated scan parameters in your scan profile. See [automated scan parameters](../build-tools/#configure-automated-scan-parameters) to learn more.

   Here is an example that you can use to create a `ScanProfile` object for installing `Java 8` and `Maven 3.9.4` in Linux and macOS. After executing this command, you can fetch the UUID of the `ScanProfile` object. See [toolchain support matrix](../build-tools/#toolchain-support-matrix) for a complete description of supported toolchains.

   ```
   meta:
     name: "demo"
   spec:
     automated_scan_parameters:
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
     toolchain_profile:
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
4. Associate the `scan_profile_uuid` to your project UUID `project-uuid` using the following command.

   ```
   endorctl api update -r Project --uuid=<project-uuid> -d '{"spec":{"scan_profile_uuid":"<scanprofile-uuid>"}}' --field-mask 'spec.scan_profile_uuid'
   ```

## Feedback

Was this page helpful?

Yes
No

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

Thanks for the feedback. Write to us at support@endor.ai to tell us more.
