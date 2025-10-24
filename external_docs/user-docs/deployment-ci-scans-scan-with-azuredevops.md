---
url: https://docs.endorlabs.com/deployment/ci-scans/scan-with-azuredevops/
title: Scanning in Azure Pipelines | Endor Labs Docs
downloaded: 2025-10-23 23:27:27
---

Scanning in Azure Pipelines | Endor Labs Docs



* Type to search...
* ---

[Print entire section](/deployment/ci-scans/scan-with-azuredevops/_print.html)



# Scanning in Azure Pipelines

Learn how to implement Endor Labs in an Azure Pipeline.

Azure Pipelines is a continuous integration and continuous delivery (CI/CD) service available in Azure DevOps ecosystem. It facilitates continuous integration, continuous testing, and continuous deployment for seamless building, testing, and delivery of software.

You can use Azure extension from Endor Labs to include Endor Labs within your Azure pipelines or add steps in your pipeline to manually download and use Endor Labs in your runner.

## Complete the prerequisites

Ensure that you complete the following prerequisites before you proceed.

### Set up an Endor Labs tenant

You must have an Endor Labs tenant set up for your organization. You can also set up namespaces according to your requirements. See [Set up namespaces](../../../administration/namespaces/)

### Configure Endor Labs authentication

Configure an API key and secret for authentication. See [managing API keys](../../../administration/api-keys/) for more information on generating an API key for Endor Labs. Store API key and secret as environment variables, `ENDOR_API_CREDENTIALS_KEY` and `ENDOR_API_CREDENTIALS_SECRET`.

### Enable Advanced Security in Azure

You need to enable Advanced Security in your Azure repository to view results in Azure.

1. Log in to Azure and open **Project Settings**.
2. Navigate to **Repos > Repositories** in the left navigation panel.
3. Select your repository.
4. Enable Advanced Security.
   ![Enable Advanced Security](../../../images/EnableAdvancedSecurity.png)

## Integrate Endor Labs with Azure pipelines with the Azure extension

To integrate Endor Labs with Azure pipelines, you need to set up the Azure extension. After you set up the extension, you can configure your pipeline to use Endor Labs.

#### Note

The Endor Labs Azure extension requires `code read`, `build read`, and `execute` permissions.

### Set up the Azure extension

