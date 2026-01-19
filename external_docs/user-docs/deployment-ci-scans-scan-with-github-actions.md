---
url: https://docs.endorlabs.com/deployment/ci-scans/scan-with-github-actions/
title: Scanning with GitHub Actions | Endor Labs Docs
downloaded: 2026-01-16 09:48:49
---

Scanning with GitHub Actions | Endor Labs Docs



* Type to search...

[Print entire section](/deployment/ci-scans/scan-with-github-actions/_print.html)



# Scanning with GitHub Actions

Learn how to implement Endor Labs in GitHub action workflows.

GitHub Actions is a continuous integration and continuous delivery (CI/CD) platform that allows you to automate your build, test, and deployment pipeline.
You can use GitHub Actions to include Endor Labs into your CI pipeline seamlessly.

Using this pipeline, developers can view and detect:

* Policy violations in the source code
* Secrets inadvertently included in the source code

The Endor Labs verifications are conducted as automated checks and help you discover violations before pushing code to the repository. Information about the violations can be included as comments on the corresponding pull request (PR). This enables developers to easily identify issues and take remedial measures early in the development life cycle.

* For policy violations, the workflow is designed to either emit a warning or return an error based on your action policy configurations.
* For secrets discovered in the commits, developers can view the PR comments and take necessary remedial measures.

## Install Software Prerequisites

To ensure the successful execution of the Endor Labs GitHub action, the following prerequisites must be met:

* The GitHub action must be able to authenticate with the Endor Labs API.
* You must have the value of the Endor Labs namespace handy for authentication.
* You must have access to the Endor Labs API.
* If you use keyless authentication, you must set an authorization policy in Endor Labs. See [Authorization policies](../../../administration/access-endorlabs/authorization-policies/) for details.

## Example GitHub Action Workflow

Endor Labs scanning workflow using GitHub Actions that accomplishes the following tasks in your CI environment:

* Tests PRs to the default branch and monitors the most recent push to the default branch.
* Builds a Java project and sets up the Java build tools. If your project is not on Java, then configure this workflow with your project-specific steps and build tools.
* Authenticates to Endor Labs with GitHub Actions keyless authentication.
* Scan with Endor Labs.
* Comments on PRs if any policy violations occur.
* Generates findings and uploads results to GitHub in SARIF format.

The following example workflow shows how to scan with Endor Labs for a Java application using the recommended keyless authentication for GitHub Actions.

```
name: Endor Labs Dependency and Secrets Scan
on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]
jobs:
  scan:
    permissions:
      security-events: write # Used to upload Sarif artifact to GitHub
      contents: read # Used to check out a private repository
      actions: read # Required for private repositories to upload Sarif files. GitHub Advanced Security licenses are required.
      id-token: write # Used for keyless authentication with Endor Labs
      pull-requests: write # Required to automatically comment on PRs for new policy violations
    runs-on: ubuntu-latest
    steps:
    - name: Checkout Repository
      uses: actions/checkout@v3
    - name: Setup Java
      uses: actions/setup-java@v3
      with:
        distribution: 'microsoft'
        java-version: '17'
    - name: Build Package
      run: mvn clean install
    - name: Endor Labs Scan Pull Request
      if: github.event_name == 'pull_request'
      uses: endorlabs/github-action@v1 # Replace v1 with the commit SHA of the latest version of the GitHub Action for enhanced security
      with:
        namespace: 'example' # Replace with your Endor Labs tenant namespace
        scan_dependencies: true
        scan_secrets: true
        pr: true
        enable_pr_comments: true # Required to automatically comment on PRs for new policy violations
        github_token: ${{ secrets.GITHUB_TOKEN }} # Required for PR comments on new policy violations

  scan-main:
    permissions:
      id-token: write
      repository-projects: read
      pull-requests: read
      contents: read
    name: endorctl-scan
    runs-on: ubuntu-latest
    steps:
    - name: Checkout Repository
      uses: actions/checkout@v3
    - name: Setup Java
      uses: actions/setup-java@v3
      with:
        distribution: 'microsoft'
        java-version: '17'
    - name: Build Package
      run: mvn clean install
    - name: 'Endor Labs Scan Push to main'
      if: ${{ github.event_name == 'push' }}
      uses: endorlabs/github-action@v1 # Replace v1 with the commit SHA of the latest version of the GitHub Action for enhanced security
      with:
        namespace: 'example' # Replace with your Endor Labs tenant namespace
        scan_dependencies: true
        scan_secrets: true
        pr: false
        scan_summary_output_type: 'table'
        sarif_file: 'findings.sarif'
    - name: Upload findings to github
      uses: github/codeql-action/upload-sarif@v3
      with:
        sarif_file: 'findings.sarif'
```

## Set up branch tracking in GitHub Actions

In Git, a detached HEAD state occurs when the repository checks out a specific commit instead of a branch reference. In this state, Git points the HEAD directly to a commit hash, without associating it with a named branch. As a result, actions performed, such as creating new commits or running automated scans, do not carry branch identity unless explicitly specified.

