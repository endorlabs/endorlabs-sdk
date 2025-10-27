---
url: https://docs.endorlabs.com/deployment/monitoring-scans/jenkins-supervisory-scan/
title: Set up Jenkins pipeline for supervisory scans | Endor Labs Docs
downloaded: 2025-10-27 13:00:20
---

Set up Jenkins pipeline for supervisory scans | Endor Labs Docs



* Type to search...
* ---

[Print entire section](/deployment/monitoring-scans/jenkins-supervisory-scan/_print.html)



# Set up Jenkins pipeline for supervisory scans

Learn how to use Endor Labs Jenkins pipeline to conduct organization wide supervisory scans

Use the Endor Labs Jenkins pipeline to scan all the repositories in your organization and view consolidated findings. This pipeline runs on your organization’s Jenkins infrastructure and enables administrators to run organization-level supervisory scans easily. It is designed to work in GitHub Cloud and GitHub enterprise server environments.

The Jenkins pipeline carries out the following actions.

* Pulls the Endor Labs Docker image required to perform the scan.
* Synchronizes GitHub organization repositories to a specified namespace on the Endor Labs platform.
* Retrieves the project list or the GitHub repositories for the given tenant’s namespace.
* Groups the projects into batches to optimize scan execution.
* Runs endorctl scans on each batch of projects simultaneously.

## Scan the repositories in your organization

