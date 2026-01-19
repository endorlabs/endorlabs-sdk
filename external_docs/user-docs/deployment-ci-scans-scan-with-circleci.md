---
url: https://docs.endorlabs.com/deployment/ci-scans/scan-with-circleci/
title: Scanning with CircleCI | Endor Labs Docs
downloaded: 2026-01-16 09:50:51
---

Scanning with CircleCI | Endor Labs Docs



* Type to search...

[Print entire section](/deployment/ci-scans/scan-with-circleci/_print.html)



# Scanning with CircleCI

Learn how to implement Endor Labs in a CircleCI pipeline.

CircleCI CI/CD pipelines allow you to configure your pipeline as code. Your entire CI/CD process is orchestrated through a single file called `config.yml`. The `config.yml` file is located in a folder called `.circleci` at the root of your project which defines the entire pipeline.

To integrate Endor Labs into your CircleCI CI/CD processes:

1. [Authenticate to Endor Labs](#authenticate-to-endor-labs)
2. Install your build toolchain
3. Build your code
4. Scan with Endor Labs

## Authenticate to Endor Labs

Endor Labs recommends using keyless authentication in continuous integration environments. Keyless Authentication is more secure and reduces the cost of secret rotation but is **only available on self-hosted runners in CircleCI.**

To configure keyless authentication see [the keyless authentication documentation](../keyless-authentication/)

If you choose not to use keyless authentication you can configure an API key and secret in CircleCI for authentication using the following steps. See [managing API keys](../../../administration/api-keys/) for more information on generating an API key for Endor Labs.

1. In your CircleCI environment, navigate to **Organizational Settings**.
2. From **Contexts** and select **Create Context**.
3. Enter a context name for reference such as `endorlabs` or reuse an existing context.
4. Click into your new or existing context. Add any project restrictions and select **Add Environment Variable**.
5. In **Environment Variable Name**, enter **ENDOR\_API\_CREDENTIALS\_KEY** and in **Value**, enter the Endor Labs API Key.
6. Select **Add Environment Variable**.
7. Repeat the previous 3 steps to add your **API key secret** as the environment variable **ENDOR\_API\_CREDENTIALS\_SECRET**. Have the name of the context handy to reference in the workflows later.

## Configure your CircleCI pipeline

**Important**

CircleCI may check out commits in a detached HEAD state, which can lead to fragmented branch tracking in Endor Labs. See [Set up branch tracking in CircleCI](#set-up-branch-tracking-in-circleci) to configure proper branch context.

To create a CircleCI pipeline reference the following steps:

1. Create a `.cirlceci/config.yml` file in your repository if you do not already have one.
2. In your `config.yml` file customize the job configuration based on your project’s requirements using one of the examples, [simple CircleCI configuration](#simple-circleci-configuration) or [advanced CircleCI configuration](#advanced-circleci-configuration).
3. Create two workflows called `build_and_watch_endorlabs` and `build_and_test_endorlabs`.
4. Ensure that the context you created is part of the workflow if you are not using keyless authentication.
5. Adjust the image field to conform to the required build tools for constructing your software packages, and synchronize your build steps with those of your project.
6. Update your Endor Labs tenant namespace to the appropriate namespace for your project.
7. Update your default branch from main if you do not use main as the default branch name.
8. Modify any dependency or artifact caches to align with the languages and caches used by your project.

## Examples

Use the following examples to get started. Make sure to customize this job with your specific build environment and build steps.

### Simple CircleCI configuration

```
version: 2.1

jobs:
  test-endorlabs-scan:
    docker:
      - image: maven:3.6.3-jdk-11 # Modify this image as needed for your build tools
    environment:
      ENDORCTL_VERSION: "latest"
      ENDOR_NAMESPACE: "example"
    steps:
      - checkout
      - run:
          name: "Build"
          command: |
            mvn clean install -Dskiptests
      - run:
          name: "Install endorctl"
          command: |
            curl https://api.endorlabs.com/download/latest/endorctl_linux_amd64 -o endorctl
            echo "$(curl -s https://api.endorlabs.com/sha/latest/endorctl_linux_amd64)  endorctl" | sha256sum -c;
            if [ $? -ne 0 ]; then
              echo "Integrity check failed";
              exit 1;
            fi
            chmod +x ./endorctl
            ./endorctl --version
      - run:
          name: "Endor Labs Test"
          command: |
            ./endorctl scan --pr --pr-baseline=main --dependencies --secrets
  watch-endorlabs-scan:
    docker:
      - image: maven:3.6.3-jdk-11 # Modify this image as needed for your build tools
    environment:
      ENDOR_NAMESPACE: "example" # Replace with your Endor Labs namespace
    steps:
      - checkout
      - run:
          name: "Build"
          command: |
            mvn clean install -Dskiptests
      - run:
          name: "Install endorctl"
          command: |
            curl https://api.endorlabs.com/download/latest/endorctl_linux_amd64 -o endorctl
            echo "$(curl -s https://api.endorlabs.com/sha/latest/endorctl_linux_amd64)  endorctl" | sha256sum -c;
            if [ $? -ne 0 ]; then
              echo "Integrity check failed";
              exit 1;
            fi
            chmod +x ./endorctl
            ./endorctl --version
      - run:
          name: "Endor Labs Watch"
          command: |
            ./endorctl scan --dependencies --secrets
workflows:
  build_and_endorlabs_watch:
    when:
      equal: [ main, << pipeline.git.branch >> ]
    jobs:
      - watch-endorlabs-scan:
          context:
            - endorlabs
  build_and_endorlabs_test:
    jobs:
      - test-endorlabs-scan:
          context:
            - endorlabs
```

### Advanced CircleCI configuration

The following example is an advanced implementation of Endor Labs in circleCI which includes several optional performance optimizations and job maintainability updates.

This includes:

1. Caching and restoring caches of jobs and artifacts to improve performance. Caches should be modified to reflect the build artifacts and dependencies of your project.
2. Segmenting jobs and scans.

```
# You can copy and paste portions of this `config.yml` file as an easy reference.
#
version: 2.1

jobs:
  build:
    docker:
      - image: maven:3.6.3-jdk-11 # Modify this image as needed for your build steps
    steps:
      - checkout
      - restore_cache:
          keys:
            # when lock file changes, use increasingly general patterns to restore cache
            - maven-repo-v1-{{ .Branch }}-{{ checksum "pom.xml" }}
            - maven-repo-v1-{{ .Branch }}-
            - maven-repo-v1-
      - run:
          name: "Build Your Project"
          command: |
            mvn clean install
      - persist_to_workspace:
          root: .
          paths:
            - target/ # Persist artifact across job. Change this if you are creating your artifact in a location outside of the target directory.
      - save_cache:
          paths:
            - ~/.m2/repository
          key: maven-repo-v1-{{ .Branch }}-{{ checksum "pom.xml" }}

  test-endorlabs-scan:
    docker:
      - image: maven:3.6.3-jdk-11 # Modify this image as needed for your build tools
    environment:
      ENDORCTL_VERSION: "latest"
      ENDOR_NAMESPACE: "example"
    steps:
      - checkout
      - attach_workspace:
          at: .
      - restore_cache:
          keys:
            # when lock file changes, use increasingly general patterns to restore cache
            - maven-repo-v1-{{ .Branch }}-{{ checksum "pom.xml" }}
            - maven-repo-v1-{{ .Branch }}-
            - maven-repo-v1-
      - run:
          name: "Install endorctl"
          command: |
            curl https://api.endorlabs.com/download/latest/endorctl_linux_amd64 -o endorctl
            echo "$(curl -s https://api.endorlabs.com/sha/latest/endorctl_linux_amd64)  endorctl" | sha256sum -c;
            if [ $? -ne 0 ]; then
              echo "Integrity check failed";
              exit 1;
            fi
            chmod +x ./endorctl
            ./endorctl --version
      - run:
          name: "Endor Labs Test"
          command: |
            ./endorctl scan --pr --pr-baseline=main --dependencies --secrets

  watch-endorlabs-scan:
    docker:
      - image: maven:3.6.3-jdk-11 # Modify this image as needed for your build tools
    environment:
      ENDORCTL_VERSION: "latest"
      ENDOR_NAMESPACE: "example" #Replace with your namespace in Endor Labs
    steps:
      - checkout
      - attach_workspace:
          at: .
      - restore_cache:
          keys:
            # when lock file changes, use increasingly general patterns to restore cache
            - maven-repo-v1-{{ .Branch }}-{{ checksum "pom.xml" }}
            - maven-repo-v1-{{ .Branch }}-
            - maven-repo-v1-
      - run:
          name: "Install endorctl"
          command: |
            curl https://api.endorlabs.com/download/latest/endorctl_linux_amd64 -o endorctl
            echo "$(curl -s https://api.endorlabs.com/sha/latest/endorctl_linux_amd64)  endorctl" | sha256sum -c;
            if [ $? -ne 0 ]; then
              echo "Integrity check failed";
              exit 1;
            fi
            chmod +x ./endorctl
            ./endorctl --version
      - run:
          name: "Endor Labs Watch"
          command: |
            ./endorctl scan --dependencies --secrets
workflows:
  build_and_endorlabs_watch:
    when:
      equal: [ main, << pipeline.git.branch >> ]
    jobs:
      - build
      - watch-endorlabs-scan:
          requires:
            - build
          context:
            - endorlabs
  build_and_endorlabs_test:
    jobs:
      - build
      - test-endorlabs-scan:
          requires:
            - build
          context:
            - endorlabs
```

Once you’ve set up Endor Labs you can test your CI implementation is successful and begin scanning.

## Set up branch tracking in CircleCI

In Git, a detached HEAD state occurs when the repository checks out a specific commit instead of a branch reference. In this state, Git points the HEAD directly to a commit hash, without associating it with a named branch. As a result, actions performed, such as creating new commits or running automated scans, do not carry branch identity unless explicitly specified.

Proper branch context enables Endor Labs to:

* Associate scans with the correct branch
* Identify scans on the monitored default branch
* Track findings and display metrics accurately across branches

Without proper branch configuration, Endor Labs may create multiple branch entries for the same logical branch, leading to fragmented reporting and inaccurate metrics.

![Project with multiple branch entries](../../../images/branch-fragmentation.png)

CircleCI often checks out commits by their SHA instead of the branch name, which creates a detached HEAD state.

Use `--detached-ref-name` only to specify the branch name for a commit in detached HEAD state. This associates the commit with the correct branch without setting it as the default branch.

```
- run:
    name: "Endor Labs Scan"
    command: |
      ./endorctl scan --dependencies --secrets \
      --detached-ref-name="<< pipeline.git.branch >>"
```

Use both `--detached-ref-name` and `--as-default-branch` together when you want to associate the commit with a branch and set it as the default branch scan.

```
- run:
    name: "Endor Labs Scan"
    command: |
      ./endorctl scan --dependencies --secrets \
      --as-default-branch \
      --detached-ref-name="<< pipeline.git.branch >>"
```

## Feedback

Was this page helpful?

Yes
No

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

Thanks for the feedback. Write to us at support@endor.ai to tell us more.
