---
url: https://docs.endorlabs.com/scan-with-endorlabs/scan-containers/
title: Scan containers | Endor Labs Docs
downloaded: 2026-01-16 09:51:11
---

Scan containers | Endor Labs Docs



* Type to search...

[Print entire section](/scan-with-endorlabs/scan-containers/_print.html)



# Scan containers

Learn how to scan your containers with Endor Labs.

**Important**

Container scanning now has its own dedicated command: `endorctl container scan`.

The `endorctl scan --container` commands are deprecated will be removed after a three-month deprecation period.

Migrate to `endorctl container scan` command to ensure continued compatibility. For more details, see [Container scan commands migration guide](../scan-containers/container-migration/).

Containers help developers create, test, and deploy applications in a consistent environment. Container images include standalone or executable files encompassing files, libraries, and dependencies needed to run a container. They include several open-source software, making them vulnerable to open-source risks.

Gaining visibility into container images is essential to identify and prioritize risks or maintain compliance obligations.

Endor Labs container scan detects and reports known vulnerabilities and other risks in:

* **Operating system packages:** Identifies packages installed through the container’s base operating system package manager.
* **Programming language packages:** Identifies packages installed through language-specific package managers.
* **Libraries and dependencies:** Identifies static and dynamic libraries, and runtime dependencies required by the application.

Additionally, it generates an **SBOM (Software Bill of Materials)** that details all components, their versions, and associated metadata, providing a complete inventory of the container’s contents.

Upgrade to endorctl version 1.6.734 or higher to ensure accurate container scan results. Sometimes, container scans performed with older endorctl versions may yield different or no results.

## Verify access to container registries

If the container image is in a private Docker registry, you must authenticate the container client before the scan.

Here are a few commands to authenticate the container client.

Authenticate to a Docker registry

```
docker login <host> -u <user_name> -p <password>
```

