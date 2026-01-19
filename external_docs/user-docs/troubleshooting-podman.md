---
url: https://docs.endorlabs.com/troubleshooting/podman/
title: Scanning Podman built container images | Endor Labs Docs
downloaded: 2026-01-16 09:49:59
---

Scanning Podman built container images | Endor Labs Docs



* Type to search...

# Scanning Podman built container images

Troubleshoot errors while scanning container images built using Podman

To successfully run endorctl scans on a container image built using Podman, use the following instructions:

1. Build the image using the following command. This command builds a container image and tags it with the label `test:latest`.

   ```
      podman build -t test:latest
   ```
2. After building the image, confirm the target registry by running the following command. Podman automatically adds `localhost` as the target registry for this image.

   ```
      podman image ls
   ```
3. Before scanning the image with endorctl, sign in to the target registry where the image is stored.
4. Check if there is a registry running at `localhost`.
5. If a registry is not running at `localhost`, then you must re-tag the image to a reachable registry, using the following command. Replace `<reachable-registry>` with the actual URL of an accessible registry.

   ```
      podman tag test:latest <reachable-registry>/test:latest
   ```
6. Sign in to the reachable registry using any container runtime. Now you can run the `endorctl` scan. Targeting a reachable registry lets you locate the image manifest and download all required layer blobs for vulnerability analysis.

## Feedback

Was this page helpful?

Yes
No

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

Thanks for the feedback. Write to us at support@endor.ai to tell us more.