1. Install the Endor Labs extension from the [Visual Studio Marketplace](https://marketplace.visualstudio.com/items?itemName=endorlabs.endorlabs-security-scan-task).
2. Log in Azure DevOps and select your project.
3. Select **Project Settings** from the left sidebar.
4. Select **Service Connections** under **Pipelines**.
5. Click **Create service connection**.
6. Select **Endor Labs** and click **Next**.
7. Enter `https://api.endorlabs.com` as the **Server URL**.
8. Enter the **API Key** and **API Secret** that you [created](#configure-endor-labs-authentication).
9. Enter the service connection name.
   The name you enter here is to be used inside the Azure pipeline.
10. Optionally, you can enter service management reference and description.
11. Select **Grant access permission to all pipelines** to provide access to Endor Lab’s service connection to your pipelines.

    #### Warning

    Ensure that you select this option if you want to use Endor Labs with your pipelines. Unless you enable the service connection, Endor Labs will not be available to your pipelines.
12. Click **Save**.

### Configure Azure pipeline to use Endor Labs

1. Create `azure-pipelines.yml` file in your project, if it doesn’t exist and enter values according to your requirement.
2. In the `azure-pipelines.yml` file, enter the task, `EndorLabsScan@0`, with the service connection name, Endor Labs namespace, and the SARIF file name.

   For example:

   ```
    steps:
     - task: EndorLabsScan@0
       inputs:
         serviceConnectionEndpoint: 'Endor'
         namespace: 'demo'
         sarifFile: 'scanresults.sarif'
   ```
3. Enter the task, `AdvancedSecurity-Publish@1`, if you wish to publish the scan results, which you can view under the Advanced Security tab in Azure DevOps.

   ```
   steps:
     - task: AdvancedSecurity-Dependency-Scanning@1
       displayName: Publish scan dependencies to Advanced Security
       inputs:
         SarifsInputDirectory: $(Build.SourcesDirectory)\
   ```

After a successful run of the pipeline, you can [view the results in Azure](#view-scan-results-in-azure).

### Endor Labs scan parameters

You can use the following input parameters in the `EndorLabsScan@0` task.

| Parameter | Description |
| --- | --- |
| `additionalArgs` | Add custom arguments to the endorctl scan command. |
| `phantomDependencies` | Set to `true` to enable phantom dependency analysis. (Default: `false`) |
| `sarifFile` | Set to a location on your hosted agent to output the findings in SARIF format. |
| `scanDependencies` | Scan Git commits and generate findings for all dependencies. (Default: `true`) |
| `scanPath` | Set the path to the directory to scan. (Default: `.`) |
| `scanSast` | Set to `true` to enable SAST scan. (Default: `false`) |
| `scanSecrets` | Scan source code repository and generate findings for secrets. See also `scanGitLogs`. (Default: `false`) |
| `scanGitLogs` | Perform a more complete and detailed scan of secrets in the repository history. Requires `scanSecrets` to be set as `true`. (Default: `false`) |
| `scanTools` | Scan source code repository for CI/CD tools. (Default: `false`) |
| `tags` | Specify a list of user-defined tags to add to this scan. Tags help you search and filter scans. |
| `scanPackage` | Scan a specified artifact or a package. The path to an artifact must be set with `scanPath`. (Default: `false`) |
| `scanContainer` | Scan a specified container image. Set the image with `image` and a project with `projectName`. (Default: `false`) |
| `projectName` | Specify a project name for a container image scan or for a package scan. |
| `image` | Specify a container image to scan. |

### Example Workflow

The following example workflow initiates a scan where all dependencies are scanned along with secrets. The findings are tagged with `Azure`. The scan generates a SARIF file and uploads to GitHub Advanced Security.

```
trigger:
- none

pool:
  name: Azure Pipelines
  vmImage: "windows-latest"

steps:
- task: EndorLabsScan@0
  inputs:
    serviceConnectionEndpoint: 'endorlabs-service-connection'
    namespace: 'endor'
    sarifFile: 'scanresults.sarif'
    scanSecrets: 'true'
    tags: `Azure`

- task: AdvancedSecurity-Publish@1
  displayName: Publish 'scanresults.sarif' to Advanced Security
  inputs:
   SarifsInputDirectory: $(Build.SourcesDirectory)\
```

## View scan results in Azure

After the pipeline runs, you can view the scan results in Azure.

1. Log in to Azure and navigate to your projects.
2. Select **Repos** > **Advanced Security** to view the scan results.
   ![View Azure advanced security](../../../images/azure-advanced-security.png)
3. Click an alert to view more details.
   ![View Azure alert](../../../images/azure-singleissue.png)
4. If you ran endorctl with `--secrets` flag, you can view if there are any secret leaks.
   ![View Azure secret leak](../../../images/azuresecretdetected.png)

   Click the entry to view more details.
   ![View Azure secret leak expanded](../../../images/azuresecretexpanded.png)

## Download and use endorctl in Azure pipeline

You can also choose to set up your pipeline to download endorctl and scan using Endor Labs without using the Azure extension.

### Configure Endor Labs variables in the pipeline

You can manage Endor Labs variables centrally by configuring them within your Azure project. You can assign these variables to various pipelines.

1. Log in to Azure and select **Pipelines > Library**.
2. Click **+Variable Group** to add a new variable group for Endor Labs.
3. Enter a name for the variable group, for example, `tenant-variables`, and click **Add** under **Variables**.
4. Add the following variables.
   * `ENDOR_API_CREDENTIALS_KEY`
   * `ENDOR_API_CREDENTIALS_SECRET`
   * `NAMESPACE`
     ![Create Variables](../../../images/createvariables.png)
5. Select the variable group that you created.
   ![Create Variables](../../../images/variableset.png)
6. Click **Pipeline Permissions**.
7. Click **+** to add the pipelines in which you want to use the variable group.
   ![Create Variables](../../../images/assignvariableset.png)

### Configure your Azure pipeline

1. Create `azure-pipelines.yml` file in your project, if it doesn’t exist.
2. In the `azure-pipelines.yml` file, customize the job configuration based on your project’s requirements.
3. Adjust the image field to use the necessary build tools for constructing your software packages, and align your build steps with those of your project.
   For example, update the node pool settings based on your operating system.

* Windows
* Ubuntu
* macOS

```
pool:
  name: Default
  vmImage: "windows-latest"
```

```
pool:
  name: Default
  vmImage: "ubuntu-latest"
```

```
pool:
  name: Default
  vmImage: "macOS-latest"
```

4. Update your default branch from main if you do not use main as the default branch name.
5. Modify any dependency or artifact caches to align with the languages and caches used by your project.
6. Enter the following steps in the `azure-pipelines.yml` file to download endorctl.

* Windows
* Ubuntu
* macOS

```
- bash: |
    echo "Downloading latest version of endorctl"
    VERSION=$(curl https://api.endorlabs.com/meta/version | grep -o '"Version":"[^"]*"' | sed 's/.*"Version":"\([^"]*\)".*/\1/')
    curl https://api.endorlabs.com/download/endorlabs/"$VERSION"/binaries/endorctl_"$VERSION"_windows_amd64.exe -o endorctl.exe
    echo "$(curl -s https://api.endorlabs.com/sha/latest/endorctl_windows_amd64.exe)  endorctl" | sha256sum -c
    if [ $? -ne 0 ]; then
      echo "Integrity check failed"
      exit 1
    fi
```

```
- bash: |
    echo "Downloading latest version of endorctl"
    VERSION=$(curl https://api.endorlabs.com/meta/version | grep -o '"Version":"[^"]*"' | sed 's/.*"Version":"\([^"]*\)".*/\1/')
    curl https://api.endorlabs.com/download/endorlabs/"$VERSION"/binaries/endorctl_"$VERSION"_linux_amd64 -o endorctl
    echo "$(curl -s https://api.endorlabs.com/sha/latest/endorctl_linux_amd64)  endorctl" | sha256sum -c
    if [ $? -ne 0 ]; then
      echo "Integrity check failed"
      exit 1
    fi
```

```
- bash: |
    echo "Downloading latest version of endorctl"
    VERSION=$(curl https://api.endorlabs.com/meta/version | grep -o '"Version":"[^"]*"' | sed 's/.*"Version":"\([^"]*\)".*/\1/')
    curl https://api.endorlabs.com/download/endorlabs/"$VERSION"/binaries/endorctl_"$VERSION"_macos_arm64 -o endorctl
    echo "$(curl -s https://api.endorlabs.com/sha/latest/endorctl_macos_arm64)  endorctl" | shasum -a 256 --check
    if [ $? -ne 0 ]; then
      echo "Integrity check failed"
      exit 1
    fi
```

7. Enter the steps to build your project if your project needs building and setup steps.
8. Enter the following step in the `azure-pipelines.yml` file to run endorctl scan to generate the SARIF file.

   You can run endorctl scan with [options](../../../endorctl/commands/scan/) according to your requirement, but you must include the `-s` option to generate the SARIF file.

   For example, use the `--secrets` flag to scan for secrets.

* Windows
* Ubuntu
* macOS

```
- script: |
    .\endorctl.exe scan -n $(NAMESPACE) -s scanresults.sarif
    env:
      ENDOR_API_CREDENTIALS_KEY: $(ENDOR_API_CREDENTIALS_KEY)
      ENDOR_API_CREDENTIALS_SECRET: $(ENDOR_API_CREDENTIALS_SECRET)
```

```
- script: |
    .\endorctl scan -n $(NAMESPACE) -s scanresults.sarif
    env:
      ENDOR_API_CREDENTIALS_KEY: $(ENDOR_API_CREDENTIALS_KEY)
      ENDOR_API_CREDENTIALS_SECRET: $(ENDOR_API_CREDENTIALS_SECRET)
```

```
- script: |
    .\endorctl scan -n $(NAMESPACE) -s scanresults.sarif
    env:
      ENDOR_API_CREDENTIALS_KEY: $(ENDOR_API_CREDENTIALS_KEY)
      ENDOR_API_CREDENTIALS_SECRET: $(ENDOR_API_CREDENTIALS_SECRET)
```

9. Enter the following task in the `azure-pipelines.yml` to publish the scan results.

```
- task: AdvancedSecurity-Publish@1
    displayName: Publish '.\sarif\scanresults.sarif' to Advanced Security
    inputs:
      SarifsInputDirectory: $(Build.SourcesDirectory)\
```

After a successful run of the pipeline, you can [view the results in Azure](#view-scan-results-in-azure).

### Azure Pipeline Examples

* Windows
* Ubuntu
* macOS

```
trigger:
- none

pool:
  name: Azure Pipelines
  vmImage: "windows-latest"

variables:
- group: tenant-variables

steps:
# All steps related to building of the project should be before this step.
# Implement and scan with Endor Labs after your build is complete.
- bash: |
    - bash: |
        echo "Downloading latest version of endorctl"
        VERSION=$(curl https://api.endorlabs.com/meta/version | grep -o '"Version":"[^"]*"' | sed 's/.*"Version":"\([^"]*\)".*/\1/')
        curl https://api.endorlabs.com/download/endorlabs/"$VERSION"/binaries/endorctl_"$VERSION"_windows_amd64.exe -o endorctl.exe
       echo "$(curl -s https://api.endorlabs.com/sha/latest/endorctl_windows_amd64.exe)  endorctl" | sha256sum -c
        if [ $? -ne 0 ]; then
          echo "Integrity check failed"
          exit 1
        fi

  displayName: 'Downloading latest version of endorctl'
  continueOnError: false

- script: |
    .\endorctl.exe scan -n $(NAMESPACE) -s scanresults.sarif
  displayName: 'Run a scan against the repository using your API key & secret pair'
  env:
    ENDOR_API_CREDENTIALS_KEY: $(ENDOR_API_CREDENTIALS_KEY)
    ENDOR_API_CREDENTIALS_SECRET: $(ENDOR_API_CREDENTIALS_SECRET)

- task: AdvancedSecurity-Publish@1
  displayName: Publish '.\sarif\scanresults.sarif' to Advanced Security
  inputs:
   SarifsInputDirectory: $(Build.SourcesDirectory)\
```

```
trigger:
- none

pool:
  name: Azure Pipelines
  vmImage: "ubuntu-latest"

variables:
- group: tenant-variables

steps:
# All steps related to building of the project should be before this step.
# Implement and scan with Endor Labs after your build is complete.
- bash: |
    - bash: |
        echo "Downloading latest version of endorctl"
        VERSION=$(curl https://api.endorlabs.com/meta/version | grep -o '"Version":"[^"]*"' | sed 's/.*"Version":"\([^"]*\)".*/\1/')
        curl https://api.endorlabs.com/download/endorlabs/"$VERSION"/binaries/endorctl_"$VERSION"_linux_amd64 -o endorctl
        echo "$(curl -s https://api.endorlabs.com/sha/latest/endorctl_linux_amd64)  endorctl" | sha256sum -c
        if [ $? -ne 0 ]; then
          echo "Integrity check failed"
          exit 1
        fi
        ## Modify the permissions of the binary to ensure it is executable
        chmod +x ./endorctl
        ## Create an alias of the endorctl binary to ensure it is available in other directories
        alias endorctl="$PWD/endorctl"

  displayName: 'Downloading latest version of endorctl'
  continueOnError: false

- script: |
    ./endorctl scan -n $(NAMESPACE) -s scanresults.sarif
  displayName: 'Run a scan against the repository using your API key & secret pair'
  env:
    ENDOR_API_CREDENTIALS_KEY: $(ENDOR_API_CREDENTIALS_KEY)
    ENDOR_API_CREDENTIALS_SECRET: $(ENDOR_API_CREDENTIALS_SECRET)

- task: AdvancedSecurity-Publish@1
  displayName: Publish '.\sarif\scanresults.sarif' to Advanced Security
  inputs:
   SarifsInputDirectory: $(Build.SourcesDirectory)/
```

```
trigger:
- none

pool:
  name: Azure Pipelines
  vmImage: "macos-latest"

variables:
- group: tenant-variables

steps:
# All steps related to building of the project should be before this step.
# Implement and scan with Endor Labs after your build is complete.
- bash: |
        echo "Downloading latest version of endorctl"
        VERSION=$(curl https://api.endorlabs.com/meta/version | grep -o '"Version":"[^"]*"' | sed 's/.*"Version":"\([^"]*\)".*/\1/')
        curl https://api.endorlabs.com/download/endorlabs/"$VERSION"/binaries/endorctl_"$VERSION"_macos_arm64 -o endorctl
        echo "$(curl -s https://api.endorlabs.com/sha/latest/endorctl_macos_arm64)  endorctl" | shasum -a 256 --check
        if [ $? -ne 0 ]; then
          echo "Integrity check failed"
          exit 1
        fi
        ## Modify the permissions of the binary to ensure it is executable
        chmod +x ./endorctl
        ## Create an alias of the endorctl binary to ensure it is available in other directories
        alias endorctl="$PWD/endorctl"
  displayName: 'Downloading latest version of endorctl'
  continueOnError: false

- script: |
    ./endorctl scan -n $(NAMESPACE) -s scanresults.sarif
  displayName: 'Run a scan against the repository using your API key & secret pair'
  env:
    ENDOR_API_CREDENTIALS_KEY: $(ENDOR_API_CREDENTIALS_KEY)
    ENDOR_API_CREDENTIALS_SECRET: $(ENDOR_API_CREDENTIALS_SECRET)

- task: AdvancedSecurity-Publish@1
  displayName: Publish '.\sarif\scanresults.sarif' to Advanced Security
  inputs:
   SarifsInputDirectory: $(Build.SourcesDirectory)/
```

## Feedback

Was this page helpful?

Yes
No

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

Thanks for the feedback. Write to us at support@endor.ai to tell us more.