[Learn more](https://docs.docker.com/reference/cli/docker/login/)




Authenticate to a Podman registry

```
podman login -u <user_name> -p <password> <host>
```

[Learn more](https://docs.podman.io/en/stable/markdown/podman-login.1.html)
[Endor Labs Podman troubleshooting](https://docs.endorlabs.com/troubleshooting/podman/)




Authenticate with containerd

You must configure the containerd config file to authenticate with the container registry.

[Learn more](https://github.com/containerd/containerd/blob/main/docs/cri/registry.md)

## Run the endorctl scan

Endor Labs supports the following methods of scanning container images:

* **[Scan container images in a Git repository](#scan-container-images-in-a-git-repository)**: Use this approach to scan images built within your repository using a Dockerfile.
* **[Scan container images as a standalone project](#scan-container-images-in-a-git-repository)**: Use this approach to scan base or golden images that are shared across multiple repositories or applications.
* **[Scan container image tarball](#scan-container-image-tarball)**: Use this to scan images saved as tar files, such as base images exported from Docker, to generate dependency, SBOM, and vulnerability reports.

### Scan container images in a Git repository

Run the following command to scan a container image built in a specific repository. Specify the project path using the `--path` argument and the container image name using the `--image` argument. This associates the container with the Git repository and branch of the project.

```
endorctl container scan --image=<image_name:tag> --path=users/janedoe/endorlabs/npm/exampleproject
```

You can also scan multiple container images as part of a single repository.

```
endorctl container scan --image=<image_name1:tag> --path=users/janedoe/endorlabs/npm/exampleproject
endorctl container scan --image=<image_name2:tag> --path=users/janedoe/endorlabs/npm/exampleproject
endorctl container scan --image=<image_name3:tag> --path=users/janedoe/endorlabs/npm/exampleproject
```

You can tag findings with the corresponding container image name and tag. This lets you filter container-related findings in the user interface or through the API.

```
endorctl container scan --image=<image_name:tag> --path=users/janedoe/endorlabs/npm/exampleproject --finding-tags=<image_name:tag>
```

### Scan container images as a standalone project

Run the following command to scan a container image from a registry. Specify the project name using the `--project-name` argument, and the container image name and tag using the `--image` argument.

```
endorctl container scan --image=<image_name:tag> --project-name=<endor_project_name>
```

To keep multiple versions of a container image in a container-only project, include the `--as-ref` flag.

```
endorctl container scan --image=<image_name:tag> --project-name=<endor_project_name> --as-ref
```

You can tag findings with the corresponding container image name and tag. This lets you filter container-related findings in the user interface or through the API.

```
endorctl container scan --project-name=<endor_project_name> --image=<image_name:tag>  -as-ref --finding-tags=<image_name:tag>
```

**Important**

To associate a container scan with an existing SCA scan for a project, you must use the `--path` argument specifying the same project path used for the SCA scan. You cannot associate a container scan with an SCA scan for a project using the `--project-name` parameter.

### Scan container image tarball

You can save a container image as a tarball and scan it with endorctl to generate a report containing dependencies, SBOM details, and security findings.

1. Ensure that you have the container image available locally.

   ```
   docker pull alpine:latest
   ```
2. Export the image to a tarball file.

   ```
   docker save alpine:latest -o alpine-latest.tar
   ```
3. Perform the endorctl scan.

   ```
   endorctl container scan --image=alpine:latest
   --project-name=<endor_project_name>
   --image-tar=/absolute/path/to/alpine-latest.tar
   ```

**Note**

* `--image-tar` must point to the absolute path of the tarball file.
* `--image=<name:tag>` is optional but recommended. It explicitly identifies the container image inside the tarball.

## Run container scan in CI pipelines

You can integrate container scanning into CI pipelines to automatically detect vulnerabilities and ensure the security of container images during the build and deployment process.

To perform container scanning in CI pipelines using GitHub Actions, set the `scan_container` parameter to `true` in the GitHub Actions script. Additionally, you must provide the `image` parameter with the container image you want to scan.

See [Performing scans in CI/CD pipelines](../../deployment/ci-scans/) for more information.

### Understand container scan

Endor Labs fetches the container image from a container registry or loads it from a local file to scan containers. It then proceeds to extract the layers of the container image. It traverses the filesystem of each layer to identify files and directories. It looks for known package manager and metadata files to gather information about installed packages and their versions. It identifies various components and dependencies within the image and presents the findings in CLI and the Endor Labs user interface.

#### Discover base images of containers

A container image is often built upon a base image that is a foundational layer including an operating system and other essential components. It’s crucial to understand what’s in the base image for a thorough security assessment.

You can distinguish the base image related vulnerabilities from the application layer using any of the following methods:

* **Scan Sequence** - First, scan the base image. Then, scan any subsequent images built on that base image to distinguish vulnerabilities specific to the base image from those introduced by the other layers.
* **Docker file label** - Set the label directly in your Dockerfile with a command such as `LABEL org.opencontainers.image.base.name="openjdk:17-slim"`.
* **Build time label** - Include the base image label during the build process with the `--label` flag, specifying both the base image and, optionally, its exact version via SHA256 hash. For example:

```
   docker build -t tictactoe:latest --label "org.opencontainers.image.base.name=openjdk@sha256:eddacbc7e24bf8799a4ed3cdcfa50d4b88a323695ad80f317b6629883b2c2a78" .
```

![base image](../../images/base_image.png)

#### Create finding policies for containers

Container base images from untrusted sources may lack proper security audits or fail to comply with organizational standards, increasing the risk of vulnerabilities being exploited. To address this, you can configure a finding policy to detect unauthorised base images and raise a critical finding.

For example, to allow only base images that start with `gcp` or `ghcr`, use the [Container policy template](../../managing-policies/finding-policies/container-policies/) and **Specify Base Image Name Regex** as `^gcp`, `^ghcr`.

See also [Create a finding policy from template](../../managing-policies/finding-policies/#create-a-finding-policy-from-template).

![finding policy template](../../images/container_scan_policy.png)

## Supported languages and package managers

The dependencies associated with the following list of components are identified in the endorctl scan.

| OS / Language | Package Manager Packaging | Version Support |
| --- | --- | --- |
| Alpine | apk | 3.20, 3.19, 3.18, 3.17, 3.16, 3.15, 3.14, 3.12, 3.11, 3.10 |
| Debian | dpkg | 8, 9, 10, 11, 12 |
| Ubuntu | dpkg | 18.04, 20.04, 22.04, 24.04, 24.10 |
| Red Hat | RPM | 5, 6, 7, 8, 9 |
| Fedora | RPM | 40, 39 |
| Amazon Linux | RPM | 1, 2, 2022, 2023 |
| Oracle Linux | RPM | 7, 8, 9 |
| .NET | `*.dll`, `*.exe` |  |
| Objective-C | CocoaPods |  |
| Go | Go binaries |  |
| Java | jar, ear, war, native-image |  |
| JavaScript | package.json |  |
| PHP | Composer |  |
| Python | wheel, egg |  |
| Ruby | gem |  |
| Rust | Cargo |  |

Endor Labs recognizes only the installed dependencies. Declared but uninstalled dependencies in the container image are not recognized.

### View container findings

To view findings from the container scan:

1. Select **Projects** from the left sidebar.
2. Select the project for which you want to view the container findings.
   ![container overview](../../images/container-overview.png)
3. Select **Containers** from the preset filters.
4. To view and filter dependencies based on the container images, click **Container Layers** and select to view **All Layers**, **Base Image Layers Only**, or **Application Layers Only**.

   ![Filter container findings](../../images/filter_base-images.png)

### How Endor Labs derives container findings

Endor Labs’ container scanning results rely on OVAL feeds from distributions, which provide accurate, vetted vulnerability data, excluding disputed or irrelevant entries. OS dependency results are based on data from distribution developers, while for language package dependencies, we complement published data with our proprietary research.

Endor Labs categorizes the severity of vulnerabilities detected in container scans as follows:

* Use the severity assigned by the distribution, if it exists.
* Use the NVD severity if the distribution does not provide the severity.
* Report the vulnerability as `Medium` if there is no severity assigned by the distribution, or the NVD severity is not known or can’t be matched.

Endor Labs doesn’t report the following vulnerabilities:

* Minor vulnerabilities in Debian and Ubuntu.
* Disputed vulnerabilities withdrawn from NVD.

### Limitations of container findings

* Scanning Windows containers is not supported.
* Docker file scans are not currently supported.
* Container registry direct integrations are not currently supported.
* Support for scanning binary files inside a container is limited.
* Endor scores are not calculated for findings reported in the container scan.

## Feedback

Was this page helpful?

Yes
No

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

Thanks for the feedback. Write to us at support@endor.ai to tell us more.