The Jenkins Pipeline script is available in the [`github-org-scan-docker.groovy`](https://github.com/endorlabs/jenkins-org-scan/blob/main/github-org-scan-docker.groovy) file.

To scan the repositories in your organization:

1. [Generate Endor Labs API credentials](../../../administration/api-keys/)
2. [Configure GitHub cloud or GitHub enterprise server credentials](#configure-github-credentials)
3. [Configure the Jenkins job](#configure-the-jenkins-job)

### Configure GitHub credentials

Configure the required credentials needed to access GitHub and Endor Labs in the Jenkins pipeline script. You can configure these values from the Jenkins user interface.

* `GITHUB_TOKEN`- Enter the GitHub token that has permission to access all the repositories in the organization.
* `ENDOR_LABS_API_KEY`- Enter the Endor Labs API key that you generated.
* `ENDOR_LABS_API_SECRET`- Enter the Endor Labs API secret generated while creating the Endor Labs API key.

### Configure GitHub cloud credentials

Configure the following GitHub cloud parameters in the Jenkins pipeline script.

#### Required Parameters for GitHub cloud

* `AGENT_LABEL`- This is a string parameter. Enter the label used to identify the Jenkins agents. The Jenkins job will run on the agents that have this label.
* `GITHUB_ORG`- This is a string parameter. Enter the organization name in GitHub.
* `ENDOR_LABS_NAMESPACE`- This is a string parameter. The **namespace** of your organization tenant in Endor Labs.

#### Optional Parameters for GitHub cloud

* `ENDOR_LABS_API`- This is a string parameter. This is only required if the tenant **namespace** is configured on the Endor Labs staging environment.
* `ADDITIONAL_ARGS`- This is a string parameter. Use this field to pass any additional parameter to the `endorctl` scan.
* `NO_OF_THREADS`- This is a string parameter. Enter the number of Jenkins agents that can be used in parallel for the `endorctl` scan. If you have 10 Jenkins agents configured with the given `AGENT_LABEL`, you can enter this value as 9, 1 agent is used for the main job. If not specified, this value defaults to **5**.
* `ENDORCTL_VERSION`- This is a string parameter. Specify the version of the `endorctl` Docker container. Defaults to the latest version.
* `SCAN_TYPE`- This is a string parameter. Set this to `git` to scan commits or `github` to fetch info from the GitHub API. Defaults to [`git`, `analytics`].
* `SCAN_SUMMARY_OUTPUT_TYPE`- This is a string parameter. Use this field to set the desired output format. Supported formats: **json**, **yaml’**, **table**, **summary**. Defaults to **table**.
* `LOG_LEVEL`- This is a string parameter. Use this field to set the log level of the application. Defaults to **info**.
* `LOG_VERBOSE`- This is a string parameter. Use this field to make the log verbose.
* `LANGUAGES`- This is a string parameter. Use this field to set programming languages to scan. Supported languages: `c#`,`go`, `java`, `javascript`, `php`, `python`, `ruby`, `rust`, `scala`, `typescript`. Defaults to all supported languages.
* `ADDITIONAL_ARGS`- This is a string parameter. Use this field to pass any additional parameters to the endorctl scan.

### Configure GitHub enterprise server credentials

Configure the following GitHub enterprise server parameters in the Jenkins pipeline script.

#### Required Parameters for GitHub enterprise server

* `AGENT_LABEL` - This is a string parameter. Enter the label used to identify the Jenkins agents. The Jenkins job will run on the agents that have this label.
* `GITHUB_ORG` - This is a string parameter. Enter the organization name in GitHub.
* `ENDOR_LABS_NAMESPACE` - This is a string parameter. The **namespace** of your organization tenant in Endor Labs.
* `GITHUB_API_URL` - This is a string parameter. Enter the API URL of the GitHub enterprise server. This is normally in the form of `<FQDN of GitHub Enterprise Server>/api/v3`. For example, `https://ghe.endorlabs.in/api/v3`.

#### Optional Parameters for GitHub enterprise server

* `ENDOR_LABS_API` - This is a string parameter. This is only required if the tenant **namespace** is configured on the Endor Labs staging environment.
* `GITHUB_DISABLE_SSL_VERIFY` - This is a boolean parameter. This should be used when you want to skip SSL Verification while cloning the repository.
* `GITHUB_CA_CERT` - This is a multi-line string parameter. This should be used to provide the content of the CA Certificate (PEM format) of the SSL Certificate used on the GitHub Enterprise Server.
* `PROJECT_LIST` - This is a multi-line string parameter. This should be used to provide a list of projects to scan.
* `SCAN_TYPE` - This is a string parameter. Set this to `git` to scan commits or `github` to fetch info from the GitHub API. Defaults to [`git`, `analytics`].
* `SCAN_SUMMARY_OUTPUT_TYPE` - This is a string parameter. Use this field to set the desired output format. Supported formats: **json**, **yaml**\*, **table**, **summary**. Defaults to **table**.
* `LOG_LEVEL` - This is a string parameter. Use this field to set the log level of the application. Defaults to **info**.
* `LOG_VERBOSE` - This is a string parameter. Use this field to generate verbose logs.
* `LANGUAGES` - This is a string parameter. Use this field to set programming languages to scan. Supported languages: `c#`, `go`, `java`, `javascript`, `php`, `python`, `ruby`, `rust`, `scala`, `typescript`. Defaults to all supported languages.
* `ADDITIONAL_ARGS` - This is a string parameter. Use this field to pass any additional parameters to the endorctl scan.
* `PROJECT_LIST` - This is a multi-line string parameter. List of projects to scan. Even though all projects are synchronized, scans run only on the provided projects.
* `SCAN_PROJECTS_BY_LAST_COMMIT` - This is a string parameter. This parameter is used to filter projects based on the date of the last commit. Enter a number (integer) value for this parameter. The value of 0 means that projects won’t be filtered based on last commit date. Any positive integer is used to calculate the duration in which a commit will add the project for further scanning. If a project did not have a commit in that interval, it will be skipped.
  If a proper SSL Certificate (a certificate issued by a well-known CA) is not used for GitHub Enterprise, the `sync-org` command fails and Endor Labs cannot fetch the projects or repositories to scan from the GitHub enterprise server. You can use this field to provide the list of projects or repositories to scan one per line.
  For example:

  ```
          https://github-test.endorlabs.in/pse/vuln_rust_callgraph.git
          https://github-test.endorlabs.in/pse/vulnerable-golang.git
          https://github-test.endorlabs.in/pse/java-javascript-vulnerable-repo.git
          https://github-test.endorlabs.in/pse/multi-lang-repo.git
  ```
* `EXCLUDE_PROJECTS` - This is a multi-line string parameter. Use this parameter to list projects or repositories to exclude from the scan.
* `NO_OF_THREADS` - This is a string parameter. Enter the number of Jenkins agents that can be used in parallel for the `endorctl` scan. If you have 10 Jenkins agents configured with the given `AGENT_LABEL`, you can enter this value as 9. If not specified, this value defaults to **5**.

### Configure the Jenkins job

Use the following procedure to configure the Jenkins pipeline and scan the repositories in your organization.

1. Sign in to Jenkins
2. Configure [an Endor Labs API Key](../../../administration/api-keys/) and [GitHub](#configure-github-credentials) credentials correctly for your environment.
3. Click **+ New Item**, to create a new Jenkins job.
4. Enter the name of the new pipeline
5. Select **Pipeline** and click **OK**.
6. Select **This project is parameterised** and add the parameters based on your requirements.
7. From the **Pipeline** section, for **Definition**, select **Pipeline script from SCM**
8. For **SCM** select **Git**
9. For the **Repository URL**, enter either `git@github.com:endorlabs/jenkins-org-scan.git` or `https://github.com/endorlabs/jenkins-org-scan.git`.
10. For **Credentials**, enter the credentials required for cloning the repository entered in the previous step.
11. In **Branches to build**, enter `*/main`.
12. For **Script Path**, enter `github-org-scan-docker.groovy`.
13. Select **Lightweight checkout**.
14. Click **Save**.

The Jenkins pipeline is highly customizable and adaptable to various GitHub environments and scanning requirements. It streamlines the process of running endorctl scans on your repositories efficiently.

## Feedback

Was this page helpful?

Yes
No

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

Thanks for the feedback. Write to us at support@endor.ai to tell us more.
