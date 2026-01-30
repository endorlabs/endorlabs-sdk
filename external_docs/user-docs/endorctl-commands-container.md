---
url: https://docs.endorlabs.com/endorctl/commands/container/
title: container | Endor Labs Docs
downloaded: 2026-01-29 22:20:26
---

container | Endor Labs Docs



* Type to search...

[Print entire section](/endorctl/commands/container/_print.html)



# container

Use the container command to scan container images.

The `endorctl container scan` command scans container images for vulnerabilities and security risks. It detects and reports known vulnerabilities in operating system packages, programming language packages, and libraries within your container images.

**Note**

Use the `endorctl container scan` command instead of the deprecated `endorctl scan --container` command. See [Container scan commands migration guide](../../../scan-with-endorlabs/scan-containers/container-migration/) for more information.

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

## Options

The following flags are supported for the `endorctl container scan` command:

| Flag | Environment Variable | Type | Description |
| --- | --- | --- | --- |
| `image` | `ENDOR_CONTAINER_SCAN_IMAGE` | string | The container image name and tag to scan, for example, `nginx:latest`. Use this flag in combination with other scan-related parameters. |
| `image-tar` | `ENDOR_CONTAINER_SCAN_IMAGE_TAR` | string | The absolute path to a container image tarball file to scan, for example, `/path/to/image.tar`. Use this flag in combination with other scan-related parameters. |
| `p`, `path` | `ENDOR_CONTAINER_SCAN_REPOSITORY_PATH` | string | The path to a valid git repository to associate the container scan with a Git repository. |
| `project-name` | `ENDOR_CONTAINER_SCAN_PROJECT_NAME` | string | The project name for the container scan when scanning as a standalone project. |
| `as-ref` | `ENDOR_CONTAINER_SCAN_AS_REF` | boolean (default:false) | Scan the container in a persistent context and keep the version. Use with `--project-name` to specify the name of the project. |
| `project-tags` | `ENDOR_CONTAINER_SCAN_PROJECT_TAGS` | string | A list of user-defined tags to add to this project. |

## Feedback

Was this page helpful?

Yes
No

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

Thanks for the feedback. Write to us at support@endor.ai to tell us more.
