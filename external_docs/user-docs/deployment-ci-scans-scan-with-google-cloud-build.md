---
url: https://docs.endorlabs.com/deployment/ci-scans/scan-with-google-cloud-build/
title: Scanning with Google Cloud Build | Endor Labs Docs
downloaded: 2025-11-20 11:51:31
---

Scanning with Google Cloud Build | Endor Labs Docs



* Type to search...
* ---

[Print entire section](/deployment/ci-scans/scan-with-google-cloud-build/_print.html)



# Scanning with Google Cloud Build

Learn how to implement Endor Labs with Google Cloud Build.

Google Cloud Build is a fully managed continuous integration and continuous delivery (CI/CD) service offered by Google Cloud Platform.

To integrate Endor Labs with Google Cloud Build:

* [Authenticate to Endor Labs](#authenticate-to-endor-labs)
* [Set up Google Cloud prerequisites](#set-up-google-cloud-prerequisites)
* [Set up repositories on Google Cloud Build](#set-up-repositories-on-google-cloud-build)
* [Create Cloud Build triggers](#create-cloud-build-triggers)
  + [Baseline scan](#baseline-scan)
  + [PR scan](#pr-scan)
  + [Release scan](#release-scan)
  + [Example configuration file](#example-configuration-file)

## Authenticate to Endor Labs

Generate API credentials to authenticate to Endor Labs. Configure the API key and secret in the `cloudbuild.yaml` file for authentication. See [managing API keys](../../../administration/api-keys/) for more information on generating an API key for Endor Labs.

You can enable keyless authentication to Google Cloud. See [Enabling Keyless Authentication in Google Cloud](../keyless-authentication/#Enabling-Keyless-Authentication-in-Google-Cloud) for more information.

## Set up Google Cloud prerequisites

Ensure the following prerequisites are in place in Google Cloud Build before integrating with Endor Labs.

* **GCP Service Account**: Create a service account to operate Google Cloud Build.
* **APIs**:
  + Enable the Google Cloud Build API.
  + Enable the Secrets Manager API.
* **Secrets**:
  + Create secrets in Secret Manager to store the Endor Labs API credentials: `endor-api-key` and `endor-api-secret`.
* **Permissions**:
  Grant the service account the following roles:
  + **Secret Manager Secret Accessor**: Allows the service account to access API credentials from Secret Manager.
  + **Logging Admin**: Allows the service account to write build logs to Cloud Logging.

## Set up repositories on Google Cloud Build

1. Sign in to the Google Cloud Build console.
2. Navigate to Repositories.
3. Follow the instructions in [Connecting GitHub Repositories to Cloud Build](https://cloud.google.com/build/docs/automating-builds/github/connect-repo-github?generation=2nd-gen) to add the repositories you want to scan with Cloud Build.

## Create Cloud Build triggers

Triggers initiate Cloud Build for different types of scans. You can set up triggers for the following scan types:

* [Baseline scan](#baseline-scan)
* [PR scan](#pr-scan)
* [Release scan](#release-scan)

### Baseline scan

* **Purpose**: Scans the baseline or the default branch to identify existing security vulnerabilities. Future code and dependencies will be evaluated against this baseline.
* **Trigger Type**: Push to branch.
* **Setup**: Create a trigger for the required repository and branch, for example, main, or develop.
* **Cloud Build Configuration**: Create a `cloudbuild.yaml` file using the [configuration file examples](#example-configuration-file) as a reference. Include this file for baseline scans in the required GitHub repository.

### PR scan

* **Purpose**: Scans the pull requests that could include new code and dependencies for vulnerabilities and security risks. This scan compares the new code against the baseline or the default branch and raises results based on findings and admission policies.
* **Trigger Type**: Pull request.
* **Setup**: Create a trigger for the required repository and branch.
* **Additional Parameters**: Pass extra parameters as part of the endorctl arguments.
* **Cloud Build Configuration**: Create a `cloudbuild.yaml` file using the [configuration file examples](#example-configuration-file) as a reference. Include this file for baseline scans in the required GitHub repository,

### Release scan

* **Purpose**: Scans code before it lands in production or pre-production environments. This is similar to a baseline scan, however, it is triggered when you push the code to a release branch or create a new release tag.
* **Trigger Type**: Push to branch or push to new tag.
* **Setup**: Create a trigger for the release branch or tag.
* **Cloud Build Configuration**: Create a `cloudbuild.yaml` file using the [configuration file examples](#example-configuration-file) excluding the `--as-default-branch argument` for release scans, and add this file to the required GitHub repository.

### Example configuration file

Here is an example `cloudbuild.yaml` configuration file to perform a baseline scan for Java project repository.

```
steps:
  # Step 1: Fetch The Trigger Branch
  # This step addresses a known issue where Cloud Build renames the pulled branch to main.
  # If you are not encountering this issue with your build, you can skip this step.
  - name: 'gcr.io/cloud-builders/git'
    entrypoint: 'bash'
    args:
      - '-c'
      - |
        echo "Fetching all branches..."
        git fetch origin
        echo "Checking out branch: ${BRANCH_NAME}"
        git checkout ${BRANCH_NAME}
  # Step 2: Build With Maven
  - name: 'maven:3.8.6-openjdk-11'
    entrypoint: 'mvn'
    args: ['clean', 'install']
    id: 'Build'
  # Step 3: Install latest version of endorctl
  - name: 'maven:3.8.6-openjdk-11'
    entrypoint: 'bash'
    args:
      - '-c'
      - |
        curl https://api.endorlabs.com/download/latest/endorctl_linux_amd64 -o endorctl
        echo "$(curl -s https://api.endorlabs.com/sha/latest/endorctl_linux_amd64)  endorctl" | sha256sum -c
        chmod +x ./endorctl
        ./endorctl --version
    id: 'Install latest version of endorctl'
  # Step 4: SCA Scan With EndorLabs
  - name: 'maven:3.8.6-openjdk-11'
    entrypoint: 'bash'
    args: ["-c", "./endorctl scan -n $$ENDOR_NAMESPACE --api-key=$$ENDOR_API_CREDENTIALS_KEY --api-secret=$$ENDOR_API_CREDENTIALS_SECRET --as-default-branch=true"]
    secretEnv: ['ENDOR_API_CREDENTIALS_KEY', 'ENDOR_API_CREDENTIALS_SECRET']
    env:
      - 'ENDOR_NAMESPACE=demo'
    id: 'SCA Scan With EndorLabs'

# Fetch Endor Labs API Token and Secret From Secrets Manager
availableSecrets:
  secretManager:
  - versionName: projects/{your-project-id}/secrets/endor-api-key/versions/1
    env: 'ENDOR_API_CREDENTIALS_KEY'
  - versionName: projects/{your-project-id}/secrets/endor-api-secret/versions/1
    env: 'ENDOR_API_CREDENTIALS_SECRET'

options:
  # Choose your log configuration
  logging: 'CLOUD_LOGGING_ONLY'
  # Select a private pool if the default runners do not meet the minimum requirements.
  pool:
    name: 'projects/{your-project-id}/locations/{your_location}/workerPools/{your_worker_pool_id}'
```

Check the example [configuration files](https://github.com/Endor-Solutions-Architecture/CI-CD-Examples/tree/main/gcp_cloud_build) and customize them for your requirements.

## Feedback

Was this page helpful?

Yes
No

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

Thanks for the feedback. Write to us at support@endor.ai to tell us more.
