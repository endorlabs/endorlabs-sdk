---
url: https://docs.endorlabs.com/scan-with-endorlabs/language-scanning/dotnet/
title: .NET | Endor Labs Docs
downloaded: 2025-12-11 11:34:59
---

.NET | Endor Labs Docs



* Type to search...
* ---

[Print entire section](/scan-with-endorlabs/language-scanning/dotnet/_print.html)



# .NET

Learn how to implement Endor Labs in repositories with .NET packages.

.NET is a free, cross-platform, open-source developer platform for building different types of applications. Endor Labs supports the scanning and monitoring of projects built on the .NET platform.

Using Endor Labs, application security engineers and developers can:

* Scan their software for potential security issues and violations of organizational policy.
* Prioritize vulnerabilities in the context of their applications.
* Understand the relationships between software components in their applications.

## System specifications for deep scan

Before you proceed to run a deep scan, ensure that your system meets the following specification.

| Project Size | Processor | Memory |
| --- | --- | --- |
| Small projects | 4-core processor | 16 GB |
| Mid-size projects | 8-core processor | 32 GB |
| Large projects | 16-core processor | 64 GB |

## Software prerequisites

The following prerequisites must be fulfilled:

* Make sure your repository includes one or more files with `.cs` extension.
* Dependency resolution and reachability analysis is supported only for SDK-style .NET projects.
* One or more `*.csproj` files must be present in your repository.
* The .NET command or NuGet command must be installed and available on the host system.
* At least one .NET SDK installed on the system must be compatible with the project’s `global.json` file settings.

**Note**

To check your available SDK versions you can run the command `dotnet --info` or `dotnet --list-sdks`.

## Run a scan

Use the following options to scan your repositories. Perform a scan after building the projects.

### Option 1 - Quick scan

Perform a quick scan to get quick visibility into your software composition. This scan won’t perform reachability analysis to help you prioritize vulnerabilities.

You must restore your .NET projects before running a quick scan. Additionally, ensure that the packages are downloaded into the local package caches and that the build artifacts are present in the standard locations.

1. Run the following commands to resolve dependencies and create the necessary files to scan your .NET project.

   To ensure that the build artifacts `project.assets.json` file is generated and dependencies are resolved run:

   ```
   dotnet restore
   ```

   If you use NuGet instead run:

   ```
   nuget restore
   ```

   To create a `packages.lock.json` file if your project uses a lock file run:

   ```
   dotnet restore --use-lock-file
   ```

   If `project.assets.json` or `packages.lock.json` are not present and if the project is buildable, endorctl will restore the project and create a `project.assets.json` or a `packages.lock.json` file to resolve dependencies.
2. You can run a quick scan with the following commands:

   ```
   endorctl scan --quick-scan
   ```

   You can perform the scan from within the root directory of the Git project repository, and save the local results to a `results.json` file. The results and related analysis information are available on the Endor Labs user interface.

   ```
   endorctl scan --quick-scan -o json | tee /path/to/results.json
   ```

   You can sign in to the Endor Labs user interface and navigate to **Projects** from the left sidebar to review your project results.

### Option 2 - Deep scan

Use the deep scan to perform dependency resolution, reachability analysis, and generate call graphs. You can do this after you complete the quick scan successfully.

You must restore and build your .NET projects before running a deep scan. Additionally, ensure that the packages are downloaded into the local package caches and that the build artifacts are present in the standard locations.

1. Run the following commands to restore and build your project. This may vary depending on your project’s configuration.

   ```
   dotnet restore
   dotnet build
   ```
2. You can run a deep scan with the following commands:

   ```
   endorctl scan
   ```

   Use the following flags to save the local results to a `results.json` file. The results and related analysis information are available on the Endor Labs user interface.

   ```
   endorctl scan -o json | tee /path/to/results.json
   ```

When a deep scan is performed all private software dependencies are completely analyzed by default if they have not been previously scanned. This is a one-time operation and will slow down initial scans, but won’t impact subsequent scans.

Organizations might not own some parts of the software internally and findings are actionable by another team. These organizations can choose to disable this analysis using the flag `disable-private-package-analysis`. By disabling private package analysis, teams can enhance scan performance but may lose insights into how applications interact with first-party libraries.

Use the following command flag to disable private package analysis:

```
endorctl scan --disable-private-package-analysis
```

You can sign into the Endor Labs user interface and select **Projects** from the left sidebar to review your project results.

### Configure private NuGet package repositories

Endor Labs supports fetching and scanning dependencies from private NuGet package registries. Endor Labs will fetch resources from authenticated endpoints and perform the scan, allowing you to view the resolved dependencies and findings. See [NuGet package manager integrations](../../../integrations/package-manager/nuget-private-package-manager/) for more information on configuring private registries.

## Understand the scan process

A `*.csproj` file is an XML-based C# project file that contains information about the project, such as its source code files, references, build settings, and other configuration details. The dependencies and findings are listed individually for every `.csproj` file. The scan discovers all `*.csproj` files and uses these files to resolve the appropriate dependency graph of your project.

