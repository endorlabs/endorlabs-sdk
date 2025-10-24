---
url: https://docs.endorlabs.com/scan-with-endorlabs/scan-containers/container-migration/
title: Migrate to new container scan commands | Endor Labs Docs
downloaded: 2025-10-23 23:25:07
---

Migrate to new container scan commands | Endor Labs Docs



* Type to search...
* ---

[Print entire section](/scan-with-endorlabs/scan-containers/container-migration/_print.html)



# Migrate to new container scan commands

Learn how to migrate from deprecated container scan flags to the new `endorctl container scan` command.

With the release of the new `endorctl container scan` commands, the old `endorctl scan` container commands and their related flags will be removed after a three-month deprecation period.

Use the new dedicated command to ensure continued compatibility.

### Mapping of deprecated and new container scan commands

| Old | New |
| --- | --- |
| `endorctl scan --container <image> --path=<project_path>` | `endorctl container scan --image <image> --path=<project_path>` |
| `endorctl scan --container <image> --project-name=<project_name>` | `endorctl container scan --image <image> --project-name=<project_name>` |
| `endorctl scan --container-tar <file>` | `endorctl container scan --image-tar <file>` |
| `endorctl scan --container-as-ref` | `endorctl container scan --as-ref` |

### Examples

* To scan a basic container image:

  + **Old:** `endorctl scan --container nginx:latest --namespace my-namespace`
  + **New:** `endorctl container scan --image nginx:latest --namespace my-namespace`
* To scan a container tar file:

  + **Old:** `endorctl scan --container-tar /path/to/image.tar --namespace my-namespace`
  + **New:** `endorctl container scan --image-tar /path/to/image.tar --namespace my-namespace`
* To scan a container with a project name:

  + **Old:** `endorctl scan --container nginx:latest --project-name my-nginx --namespace my-namespace`
  + **New:** `endorctl container scan --image nginx:latest --project-name my-nginx --namespace my-namespace`
* To scan a container in a reference context:

  + **Old:** `endorctl scan --container nginx:latest --container-as-ref --namespace my-namespace`
  + **New:** `endorctl container scan --image nginx:latest --as-ref --namespace my-namespace`

## Feedback

Was this page helpful?

Yes
No

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

Thanks for the feedback. Write to us at support@endor.ai to tell us more.
