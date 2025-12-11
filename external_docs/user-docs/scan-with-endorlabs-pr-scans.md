---
url: https://docs.endorlabs.com/scan-with-endorlabs/pr-scans/
title: Pull Request scans | Endor Labs Docs
downloaded: 2025-12-11 11:33:25
---

Pull Request scans | Endor Labs Docs



* Type to search...
* ---

[Print entire section](/scan-with-endorlabs/pr-scans/_print.html)



# Pull Request scans

Scan pull requests created in your repository.

Scan pull requests as soon as they are raised in your repository. PR scans detect vulnerabilities in your branch when they are introduced, making it easier to identify and fix them early.

You can perform the following types of PR scans.

* [PR scan](#scan-prs-using-endorctl)
* [Incremental PR scan](#perform-incremental-pr-scan)

You can perform PR scans during the following deployments:

* [Using endorctl](#scan-prs-using-endorctl)
* [During CI workflows](#scan-prs-during-ci-workflows)
* [PR scans using the Endor Labs GitHub app](../../deployment/monitoring-scans/github-app/github-app-pr-scans/)
* [MR scans using the Endor Labs GitLab App](../../deployment/monitoring-scans/gitlab-app/gitlab-mr-scan/)

## Scan PRs using endorctl

You can scan pull requests or merge requests using endorctl for both GitHub and GitLab repositories.

Run the following command to scan PRs or merge requests after you commit to a pull request or merge request.

```
endorctl scan --pr
```

After you raise a pull request or merge request, the `--pr` flag enables scanning of the latest version of the pull request or merge request and stores the results separately from the main branches. The PR scan and its findings do not affect the main branch’s reporting.

Endor Labs stores the PR and MR scan findings in **PR Runs** for three weeks, after which they are erased to accommodate new PR scans.

### Set a baseline branch for PR scans

Setting up a baseline branch is recommended to establish a Git reference against which you can compare the changes introduced in pull requests or merge requests. You must regularly scan the baseline branch for vulnerabilities by either scheduling it (using the GitHub App or GitLab App) or triggering it using the `--pr-baseline` flag.

Usually, the first scanned branch becomes the baseline and is continuously monitored. A successful complete scan will resolve dependencies, run analytics, and generate call graphs for supported languages. See [set a default branch](../scanning-strategies/#set-a-default-branch).

By scanning a baseline branch, you establish a qualified reference with known vulnerabilities, and understand the current state of security. This reduces the risk of introducing vulnerabilities or breaking changes to your project.

Run the following command to set a baseline branch for PR scans.

```
endorctl scan --pr --pr-baseline=main
```

In the above example, the `main` branch is the baseline, and all PR scans will only display findings that were not already reported when the `main` branch was scanned.

## Perform incremental PR scan

The `--pr-incremental` flag scans only the parts of the codebase and dependencies that have changed since the last complete baseline scan, rather than scanning the entire codebase every time. It focuses on new or modified code that may introduce vulnerabilities or issues. The scan reports only findings that don’t exist in the baseline and are associated with changed dependencies in the pull request.

The baseline is detected automatically for GitHub App or GitLab App scans, or when PR comments are enabled. Otherwise, you must provide it using the `--pr-baseline` option. You can only perform an incremental scan after scanning a baseline or the default branch.

If a finding has been fixed in the baseline by upgrading or downgrading a dependency, and a PR modifies the same package, the finding will be flagged as new. This happens because there is no matching finding in the baseline and the dependency versions don’t match. To mitigate this, rebase the PR with the latest baseline content and re-run the PR check.

To initiate an incremental PR scan:

1. Run a complete scan successfully.
2. Run the following command to perform an incremental scan. Replace `main` with your baseline branch.

   ```
   endorctl scan --pr --pr-baseline=main --pr-incremental
   ```

During an incremental PR scan, Endor Labs first identifies packages and their dependencies. If changes are detected, only the modified packages are scanned. If the packages remain unchanged, the scan is skipped, and the `No changes found` message is displayed. The results of the PR incremental scan are available in **Projects** > **PR Runs**. Call graphs are generated only for the modified packages.

Incremental scans fail in the following cases.

* There are errors when resolving dependencies.
* The project’s path has changes.
* The project’s packages have failures.

In these cases, Endor Labs automatically performs a complete scan.

## Scan PRs during CI workflows

Configure your CI/CD tools to scan PRs and detect vulnerabilities during the workflow. You can also configure other [pull request flags](../../endorctl/commands/scan/#pull-request-ci-flags) to enhance your PR scanning workflow.

### GitHub Actions

The following example snippet shows you can set `pr: true` to enable PR scanning in [GitHub Actions](../../deployment/ci-scans/scan-with-github-actions/).

```
- name: 'Endor Labs Scan Push'
    if: ${{ github.event_name == 'push' }}
    uses: endorlabs/github-action@v1 # Replace v1 with the commit SHA of the latest version of the GitHub Action for enhanced security
    with:
    namespace: 'demo' # Replace with your Endor Labs tenant namespace
    scan_dependencies: true
    pr: true
    scan_summary_output_type: 'table'
    sarif_file: 'findings.sarif'
```

### Azure pipelines

The following example snippet shows you can pass `--pr` in `additionalArgs` to enable PR scanning in [Azure pipelines](../../deployment/ci-scans/scan-with-azuredevops/).

```
- task: EndorLabsScan@0
    inputs:
      serviceConnectionEndpoint: 'sanity-azure-devops-extension-staging'
      namespace: 'sanity.linux-latest'
      endorAPI: 'https://api.staging.endorlabs.com'
      logLevel: verbose
      tags: $(Build.BuildId)
      additionalArgs: '--output-type=summary --pr'
      sarifFile: scanresults.sarif
```

### Jenkins

The following example snippet shows how you can enable PR scanning using endorctl in [Jenkins](../../deployment/ci-scans/scan-with-jenkins/).

```
stage('endorctl Scan') {
    steps {
        // Download and install endorctl.
        sh '''#!/bin/bash
            echo "Downloading latest version of endorctl"
            VERSION=$(curl $ENDOR_API/meta/version | jq -r '.ClientVersion')
            ENDORCTL_SHA=$(curl $ENDOR_API/meta/version | jq -r '.ClientChecksums.ARCH_TYPE_LINUX_AMD64')
            curl $ENDOR_API/download/endorlabs/"$VERSION"/binaries/endorctl_"$VERSION"_linux_amd64 -o endorctl
            echo "$ENDORCTL_SHA  endorctl" | sha256sum -c
            if [ $? -ne 0 ]; then
                echo "Integrity check failed"
                exit 1
            fi
            chmod +x ./endorctl
            // Check endorctl version and installation.
            ./endorctl --version
            // Run the scan.
            ./endorctl scan -a $ENDOR_API -n $ENDOR_NAMESPACE --api-key $ENDOR_API_CREDENTIALS_KEY --api-secret $ENDOR_API_CREDENTIALS_SECRET --pr $ENABLE_PR_SCAN
        '''
    }
```

### GitLab pipelines

Enable MR scans in GitLab CI pipelines by adding the `--pr` flag. Configure your pipeline to run only on merge requests using `rules: - if: $CI_MERGE_REQUEST_IID`. See [Run MR scans](../../deployment/ci-scans/scan-with-gitlab/#run-mr-scans) and [Enable MR comments](../../deployment/ci-scans/scan-with-gitlab/#enable-mr-comments) for complete configuration examples.

### Bitbucket pipelines

The following example snippet shows how you can enable PR scanning using endorctl in [Bitbucket pipelines](../../deployment/ci-scans/scan-with-bitbucket/).

```
pull-requests:
    '**':
      - step:
          name: "Build and Test on PR"
          script:
            - mvn install -DskipTests
            - echo "Running Endor Labs PR Scan"
            - curl https://api.endorlabs.com/download/latest/endorctl_linux_amd64 -o endorctl
            - echo "$(curl -s https://api.endorlabs.com/sha/latest/endorctl_linux_amd64)  endorctl" | sha256sum -c
            - chmod +x ./endorctl
            - ./endorctl scan --pr --pr-baseline=main --languages=java --output-type=json -n $ENDOR_NAMESPACE --api-key $ENDOR_API_CREDENTIALS_KEY --api-secret $ENDOR_API_CREDENTIALS_SECRET | tee output.json
```

### CircleCI

The following example snippet shows how you can enable PR scanning using endorctl in [CircleCI](../../deployment/ci-scans/scan-with-circleci/).

```
- run:
    name: "Endor Labs Scan"
    command: |
    ./endorctl scan --dependencies --pr
```

### Google Cloud Build

The following example snippet shows how you can enable PR scanning using endorctl in [Google Cloud Build](../../deployment/ci-scans/scan-with-google-cloud-build/).

```
# Step 4: SCA Scan With EndorLabs
  - name: 'SCA scan'
    entrypoint: 'bash'
    args: ["-c", "./endorctl scan -n $$ENDOR_NAMESPACE --api-key=$$ENDOR_API_CREDENTIALS_KEY --api-secret=$$ENDOR_API_CREDENTIALS_SECRET --as-default-branch=true --pr"]
    secretEnv: ['ENDOR_API_CREDENTIALS_KEY', 'ENDOR_API_CREDENTIALS_SECRET']
    env:
      - 'ENDOR_NAMESPACE=demo'
    id: 'SCA Scan With EndorLabs'
```

See [Google Cloud Build configuration example](../../deployment/ci-scans/scan-with-google-cloud-build//#example-configuration-file) for more information.

## Scan PRs using the Endor Labs GitHub app

To automatically scan the PRs when they are raised, set the pull request preferences during the [installation of the GitHub App](../../deployment/monitoring-scans/github-app/#install-the-github-app) or edit the [integration preferences](../../deployment/monitoring-scans/github-app/#manage-github-apps-on-endor-labs) afterward.

The Endor Labs GitHub App provides a scan report with details about scan failures. The report includes warning and error logs, recommended actions when available, and a link to the full [scan history](../../managing-projects/scan-history/) for additional context.

To view the scan report:

1. Open the pull request where the scan failed.
2. Click on the three vertical dots and select **View Details** from the **Endor Labs Automated Scan** to view the scan report.

## View PR scan findings

View detailed results of your pull request scans in PR Runs. See [PR Runs](../../managing-projects/pr-runs/) to learn more.

---

##### [Pull Request comments](/scan-with-endorlabs/pr-scans/pr-comments/)

Learn how to enable and configure automated PR comments.

## Feedback

Was this page helpful?

Yes
No

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

Thanks for the feedback. Write to us at support@endor.ai to tell us more.
