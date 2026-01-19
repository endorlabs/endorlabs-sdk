---
url: https://docs.endorlabs.com/deployment/ci-scans/scan-with-gitlab/
title: Scanning in GitLab Pipelines | Endor Labs Docs
downloaded: 2026-01-16 09:49:58
---

Scanning in GitLab Pipelines | Endor Labs Docs



* Type to search...

[Print entire section](/deployment/ci-scans/scan-with-gitlab/_print.html)



# Scanning in GitLab Pipelines

Learn how to implement Endor Labs across a GitLab CI pipeline.

GitLab CI/CD pipelines are a part of GitLab’s integrated continuous integration and deployment features. They allow you to define and automate the different stages and tasks in your software development workflow.

This documentation page provides an overview and example job to integrate Endor Labs into your GitLab CI pipeline.

## High Level Usage Steps

1. Setup authentication to Endor Labs
2. Install your build toolchain
3. Build your code
4. Scan with Endor Labs

### Authentication to Endor Labs

Endor Labs recommends using keyless authentication in continuous integration environments.

Keyless Authentication is more secure and reduces the cost of secret rotation.

To set up keyless authentication see [the keyless authentication documentation](../keyless-authentication/)

If you choose not to use keyless authentication you can configure an API key and secret in GitLab for authentication using the following steps. See [managing API keys for more information on getting an API key for Endor Labs authentication](../../../administration/api-keys/)

### Configure API key and secret in GitLab

1. In your GitLab environment, select the project you want to scan.
2. Go to Settings > CI/CD.
3. Click Expand in the Variables section.
4. Click the Add variable button at the bottom of the section.
5. In the Key field, enter ENDOR\_API\_CREDENTIALS\_SECRET.
6. In the Value field, enter your Endor Labs API secret.
7. Under Flags, make sure you select Mask variable.
8. Repeat the previous steps to add your API key as the variable ENDOR\_API\_CREDENTIALS\_KEY.

### Configure your GitLab CI pipeline

**Important**

