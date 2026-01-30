---
url: https://docs.endorlabs.com/scan-with-endorlabs/manage-scan-profiles/configure-scanprofile-ui/
title: Configure scan profile through Endor Labs user interface | Endor Labs Docs
downloaded: 2026-01-26 10:07:57
---

Configure scan profile through Endor Labs user interface | Endor Labs Docs



* Type to search...

[Print entire section](/scan-with-endorlabs/manage-scan-profiles/configure-scanprofile-ui/_print.html)



# Configure scan profile through Endor Labs user interface

Learn how to configure scan profile through the Endor Labs user interface.

While scanning projects using the GitHub App, you can configure a scan profile and assign it to your projects directly from the Endor Labs user interface.

## Create a new scan profile

Create and customize a new scan profile to define scan parameters, toolchains, and projects.

1. Sign in to Endor Labs and click **Settings** under **Manage** in the left sidebar.
2. Select **SCAN PROFILES** and click **New Scan Profile**.
3. Enter a name for the scan profile and click **Create Scan Profile**.
4. Configure various settings like automated scan parameters and paths. See [Configure General scan profile settings](#configure-general-scan-profile-settings) for more information.
5. Select **TOOLCHAINS** and configure the toolchains. See [Configure toolchains](#configure-toolchains) for more information.
6. Select **PROJECTS** to associate the scan profile with projects. See [Associate projects with a scan profile](#associate-projects-with-a-scan-profile).

### Configure general scan profile settings

Configure the necessary scan settings to tailor scans for your projects.

1. Select the features that you want to enable for the scan profile.

   * **Enable pull request scans**: Automatically scans changes in the pull request.
   * **Enable pull request comments**: Adds scan results as comments in the pull request.
   * **Disable code snippet storage for SAST**: Disable storing the code snippet.

   See [automated scan parameters](../build-tools/#configure-automated-scan-parameters) to learn more.
2. Select the languages to scan and the languages for which you need to generate call graphs.

   If you don’t select any language, all the languages detected in the repository will automatically be selected for the scan.
3. Enter the paths to include or exclude in the scan.
4. Enter any additional environment variables, if required. Only the environment variables starting with `ENDOR_` are passed to the scan, all others are ignored.
5. Select an exporter to define what scan results to send, in which format, and to which external system.

   For example, you can select the SARIF exporter to export the scan results in the SARIF format. See [Export findings to GitHub Advanced Security](../../../scan-with-endorlabs/data-exporters/export-to-ghas/) for more information.
6. Configure Bazel settings, if required.

   * Select **Show Internal Targets as Dependencies** to include internal build targets in your dependency analysis while using Bazel as your build system.
   * Configure the following Bazel settings:

     + **Bazel Workspace Path**: Specify the location of the Bazel workspace.
     + **Target Selection**: Choose one of the following methods to define which targets should be scanned:

       - **Include Targets**: Specify individual Bazel targets to be scanned.
       - **Targets Query**: Use a Bazel query expression to define the targets dynamically.
     + **Excluded Targets**: If using **Include Targets**, do not set **Excluded Targets**, as they cannot be used together.

   See [Scan using Bazel](../../../scan-with-endorlabs/language-scanning/bazel/) for more details on Bazel scanning and target queries.
7. Click **Save Scan Profile** to save the toolchain configuration.

### Configure toolchains

Create and save a scan profile.

1. Select the operating system for the scan profile.
2. Select the architecture.
3. Select the toolchain available for the operating system-architecture combination.
4. Select the tool associated with the toolchain. For package managers like Python (pip), JavaScript (npm), and Android, you can configure a list of packages to install before the scan.
5. Select the version of the tool (or enter the package name if you chose a package in the previous step) and click **Add to Profile**.

   You can only assign one version of the tool for a scan profile for a particular operating system-architecture combination.

   You can also click **Custom** and define the custom version of the tool. See [Configure custom versions](#configure-a-custom-version-for-a-tool) for more information.

   The following image shows the creation of a scan profile for Go and JavaScript scans.
   ![Create Scan Profile](../../../images/ScanProfile_CreateScanProfile.png)
6. Click **Save Scan Profile** to save the toolchain configuration.

#### Configure a custom version for a tool

When you assign a version of the tool, you can choose to apply a custom version that is not provided by Endor Labs.

You must provide the following information.

* Version name
* The URL to download the archive package
* SHA256 checksum of the package
* The relative toolchain path, if required. The toolchain is extracted to the specified relative toolchain path if provided.

The following image shows a custom configuration for the Golang toolchain with Go 1.22.7 instead of the bundled 1.22.6.

![Custom toolchain](../../../images/ScanProfile_CustomToolChain.png)

### Associate projects with a scan profile

Assign projects to your scan profile.

1. Select **Actions > Add Projects**.

   ![Add Projects](../../../images/ScanProfile_AddProjects.png)
2. Search the project and click **Add to Scan Profile**.
   You can associate multiple projects with a scan profile, but you cannot apply multiple scan profiles to a single project.

## Manage scan profiles

You can edit, clone, delete, or set a default scan profile for a namespace.

### Set a default scan profile

You can set a default scan profile for a namespace, and all projects within that namespace will use this profile. Child namespaces inherit the default scan profile unless you override it by setting a different profile as the default within the child namespace.

1. Navigate to **Manage** > **Settings** in the left sidebar.
2. Select **SCAN PROFILES** to view the list of scan profiles.
3. Choose a scan profile, click the vertical ellipsis on the right side, and select **Set As Default**.

### Edit scan profile

You can modify the configuration of a scan profile after creating it.

1. Navigate to **Manage** > **Settings** in the left sidebar.
2. Select **SCAN PROFILES**.
3. Click on the vertical three dots of the scan profile you want to edit.
4. Select **Edit**.
5. Modify the scan profile details such as description, GitHub app features, languages, toolchains, projects it is associated with, etc.
6. Click **Save Scan Profile**.

### Clone scan profile

You can clone a scan profile so that existing configurations of the scan profile are duplicated with all parameters intact, ensuring faster setup and consistent scan settings.

1. Navigate to **Manage** > **Settings** in the left sidebar.
2. Select **SCAN PROFILES**.
3. Click on the vertical three dots of the scan profile you want to clone.
4. Select **Clone**.

### Delete scan profile

You can delete a scan profile from your namespace, which automatically removes it from any associated projects as well.

1. Navigate to **Manage** > **Settings** in the left sidebar.
2. Select **SCAN PROFILES**.
3. Click on the vertical three dots of the scan profile you want to delete.
4. Select **Delete**.
5. Click **Delete** to confirm the deletion of the scan profile from the namespace.

   ![Delete scan profile](../../../images/delete-scan-profile.png)

## Configure build tools

Instead of [configuring a custom version for a tool](#configure-a-custom-version-for-a-tool) every time a required version is not provided by Endor Labs, you can create a standard version and use it across all scan profiles. For example, you can add dotnet 5.0—which is not a standard supported version—to your build tools and make it available.

1. Navigate to **Manage** > **Settings** in the left sidebar.
2. Select **SCAN PROFILES** and click **BUILD TOOLS**.
3. Click **New Build Tool**.
4. Select the **OS** and **Architecture**.
5. Enter the required version, the download URL, and the SHA 256 checksum for verification. In advanced options, you can optionally specify a relative toolchain path.
   For example, you can enter these values to configure .NET 5.0 build chain:
   * **OS** - Linux
   * **ARCHITECTURE** - arm64
   * **TOOLCHAINS** - .NET
   * **NAME** - 5.0.408
   * **URL** - <https://builds.dotnet.microsoft.com/dotnet/Sdk/5.0.408/dotnet-sdk-5.0.408-linux-arm64.tar.gz>
   * **SHA256** - da88dxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
6. Use the **Relative Toolchain Path** to specify a custom installation directory for the tool.
7. Click **Add Build Tool**.

You will be able to choose this build tool in **TOOLCHAINS**, while creating a [scan profile](#create-a-new-scan-profile).

## Feedback

Was this page helpful?

Yes
No

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

Thanks for the feedback. Write to us at support@endor.ai to tell us more.
