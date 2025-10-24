---
url: https://docs.endorlabs.com/endorctl/commands/sign-artifacts/
title: artifact sign | Endor Labs Docs
downloaded: 2025-10-23 23:24:40
---

artifact sign | Endor Labs Docs



* Type to search...
* ---

[Print entire section](/endorctl/commands/sign-artifacts/_print.html)



# artifact sign

Use the `artifact sign` command to sign container images and build artifacts in the CI pipeline.

Use the `artifact [ sign \| verify ]` command to sign and verify container images and other build artifacts.

## Usage

To sign an artifact, use the following command.

```
endorctl artifact sign --name <artifact> --source-repository-ref <ref> --certificate-oidc-issuer <issuer>
```

To verify a signed artifact, use the following command.

```
endorctl verify --name <artifact> --certificate-oidc-issuer <issuer>`
```

To revoke a signature, use the following command.

```
endorctl artifact revoke-signature --name <artifact> --source-repository-ref <ref>
```

## Options

You can use the following flags and environment variables:

For `endorctl artifact sign`

| Flag | Environment Variable | Type | Description |
| --- | --- | --- | --- |
| `--name string` | `ENDOR_ARTIFACT_NAME` | string | Name of the artifact. For example, `ghcr.io/org/image@sha256:digest`. |
| `--build-config-digest string` | `ENDOR_ARTIFACT_BUILD_CONFIG_DIGEST` | string | Specific version of top-level/initiating build instructions. For example, `workflow sha`. |
| `--build-config-name` | `ENDOR_ARTIFACT_BUILD_CONFIG_NAME` | string | Name of top-level/initiating build instructions. For example, `workflow`. |
| `--certificate-oidc-issuer` | `ENDOR_ARTIFACT_CERTIFICATE_OIDC_ISSUER` | string | Name of the OIDC issuer present in a valid certificate. |
| `--certificate-identity` | `ENDOR_ARTIFACT_CERTIFICATE_IDENTITY` | string | Name of the identity present in a valid certificate. |
| `--runner-environment string` | `ENDOR_ARTIFACT_RUNNER_ENVIRONMENT` | string | Name of platform-hosted or self-hosted infrastructure. For example, `self-hosted`. |
| `--source-repository string` | `ENDOR_ARTIFACT_SOURCE_REPOSITORY` | string | Source repository that the build was based upon. For example, `org/repo`. |
| `--source-repository-digest string` | `ENDOR_ARTIFACT_SOURCE_REPOSITORY_DIGEST` | string | Specific version of the source code that the build was based upon. For example, `commit sha`. |
| `--source-repository-owner string` | `ENDOR_ARTIFACT_SOURCE_REPOSITORY_OWNER` | string | Owner of the source repository that the build was based upon. For example, `my-org`. |
| `--source-repository-ref string` (mandatory) | `ENDOR_ARTIFACT_SOURCE_REPOSITORY_REF` | string | Source repository ref that the build run was based upon. |

For `endorctl artifact verify`

| Flag | Environment Variable | Type | Description |
| --- | --- | --- | --- |
| `--name <name>` | `ENDOR_ARTIFACT_NAME` | string | The name of the artifact to verify. |
| `--certificate-oidc-issuer <issuer>` | `ENDOR_ARTIFACT_CERTIFICATE_OIDC_ISSUER` | string | The issuer of the OIDC certificate used for verification. |

For `endorctl artifact [revoke-signature]`

| Flag | Environment Variable | Type | Description |
| --- | --- | --- | --- |
| `--name string` | `ENDOR_ARTIFACT_NAME` | string | The name of the artifact whose signature needs to be revoked. |
| `--source-repository-ref string` (mandatory) | `ENDOR_ARTIFACT_SOURCE_REPOSITORY_REF` | string | Reference to the source repository of the artifact. |

## Feedback

Was this page helpful?

Yes
No

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

Thanks for the feedback. Write to us at support@endor.ai to tell us more.