GitLab CI/CD pipelines check out commits in a detached HEAD state, which can lead to fragmented branch tracking in Endor Labs. See [Set up branch tracking in GitLab](#set-up-branch-tracking-in-gitlab) to configure proper branch context.

1. Create a `.gitlab-ci.yml` file in the root directory of your project if you do not already have one.
2. In your `.gitlab-ci.yml` file customize the job configuration based on your project’s requirements using the example below.
3. Modify the image field to align with the build tools necessary for building your software packages.
4. Update the before\_script section to include any additional steps required before executing the scan, such as installing dependencies or building your project.
5. Save and commit the `.gitlab-ci.yml` file to your GitLab repository.
6. GitLab will automatically detect the `.gitlab-ci.yml` file and trigger the defined job whenever there are changes pushed to the repository.
7. Monitor the progress and results of the CI pipeline in the GitLab CI/CD interface.

You can use the following example job to get started. Make sure to customize this job with your specific build environment and build steps.

```
# You can copy and paste this template into a new `.gitlab-ci.yml` file.
# You should not add this template to an existing `.gitlab-ci.yml` file by using the `include:` keyword.
#
stages:
  - Scan
Endor Labs Dependency Scan:
  stage: test
  image: node # Modify this image to align with the build tools nessesary to build your software packages
  dependencies: []
  variables:
   ## Scan scoping section
   #
   ## Use the following environment variables for custom paths, inclusions and exclusions.
   # ENDOR_SCAN_PATH: "Insert a custom path to your git repository. Defaults to your pwd"
   # ENDOR_SCAN_EXCLUDE_PATH: "Insert a Glob style pattern of paths to exclude in the scan. Generally used for monorepos."
   # ENDORCTL_SCAN_INCLUDE_PATH: "Insert a Glob style pattern of paths to include in the scan. Generally used for monorepos."
   #
   ## Authentication to Endor Labs
   #
   ## Use the following environment variables for keyless authentication with your cloud provider. For more information visit: https://docs.endorlabs.com/continuous-integration/keyless-authentication/
   #
   # ENDOR_GCP_CREDENTIALS_SERVICE_ACCOUNT: "endorlabs@<yourproject.iam.gserviceaccount.com"
   # ENDOR_AWS_CREDENTIALS_ROLE_ARN: "arn:aws:iam::123456789012:role/my-role"
   #
   ## Follow the below instructions to use an API key and secret instead of keyless authentication.
   ## In your GitLab environment, select the project you want to scan.
   ## Go to `Settings` > `CI/CD`.
   ## Click `Expand` in the `Variables` section.
   ## Click the `Add variable` button at the bottom of the section.
   ## In the `Key` field, enter ENDOR_API_CREDENTIALS_SECRET.
   ## In the `Value` field, enter your Endor Labs API secret.
   ## Under `Flags` make sure you select `Mask variable`.
   ## Repeat to add your API key as the variable ENDOR_API_CREDENTIALS_KEY
   #
    ENDOR_ENABLED: "true"
    ENDOR_ALLOW_FAILURE: "false"
    ENDOR_NAMESPACE: "example" # Replace with your Endor Labs namespace
    ENDOR_PROJECT_DIR: "."
    ENDOR_ARGS: |
      --path=${ENDOR_PROJECT_DIR}
      --detached-ref-name=$CI_COMMIT_REF_NAME
      --output-type=summary
      --exit-on-policy-warning
      --dependencies --secrets --git-logs
  before_script:
    - npm install yarn # Replace with the build steps for your Endor Labs job.
  script:
    - curl https://api.endorlabs.com/download/latest/endorctl_linux_amd64 -o ./endorctl;
    - echo "$(curl -s https://api.endorlabs.com/sha/latest/endorctl_linux_amd64)  ./endorctl" | sha256sum -c;
      if [ $? -ne 0 ]; then
       echo "Integrity check failed";
       exit 1;
      fi
    - chmod +x ./endorctl
    - if [ "$DEBUG" == "true" ]; then
        export ENDOR_LOG_VERBOSE=true;
        export ENDOR_LOG_LEVEL=debug;
      fi
    - if [ "$CI_COMMIT_REF_NAME" == "$CI_DEFAULT_BRANCH" ]; then
        export ENDOR_SCAN_AS_DEFAULT_BRANCH=true;
        export ENDOR_SCAN_DETACHED_REF_NAME="$CI_COMMIT_REF_NAME";
      else
        export ENDOR_SCAN_PR=true;
      fi
    - ./endorctl scan ${ENDOR_ARGS}
  rules:
  - if: $ENDOR_ENABLED != "true"
    when: never
  - if: $ENDOR_ALLOW_FAILURE == "true"
    allow_failure: true
  - if: $ENDOR_ALLOW_FAILURE != "true"
    allow_failure: false
```

## Set up branch tracking in GitLab

In Git, a detached HEAD state occurs when the repository checks out a specific commit instead of a branch reference. In this state, Git points the HEAD directly to a commit hash, without associating it with a named branch. As a result, actions performed, such as creating new commits or running automated scans, do not carry branch identity unless explicitly specified.

Proper branch context enables Endor Labs to:

* Associate scans with the correct branch
* Identify scans on the monitored default branch
* Track findings and display metrics accurately across branches

Without proper branch configuration, Endor Labs may create multiple branch entries for the same logical branch, leading to fragmented reporting and inaccurate metrics.

![Project with multiple branch entries](../../../images/branch-fragmentation.png)

GitLab CI/CD checks out commits by their SHA instead of the branch name, which creates a detached HEAD state.

Use `--detached-ref-name` only to specify the branch name for a commit in detached HEAD state. This associates the commit with the correct branch without setting it as the default branch.

```
variables:
  ENDOR_ARGS: |
    --path=${ENDOR_PROJECT_DIR}
    --detached-ref-name=$CI_COMMIT_REF_NAME
    --dependencies --secrets

script:
  - ./endorctl scan ${ENDOR_ARGS}
```

Use both `--detached-ref-name` and `--as-default-branch` together when you want to associate the commit with a branch and set it as the default branch scan.

```
variables:
  ENDOR_ARGS: |
    --path=${ENDOR_PROJECT_DIR}
    --detached-ref-name=$CI_COMMIT_REF_NAME
    --dependencies --secrets

script:
  - if [ "$CI_COMMIT_REF_NAME" == "$CI_DEFAULT_BRANCH" ]; then
      export ENDOR_SCAN_AS_DEFAULT_BRANCH=true;
    else
      export ENDOR_SCAN_PR=true;
    fi
  - ./endorctl scan ${ENDOR_ARGS}
```

## Run MR scans

MR scans are point-in-time scans that run on merge requests to detect new policy violations and security issues introduced by the changes. Unlike default branch scans which create monitored versions, MR scans compare findings against the baseline to surface only new issues.

To run scans on merge requests, use the `--pr` flag. This flag tells endorctl to treat the scan as a merge request scan and compare findings against the target branch baseline.

The following example configuration runs an MR scan only when triggered by a merge request pipeline:

```
Endor Labs MR Scan:
  stage: test
  image: node
  variables:
    ENDOR_NAMESPACE: "example" # Replace with your Endor Labs namespace
    ENDOR_PROJECT_DIR: "."
    ENDOR_ARGS: |
      --path=${ENDOR_PROJECT_DIR}
      --detached-ref-name=$CI_COMMIT_REF_NAME
      --pr
      --dependencies --secrets
  before_script:
    - npm install # Replace with your build steps
  script:
    - curl https://api.endorlabs.com/download/latest/endorctl_linux_amd64 -o ./endorctl
    - echo "$(curl -s https://api.endorlabs.com/sha/latest/endorctl_linux_amd64)  ./endorctl" | sha256sum -c
    - chmod +x ./endorctl
    - ./endorctl scan ${ENDOR_ARGS}
  rules:
    - if: $CI_MERGE_REQUEST_IID
```

**Note**

The `--detached-ref-name` flag is recommended for MR scans in GitLab because merge request pipelines check out commits in a detached HEAD state. This flag provides the branch name context needed for proper baseline comparison.

## Enable MR comments

You can enable MR comments in your GitLab CI pipeline to automatically post comments on merge requests when policy violations are detected. MR comments build on top of [MR scans](#run-mr-scans) by posting the scan results directly on the merge request.

**Configure a GitLab token**

Configure a GitLab CI/CD variable following the same steps as described in [Configure API key and secret in GitLab](#configure-api-key-and-secret-in-gitlab). Add a variable with the key `ENDOR_SCAN_SCM_TOKEN` and set its value to your GitLab personal access token with the `api` scope. Make sure to select **Mask variable** under Flags.

### Configure the pipeline for MR comments

The following example configuration enables MR comments in your GitLab CI pipeline:

```
Endor Labs MR Scan:
  stage: test
  image: node
  variables:
    ENDOR_NAMESPACE: "example" # Replace with your Endor Labs namespace
    ENDOR_PROJECT_DIR: "."
    ENDOR_ARGS: |
      --path=${ENDOR_PROJECT_DIR}
      --detached-ref-name=$CI_COMMIT_REF_NAME
      --pr
      --enable-pr-comments
      --scm-pr-id=$CI_MERGE_REQUEST_IID
      --scm-token=$ENDOR_SCAN_SCM_TOKEN
      --dependencies --secrets
  before_script:
    - npm install # Replace with your build steps
  script:
    - curl https://api.endorlabs.com/download/latest/endorctl_linux_amd64 -o ./endorctl
    - echo "$(curl -s https://api.endorlabs.com/sha/latest/endorctl_linux_amd64)  ./endorctl" | sha256sum -c
    - chmod +x ./endorctl
    - ./endorctl scan ${ENDOR_ARGS}
  rules:
    - if: $CI_MERGE_REQUEST_IID
```

The key flags for MR comments are:

* `--pr`: Enables MR scan mode
* `--enable-pr-comments`: Enables posting comments on the merge request
* `--scm-pr-id=$CI_MERGE_REQUEST_IID`: Provides the merge request ID
* `--scm-token=$ENDOR_SCAN_SCM_TOKEN`: Provides the GitLab token for posting comments

### Configure an action policy

After you enable MR comments, you need to set up an action policy to allow comments to be posted on merge requests. See [Configure Action policy for PR comments](../../../scan-with-endorlabs/pr-scans/pr-comments/#configure-action-policy-for-pr-comments) for more information.

## Feedback

Was this page helpful?

Yes
No

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

Thanks for the feedback. Write to us at support@endor.ai to tell us more.
