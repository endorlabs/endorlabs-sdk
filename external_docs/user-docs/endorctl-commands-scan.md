---
url: https://docs.endorlabs.com/endorctl/commands/scan/
title: scan | Endor Labs Docs
downloaded: 2026-01-29 22:20:55
---

scan | Endor Labs Docs



* Type to search...

[Print entire section](/endorctl/commands/scan/_print.html)



# scan

Use the scan command to perform endorctl scan.

Use the `scan` command to perform scans against a repository.

## Usage

To perform a full scan including reachability analysis for the open source software of the packages you build in a repository and monitor the checked out version of your code run the command.

```
endorctl scan
```

If your project contains multiple programming languages, you can specify them as a comma-separated list using the `--languages` flag:

```
endorctl scan --languages=<languages-list>
```

Where `<languages-list>` should be provided as a comma-separated list from the supported languages: `c,c#,go,java,javascript,kotlin,php,python,ruby,rust,scala,swift,typescript,swifturl`.

To scan leaked secrets and monitor all results in the checked out version of your repository.

```
endorctl scan --secrets
```

Run the following command to perform a regular scan for leaked secrets including the dependencies.

```
endorctl scan --secrets --dependencies
```

Run the following can to scan for leaked secrets in all branches of your repository.

```
endorctl scan --secrets --git-logs
```

The above command performs a scan of the repository’s Git logs using the following logic:

* If it is the first time the repository’s Git log history is scanned, it performs a full scan
* A full rescan is also performed if a change has been detected to any of the rules in the namespace
* In all other cases, the scan is incremental based on the last time a scan was performed.

If the system invalidates any detected secrets, and you want to run the validators again so that the findings page properly reflects the secret state, you can force a full rescan by using the following command.

To scan for misconfigurations in a GitHub repository like <https://github.com/endorlabs/app-java-demo>.

```
export GITHUB_TOKEN=<insert-your-github-token>
endorctl scan --github --repository-http-clone-url=https://github.com/endorlabs/app-java-demo
```

To run a scan as a test in a pull request without monitoring the version of your code over time run the command.

```
endorctl scan --pr
```

To scan and discover GitHub action workflows in your CI/CD pipeline run the command.

```
endorctl scan --ghactions
```

Along with performing the regular dependency analysis on your repository, it discovers the GitHub Actions configured in your CI/CD pipeline and maps them as GitHub action dependencies in your package.

To scan binaries and artifacts run the following command.

```
endorctl scan --package --path --project-name
```

You must provide the path of your file using `--path` and specify a name for your project using `--project-name`.

To scan and discover AI/LLM models in your repository, run the following command

```
endorctl scan --ai-models --dependencies
```

To run a scan in dry run mode with local scanning and read-only access, run the following command. Dry run mode does not store scan results for monitoring and is best when used by developers running local scans.

```
endorctl scan --dependencies --dry-run
```

You can also use `--dry-run` with `--secrets` or `--sast` flags. The `--dry-run` flag cannot be used with container scanning.

## Options

The command `endorctl scan` uses the following flags and environment variables:

### Bazel flags