(Beta) Endor Labs scans the .NET projects that are using the [Central Package Management feature](https://learn.microsoft.com/en-us/nuget/consume-packages/central-package-management#enabling-central-package-management) of NuGet for the packages declared as:

* Package references in `Directory.Build.props` or `Directory.Packages.props` files.
* Package references in any `*.props` file and the prop file is imported in the `.csproj` file.
* Package references in `*.Targets` file.

**Note**

You may not be able to view the **Requested version** of the packages on the Endor Labs user interface

* For the packages declared as package version in `*.Targets` file.
* If you are importing the packages into the `*.csproj` file using MSBuild keywords in the path variables.

Endor Labs enriches your dependency graph to help you understand if your dependencies are secure, sustainable, and trustworthy. This includes Endor Labs risk analysis and scores, if a dependency is direct or transitive, and if the source code of the dependency is publicly auditable.

Software composition analysis for .NET is performed in the following ways:

* [Using Project.assests.json](#how-does-dependency-resolution-happen-using-projectassetsjson)
* [Using package.lock.json](#how-does-dependency-resolution-happen-using-packagelockjson)

### How does dependency resolution happen using Project.assets.json

The `project.assets.json` file is used in .NET projects to store metadata and information about the project’s dependencies and assets.

Endor Labs fetches resolved package versions, paths to the dependencies’ assets, such as assemblies and resources, and other related information from this file. If a project does not include a `project.assets.json` file, it is generated through the `dotnet restore` or the `nuget restore` command. This command uses all the configured sources to restore dependencies as well as project-specific tools that are specified in the project file.

**Note**

If the host machine has .NET Core or .NET 5+ installed, the dotnet restore command is used to generate the `project.assets.json` file. The `nuget restore` command is used to generate the `project.asssets.json` file for earlier versions of the .NET frameworks.

### How does dependency resolution happen using package.lock.json

The `package.lock.json` file is used in .NET projects to lock dependencies and their specific versions. It is a snapshot of the exact versions of packages installed in a project, including their dependencies and sub-dependencies, requested versions, resolved versions, and contenthash. The lock file provides a more dependable, uniform, and accurate representation of the dependency graph.

In Endor Labs’ dependency management, the resolution of dependencies is primarily based on `package.lock.json`, which takes precedence over `projects.assets.json` to resolve dependencies.

Endor Labs fetches the dependency information from `package.lock.json` and creates a comprehensive dependency graph. The vulnerabilities associated with the dependencies are listed on the Endor Labs’ user interface.

If the `package.lock.json` file is not present in the repository, Endor Labs triggers the restore process to generate the `package.lock.json` file and uses it to perform the dependency scans.

### Resolving package names from props files

endorctl attempts to evaluate MSBuild property values when they are composed of variables, as long as the variables are defined within the same file for example, `Directory.Build.props`. This enables accurate resolution of package names and versions, even if they are not explicitly declared in the `.csproj` file.

For example, in a setup like

`test.csproj`

```
<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <TargetFrameworks>net8</TargetFrameworks>
  </PropertyGroup>
  <ItemGroup>
    <PackageReference Include="Newtonsoft.Json" Version="13.0.3" />
  </ItemGroup>
</Project>
```

`Directory.Build.props`

```
<Project>
  <PropertyGroup>
    <CompanyName>via-build-prop</CompanyName>
    <AssemblyName>$(CompanyName).$(MSBuildProjectName)</AssemblyName>
  </PropertyGroup>
</Project>
```

When generating package names for .NET projects, the system evaluates the `AssemblyName` property defined in the project’s `.props` file. Instead of using a generic name like `test`, the system applies the evaluated value, for example, `via-build-prop.test`. This approach enables consistent and customizable package naming based on MSBuild properties.

### How Endor Labs performs static analysis on the code

Endor Labs performs static analysis on the C# code based on the following factors:

* Call graphs are created for your package. These are then combined with the call graphs of the dependencies in your dependency tree to form a comprehensive call graph for the entire project.
* Endor Labs looks for the project’s `.dll` files typically located within the bin directory.
* Endor Labs performs an inside-out analysis of the software to determine the reachability of dependencies in your project.
* The static analysis time may vary depending on the number of dependencies in the package and the number of packages in the project.

### Known Limitations

* When using the GitHub app, either resolve all the private and internal dependencies, or [Configure NuGet private repositories](#configure-nuget-private-repositories) before running a scan.
* When working with old-style MSBuild projects, we recommend scanning them through [Continuous Integration (CI)](../../../deployment/ci-scans/) after building the project to ensure that the .NET build system generates the required `obj/project.assets.json` file. For [monitoring scans](../../../deployment/monitoring-scans/), support for restoring dependencies in Windows projects is limited. This may lead to **restore or build errors**, potentially causing unexpected scan results.

### Call graph limitations

* You must install .NET 7.0.1 (SDK 7.0.101) or later on the host system.
* The following .NET programming languages are not supported for dependency resolution or call graph generation:
  + Projects written in F#
  + Projects written in Visual Basic
* Endor Labs’ call graph support for .NET is based on [Microsoft’s Common Intermediate Language](https://learn.microsoft.com/en-us/dynamicsax-2012/appuser-itpro/compile-into-net-framework-cil) (CIL). Artifacts such as `.exe` or `.dll` files must be available in the project’s standard workspace through a build and restore or a restored cache.

## Troubleshoot errors

Here are a few error scenarios that you can check for and attempt to resolve them.

* **Host system check failure errors**:
  .NET or NuGet is not installed or not present in the PATH environment variable. Install NuGet and try again.
* **Unresolved dependency errors**:
  This error occurs when the `.csproj` file can not be parsed or if it has syntax errors.

## Feedback

Was this page helpful?

Yes
No

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

Thanks for the feedback. Write to us at support@endor.ai to tell us more.