Proper branch context enables Endor Labs to:

* Associate scans with the correct branch
* Identify scans on the monitored default branch
* Track findings and display metrics accurately across branches

Without proper branch configuration, Endor Labs may create multiple branch entries for the same logical branch, leading to fragmented reporting and inaccurate metrics.

![Project with multiple branch entries](../../../images/branch-fragmentation.png)

GitHub Actions typically maintains proper branch context automatically. However, to ensure scans are properly tracked, when using the Endor Labs GitHub Action, set `pr: false` to create monitored versions that appear on dashboards. Use `if: github.event_name == 'push'` to trigger only on pushes to the default branch:

```
- name: Endor Labs Scan Push to main
  if: github.event_name == 'push'
  uses: endorlabs/github-action@v1
  with:
    namespace: 'example'
    scan_dependencies: true
    pr: false
```

## Secure GitHub Actions with immutable commit SHA

Endor Labs recommends pinning the commit SHA of the GitHub Actions to enhance security. By pinning GitHub Actions to a commit SHA, you make the code immutable even if the tag version is changed or the code is updated.

To find the Endor Labs GitHub action’s latest commit SHA:

1. Go to [Endor Labs GitHub Actions](https://github.com/endorlabs/github-action) page and select the latest release version in **Releases**.
2. Click the commit of the release.
   ![Select commit SHA of latest release](../../../images/github-action-pin-commit-sha.png)
3. Copy the commit SHA from the URL.

   The commit SHA is the 40-character alphanumeric string in the URL after `/commit/`.
   ![Copy commit SHA](../../../images/github-action-copy-commit-sha.png)

## Authenticate with Endor Labs

Endor Labs recommends using keyless authentication in CI environments. Keyless authentication is more secure and reduces the cost of secret rotation. To set up keyless authentication see [Keyless Authentication](../keyless-authentication/).

If you choose not to use keyless authentication, you can configure an API key and secret in GitHub for authentication as outlined in [Managing API keys](../../../administration/api-keys/).

### Authentication Without Keyless Authentication for GitHub

If you are not using keyless authentication for GitHub Actions, you must not provide `id-token: write` permissions to your GitHub token unless specifically required by a step in this job. You must also set `enable_github_action_token: false` in your Endor Labs GitHub Action configuration.

The following example configuration uses the Endor Labs API key for authentication:

```
      - name: Scan with Endor Labs
        uses: endorlabs/github-action@v1 # Replace v1 with the commit SHA of the latest version of the GitHub Action for enhanced security
        with:
          namespace: 'example'
          api_key: ${{ secrets.ENDOR_API_CREDENTIALS_KEY }}
          api_secret: ${{ secrets.ENDOR_API_CREDENTIALS_SECRET }}
          enable_github_action_token: false
```

The following example configuration uses a GCP service account for keyless authentication to Endor Labs:

```
      - name: Scan with Endor Labs
        uses: endorlabs/github-action@v1 # Replace v1 with the commit SHA of the latest version of the GitHub Action for enhanced security
        with:
          namespace: 'example'
          gcp_service_account: '<Insert_Your_Service_Account>@<Insert_Your_Project>.iam.gserviceaccount.com'
          enable_github_action_token: false
```

## Endor Labs GitHub Action Configuration Parameters

The following input configuration parameters are supported for the Endor Labs GitHub Action:

### Common parameters

Endor Labs GitHub Actions supports the following input global parameters:

| Flags | Description |
| --- | --- |
| `api_key` | Set the API key used to authenticate with Endor Labs. |
| `api_secret` | Set the secret corresponding to the API key used to authenticate with Endor Labs. |
| `enable_github_action_token` | Set to `false` if you prefer to use another form of authentication over GitHub action OIDC tokens. (Default: `true`) |
| `endorctl_checksum` | Set to the checksum associated with a pinned version of endorctl. |
| `endorctl_version` | Set to a version of endorctl to pin this specific version for use. Defaults to the latest version. |
| `gcp_service_account` | Set the target service account for GCP based authentication. GCP authentication is only enabled if this flag is set. Cannot be used with `api_key`. |
| `log_level` | Set the log level. (Default: `info`) |
| `log_verbose` | Set to `true` to enable verbose logging. (Default: `false`) |
| `namespace` | Set to the namespace of the project that you are working with. (Required) |

### Scanning parameters

The following input parameters are also supported for the Endor Labs GitHub Action when used for scanning:

| Flags | Description |
| --- | --- |
| `additional_args` | Use `additional_args` with `endorctl scan` for advanced scenarios. However, no example use case currently exists as standard options suffice for typical needs. |
| `use-bazel` | Enable the usage of Bazel for the scan. (Default: `false`) |
| `bazel_exclude_targets` | Specify a list of Bazel targets to exclude from the scan. |
| `bazel_include_targets` | Specify a list of Bazel targets to scan. If `bazel_targets_include` is not set, the `bazel_targets_query` value is used to determine which Bazel targets to scan. |
| `bazel_targets_query` | Specify a Bazel query to determine which Bazel targets to scan. Ignored if `bazel_targets_include` is set. |
| `pr` | Set to `false` to track this scan as a monitored version within Endor Labs, as opposed to a point-in-time policy and finding test for a PR. (Default: `true`) |
| `enable_pr_comments` | Set to `true` to publish new findings as review comments. Requires `pr` and `github_token`. Additionally, the `pull-requests: write` permissions must be set in the workflow. (Default: `false`) |
| `pr_baseline` | Set to the Git reference that you are merging to, such as the default branch. Enables endorctl to compare findings, so developers are only alerted to issues in the current changeset. Example: `pr_baseline: "main"`. Note: Not needed if `enable_pr_comments` is set to `true`. |
| `github_token` | Set the token used to authenticate with GitHub. Mandatory if `enable_pr_comments` is set to `true` |
| `run_stats` | Set to `false` to disable reporting of CPU/RAM/time scan statistics via `time -v` (sometimes required on Windows runners). (Default: `true`) |
| `phantom_dependencies` | Set to `true` to enable phantom dependency analysis. (Default: `false`) |
| `project_name` | Specify a project name for a container image scan or a package scan. |
| `image` | Specify a container image to scan. |
| `tags` | Specify a list of user-defined tags to add to this scan. You can use tags to search and filter scans later. |
| `scan_dependencies` | Scan Git commits and generate findings for all dependencies. (Default: `true`) |
| `scan_git_logs` | Perform a more complete and detailed scan of secrets in the repository history. Must be used together with `scan_secrets`. (Default: `false`) |
| `scan_github_actions` | Scan source code repository for GitHub Actions used in workflow files to analyze vulnerabilities and malware. (Default: `false`) |
| `scan_path` | Set the path of the directory to scan. (Default: `.`) |
| `scan_secrets` | Scan the source code repository and generate findings for secrets. See also `scan_git_logs`. (Default: `false`) |
| `scan_tools` | Scan source code repository for CI/CD tools. (Default: `false`) |
| `scan_package` | Scan a specified artifact or a package. Set the path to an artifact with `scan_path`. (Default: `false`) |
| `scan_container` | Scan a specified container image. The image must be set with `image` and a project can be defined with `project_name`. (Default: `false`) |
| `scan_sast` | Scan the source code repository and generate findings for SAST. (Default: `false`) |
| `disable_code_snippet_storage` | Disable code snippet storage for SAST scans. (Default: `false`) |
| `scan_summary_output_type` | Set the desired output format to `table`, `json`, `yaml`, or `summary`. (Default: `json`) |
| `sarif_file` | Set to a path on your GitHub runner to store the analysis results in SARIF format. |
| `export_scan_result_artifact` | Set to `false` to disable the json scan result artifact export. (Default: `true`) |
| `output_file` | Set a file to save the scan results. Use this instead of `export_scan_result_artifact` to save any scan results data to a file in the workspace for processing by others steps in the same job, instead of the workflow run log. |

### Environmental variables

You can use the following environmental variable for the Endor Labs GitHub Action:

| Flags | Description |
| --- | --- |
| `ENDOR_JS_ENABLE_TSSERVER` | Set to `false` to skip installing `tsserver` when function reachability analysis is not required for JavaScript/TypeScript projects. |

### Artifact scanning parameters

Use the following parameters and the latest sign action `endorlabs/github-action/sign@version` to build artifact signing through Endor Labs GitHub Actions.

The optional parameters are required only if `enable_github_action_token` in [common parameters](#common-parameters) is `false`. If `true` (default value), GitHub automatically populates the optional and other parameters as token claims and sends them to Endor Labs.

| Flags | Required | Description |
| --- | --- | --- |
| `artifact_name` | Mandatory | Set to the name of the artifact to be signed. |
| `source_repository_ref` | Optional | Set to the repository reference on which the build run was based. For example, `ref/tags/v1.0.1`. |
| `certificate_oidc_issuer` | Optional | Set to the OIDC issuer of the token expected in the certificate. For example, `https://token.actions.githubusercontent.com`. |

### Artifact verifying parameters

Use the following verification parameters and the latest verify action `endorlabs/github-action/verify@version` to build artifact verification through Endor Labs GitHub Actions.

| Flags | Required | Description |
| --- | --- | --- |
| `artifact_name` | Mandatory | Set to the name of the artifact to be verified. |
| `certificate_oidc_issuer` | Mandatory | Set to the OIDC issuer of the token expected in the certificate. For example, `https://token.actions.githubusercontent.com`. |

## Feedback

Was this page helpful?

Yes
No

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

Thanks for the feedback. Write to us at support@endor.ai to tell us more.