| Flag | Environment Variable | Type | Description |
| --- | --- | --- | --- |
| `bazel-exclude-targets` | `ENDOR_SCAN_BAZEL_EXCLUDE_TARGETS` | comma-separated string | Set this variable to exclude a list of Bazel targets included in a provided Bazel query. |
| `bazel-include-targets` | `ENDOR_SCAN_BAZEL_INCLUDE_TARGETS` | comma-separated string | Set this variable to scan a list of targets using Bazel. Only the specified list of targets are scanned. If you do not specify `bazel-include-targets`, you must identify targets using `bazel-targets-query`. If you specify targets, then the results from `bazel-targets-query` are ignored. |
| `bazel-show-internal-targets` | `ENDOR_SCAN_BAZEL_SHOW_INTERNAL_TARGETS` | boolean (default:false) | Show internal targets as py\_library, java\_library and go\_library as dependencies. Must be used together with `--use-bazel`. |
| `bazel-targets-query` | `ENDOR_SCAN_BAZEL_TARGETS_QUERY` | string | Set this variable to query for a list of Bazel targets to include in a scan. |
| `bazel-vendor-manifest-path` | `ENDOR_SCAN_BAZEL_VENDOR_MANIFEST_PATH` | string | Set this variable to specify the path of the `go.mod` file if you use Bazel with Gazelle in vendored mode for Go projects. |
| `bazel-workspace-path` | `ENDOR_SCAN_BAZEL_WORKSPACE_PATH` | string | Set this variable to specify the path of the Bazel workspace. |
| `use-bazel` | `ENDOR_SCAN_USE_BAZEL` | boolean (default:false) | Use Bazel to perform the endorctl scan. |
| `bazel-rc-path` | `ENDOR_SCAN_BAZEL_RC_PATH` | string | Specify custom paths for Bazel configuration files. Specify comma-separated paths relative to the repository root. If multiple `.bazelrc` files are provided and contain conflicting configuration options, the configuration in the last file listed takes precedence. See [Bazel documentation](https://bazel.build/run/bazelrc#bazelrc-file-locations) for details about `.bazel.rc` file locations. |
| `bazel-flags` | `ENDOR_SCAN_BAZEL_FLAGS` | string | Specify additional command-line flags that should be passed to Bazel when running a scan. Specify Comma-separated key-value pairs in the format `key=value`. These flags are applied to `bazel build`. |

### Pull request (CI) flags

| Flag | Environment Variable | Type | Description |
| --- | --- | --- | --- |
| `enable-pr-comments` | `ENDOR_SCAN_ENABLE_PR_COMMENTS` | boolean (default:false) | Publish new findings as review comments. Must be set together with `--scm-pr-id`, `--pr`, and either `--github-token` (for GitHub) or `--scm-token` (for GitLab). Cannot be used with `--pr-baseline` since the baseline is determined from the merge target of the PR. Note: You can continue to use `--github-pr-id` flag, but it will be deprecated and removed in the future. |
| `scm-pr-id` | `ENDOR_SCAN_SCM_PR_ID` | string | Set the PR or MR ID corresponding to the scan. Must be set together with `--enable-pr-comments`, `--pr`, and either `--github-token` (for GitHub) or `--scm-token` (for GitLab). |
| `pr` | `ENDOR_SCAN_PR` | boolean (default:false) | Set if this is a PR scan. PR scans are not used for reporting or monitoring and should be treated as point-in-time policy and finding tests. |
| `pr-baseline` | `ENDOR_SCAN_PR_BASELINE` | string | Set to the Git reference that you are merging to, such as your default branch. Action policies will only flag issues that do not exist in the baseline so that developers are only alerted to issues on the current changes. For example, `--pr-baseline=main`. |
| `pr-incremental` | `ENDOR_SCAN_PR_INCREMENTAL` | boolean (default:false) | Only scan packages with dependencies that have changed compared to the baseline scan. Must be set together with `--pr-baseline` or `--enable-pr-comments`. |
| `scm-token` | `ENDOR_SCAN_SCM_TOKEN` | string | Set the GitLab token used to authenticate with GitLab for MR comments. Must be set together with `--enable-pr-comments`, `--scm-pr-id`, and `--pr`. The token takes priority over installation PATs. |

### GitHub configuration flags

| Flag | Environment Variable | Type | Description |
| --- | --- | --- | --- |
| `github` | `ENDOR_SCAN_GITHUB` | boolean (default:false) | Fetch information from GitHub and generate findings for any GitHub misconfigurations (see also [RSPM policies](../../../managing-policies/finding-policies/managing-scm-configuration/)). |
| `github-api-url` | `GITHUB_API_URL` | string | Set the GitHub API URL used for API requests to GitHub Enterprise Cloud or GitHub Enterprise Server. **This flag must be used for self-hosted source control systems such as GitHub Enterprise Server.** (default `https://api.github.com/`) |
| `github-ca-path` | `GITHUB_CA_PATH` | string | Set the path to the CA certificate used by GitHub Enterprise Server if it is untrusted by your system. |
| `g`, `github-token` | `GITHUB_TOKEN` | string | Set the GitHub token used to authenticate with GitHub. |
| `repository-http-clone-url` | `ENDOR_SCAN_GITHUB_REPOSITORY_HTTP_CLONE_URL` | string | Set the GitHub repository HTTP clone URL for `--github` scans. |

### Call graph flags

| Flag | Environment Variable | Type | Description |
| --- | --- | --- | --- |
| `build` | `ENDOR_SCAN_BUILD` | boolean (default:false) | Enable the scan to build the project if needed. |
| `call-graph-languages` | `ENDOR_SCAN_CALLGRAPH_LANGUAGES` | strings | Set programming languages for call graph generation. Supported languages are C#, Go, Java, JavaScript, Kotlin, Python, Rust, Scala, and TypeScript. By default, the call graphs are generated for all supported languages. |
| `disable-private-package-analysis` | `ENDOR_SCAN_DISABLE_PRIVATE_PACKAGE_ANALYSIS` | boolean (default:false) | Disable the call graph analysis of private dependencies that are not part of the repository. |
| `quick-scan` | `ENDOR_SCAN_QUICK_SCAN` | boolean (default:false) | Perform a quick scan without call graph generation. |

### Policy flags

| Flag | Environment Variable | Type | Description |
| --- | --- | --- | --- |
| `exit-on-policy-warning` | `ENDOR_SCAN_EXIT_ON_POLICY_WARNING` | boolean (default: false) | Return a non-zero exit code if there are policy violation warnings. |

### Secrets scan flags

| Flag | Environment Variable | Type | Description |
| --- | --- | --- | --- |
| `force-rescan` | `ENDOR_SCAN_FORCE_RESCAN` | boolean (default:false) | Force a full rescan of the historical Git logs for all branches in the repository. Must be used together with `--secrets`. |
| `git-logs` | `ENDOR_SCAN_GIT_LOGS` | boolean (default:false) | Audit the historical Git logs of the repository for all branches in the repository. Must be used together with `--secrets`. |
| `local` | `ENDOR_SCAN_LOCAL` | boolean (default:false) | Scan the local filesystem. Must be used together with `--secrets`. |
| `start-commit` | `ENDOR_SCAN_START_COMMIT` |  | The start commit of the Git logs of the repository to start scanning from. Must be used together with `--secrets` and `--end-commit`. |
| `end-commit` | `ENDOR_SCAN_END_COMMIT` |  | The end commit of the Git logs of the repository to end scanning at. Must be used together with `--secrets` and `--start-commit`. |
| `pre-commit-checks` | `ENDOR_SCAN_PRE_COMMIT_CHECKS` | boolean (default:false) | Perform Git pre-commit checks on the changeset about to be committed. Must be used together with `--secrets`. |
| `secrets` | `ENDOR_SCAN_SECRETS` | boolean (default:false) | Scan source code repository and generate findings for leaked secrets. See also `--git-logs` and `--pre-commit-checks`. |

### SAST scan flags

| Flag | Environment Variable | Type | Description |
| --- | --- | --- | --- |
| `sast` | `ENDOR_SCAN_SAST` | boolean (default:false) | Scan for weaknesses in your source code based on the enabled rules and generate results based on the configured finding policies. See also `--disable-code-snippet-storage`. See [SAST scan](../../../sast-scans-with-endorlabs/run-a-sast-scan/) for more information. |
| `disable-code-snippet-storage` | `ENDOR_SCAN_DISABLE_CODE_SNIPPET_STORAGE` | boolean (default:false) | Do not store or display the source code related to a finding. |
| Not applicable | `ENDOR_SCAN_SEMGREP_VERBOSE` | boolean (default:false) | Enable verbose output for SAST scans to show detailed information about rule execution, file parsing status, and scan progress. |
| Not applicable | `ENDOR_SCAN_SEMGREP_DEBUG` | boolean (default:false) | Enable debug output for SAST scans, which includes all verbose information plus additional debugging details to help troubleshoot scan issues. |

### Sandbox flags

| Flag | Environment Variable | Type | Description |
| --- | --- | --- | --- |
| `install-build-tools` | `ENDOR_SCAN_INSTALL_BUILD_TOOLS` | boolean (default:false) | Install build tools in a runtime sandbox. |
| `use-scan-profile` | `ENDOR_SCAN_USE_SCAN_PROFILE` | boolean (default:false) | Use a scan profile to run a scan in a self-contained sandbox. |

### Miscellaneous flags

| Flag | Environment Variable | Type | Description |
| --- | --- | --- | --- |
| `ai-models` | `ENDOR_SCAN_AI_MODELS` | boolean (default:false) | Scan source code repository and discover usage of OSS AI models. |
| `as-default-branch` | `ENDOR_SCAN_AS_DEFAULT_BRANCH` | boolean (default:false) | Set this as the default branch. |
| `container` | `ENDOR_SCAN_CONTAINER` | string | Set this to the container image:tag to perform a scan on containers. |
| `container-as-ref` | `ENDOR_SCAN_CONTAINER_AS_REF` | boolean (default:false) | Scan container in a persistent context and keep the version. Use the `--project-name` argument to specify the name of the project and `--path` argument to specify its path. |
| `dependencies` | `ENDOR_SCAN_DEPENDENCIES` | boolean (default:false) | Scan Git commits and generate findings for all dependencies. |
| `dry-run` | `ENDOR_SCAN_DRY_RUN` | boolean (default:false) | Run the scan in dry run mode. When enabled, scan results are not stored and only read only access is required. This flag can only be used with SCA (dependencies), SAST, or secrets scanning. It cannot be used with container scanning. |
| `detached-ref-name` | `ENDOR_SCAN_DETACHED_REF_NAME` | string | Set the name of the Git reference to a user-provided name. For example, `--detached-ref-name="$CI_DEFAULT_BRANCH"`. Use with CI environments that checkout commits, such as GitLab. |
| `droid-gpt` | `ENDOR_SCAN_DROID_GPT` | boolean (default:false) | Use DroidGPT to interpret build errors and generate remediation advice. |
| `exclude-path` | `ENDOR_SCAN_EXCLUDE_PATH` | string | Specify one or more file paths or directories to exclude from the scan using Glob style expressions. For example, `--exclude-path="src/java/**"` will exclude all files under `src/java`, including any subdirectories, while `--exclude-path="src/java/*"` will only exclude the files directly under `src/java`. Paths must be relative to the root of the repository. Use quotes to ensure that your shell does not expand wild cards. |
| `finding-tags` | `ENDOR_SCAN_FINDING_TAGS` | string | Specify a list of user-defined tags to add to findings generated for objects in this scan scope. Use in combination with options such as `--include-path` or `--exclude-path`. Finding tags can be used to search and filter findings later. |
| `ghactions` | `ENDOR_SCAN_GHACTIONS` | boolean (default:false) | Scan and discover GitHub action workflows in your CI/CD pipeline. |
| `include-path` | `ENDOR_SCAN_INCLUDE_PATH` | string | Limit the scan to the specified file paths or directories using Glob style expressions. For example, `--include-path="src/java/**"` will scan all the files under `src/java`, including any subdirectories, while `--include-path="src/java/*"` will only include the files directly under `src/java`. Paths must be relative to the root of the repository. Use quotes to ensure that your shell does not expand wild cards. |
| `l`, `languages` | `ENDOR_SCAN_LANGUAGES` | string | Set programming languages to scan. Used to limit scanning to specific languages. If your project contains multiple programming languages, you can specify them as a comma-separated list as: `c,c#,go,java,javascript,kotlin,php,python,ruby,rust,scala,swift,typescript,swifturl`. |
| `o`, `output-type` | `ENDOR_SCAN_SUMMARY_OUTPUT_TYPE` | string | Set output format to json, yaml, table, or summary. Summary only displays policy violations (default: `table`). |
| `package` | `ENDOR_SCAN_PACKAGE` | boolean (default:false) | Scan binaries and artifacts. You must provide the path of your file using `--path` and specify a name for your project using `--project-name` parameters. |
| `p`, `path` | `ENDOR_SCAN_PATH` | string | Set path to local repository to scan. For example: `--path=/Users/endorlabs/github/myrepo`. |
| `project-name` | `ENDOR_SCAN_PROJECT_NAME` | string | Give a name for the project while scanning binaries and artifacts. It is used with the `--package` parameter. |
| `project-tags` | `ENDOR_SCAN_PROJECT_TAGS` | string | Specify a list of user-defined tags to add to this project. |
| `registries` | `ENDOR_SCAN_REGISTRIES` | string | Registries that must be used in addition to public or namespace registries. Format - `\"user:password@ecosystem://registry#priority\"`. |
| `s`, `sarif-file` | `ENDOR_SCAN_SUMMARY_SARIF_FILE` | string | Set the file path for saving scan results in SARIF format. SARIF output includes vulnerability aliases, such as CVE IDs, GHSA IDs, and other OSV identifiers, for SCA findings. |
| `tags` | `ENDOR_SCAN_TAGS` | string | Specify a list of user-defined tags to add to this scan. Tags can be used to search and filter scans later. |
| `use-local-repo-cache` | `ENDOR_SCAN_USE_LOCAL_CACHE` | boolean (default:false) | Use the local cache for dependency resolution. *Make sure that `mvn install -U` is successful and include [`mvn dependency`](https://mvnrepository.com/artifact/org.apache.maven.plugins/maven-dependency-plugin) and [`mvn help`](https://mvnrepository.com/artifact/org.apache.maven.plugins/maven-help-plugin) plugins in the local m2 cache. For Gradle complete `gradle assemble --refresh-dependencies`.* |
| `uuid` | `ENDOR_SCAN_UUID` | string | Scan the specified project UUID. |
| Not applicable | `ENDOR_SCAN_EMBEDDINGS` | boolean | Control the use of code segment embeddings during a scan. Set to `false` to disable embeddings for a specific scan, or `true` to enable them. This setting overrides the system-wide configuration. See [Enable code segment embeddings](../../../scan-with-endorlabs/language-scanning/c/#enable-code-segment-embeddings) for more information. |

## Feedback

Was this page helpful?

Yes
No

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

Thanks for the feedback. Write to us at support@endor.ai to tell us more.
