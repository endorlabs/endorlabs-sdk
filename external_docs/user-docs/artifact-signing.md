---
url: https://docs.endorlabs.com/artifact-signing/
title: Sign artifacts | Endor Labs Docs
downloaded: 2026-01-29 22:23:58
---

Sign artifacts | Endor Labs Docs



* Type to search...

[Print entire section](/artifact-signing/_print.html)



# Sign artifacts

Learn how to use Endor Labs to sign container images and build artifacts in the CI pipeline.

Endor Labs enhances software supply chain security by providing transparent mechanisms for signing and verifying software artifacts.

* **Integrity of container images and build artifacts:** Using a cryptographic signature ensures that container images and other build artifacts are genuine and crafted by the organization. This adds an extra layer of security to the software supply chain, making sure that only authorized and unaltered items are scheduled for execution.
* **Traces across workflows:** Beyond just verification, the framework offers thorough traceability. Users can trace the roots of container images and build artifacts, navigating through workflows and environments. Complete traceability ensures transparency, enabling organizations to validate the entire lifecycle of their software, from creation to deployment.
* **Certificate validity:** Endor Labs uses a short-lived certificate with a validity period of 5 minutes to ensure that the build artifact has been signed during this time frame. To further guarantee the signing occurred within the valid window, a timestamp is added alongside the certificate and signature, confirming the signing within the specified time frame.

You can sign artifacts using the following methods.

* [Using GitHub Action](#sign-artifacts-using-github-action)
* [Using endorctl CLI](#sign-artifacts-using-endorctl)

## Sign artifacts using GitHub Action

Use the Endor Labs [GitHub Actions](https://github.com/endorlabs/github-action/blob/main/README.md) to sign artifacts.

1. Set up authentication to Endor Labs.
   * (Recommended) If you are using GitHub Action keyless authentication, set an authorization policy in Endor Labs to allow your organization or repository to authenticate. See [Keyless Authentication](../deployment/ci-scans/keyless-authentication/) for more information.
   * Alternatively, authenticate with a GCP service account setup for keyless authentication from GitHub Actions or an Endor Labs API key added as a repository secret.
2. Checkout your code.
3. Install your build toolchain.
4. Build your code.
5. Sign your artifacts with Endor Labs.

### Endor Labs GitHub Action

Use the GitHub Action `endorlabs/github-action/sign@version` to sign your artifacts. Set the following input parameters.

| Options | Description |
| --- | --- |
| `artifact_name` | Name of the artifact. For example, `ghcr.io/org/image@sha256:digest`. |
| `enable_github_action_token` | Fetches build information from the GitHub Action OIDC token. Endor Labs uses this information to build provenance metadata for the signed artifacts. Set to `true` by default. |

See the following example workflows to sign an artifact.

```
- name: Sign artifacts with Endor Labs
  on: [push, workflow_dispatch]
  name: build
  jobs:
  ko-publish:
    name: Release ko artifact
    runs-on: ubuntu-latest
    permissions:
      id-token: write
      packages: write
      contents: read
    steps:
      - uses: actions/setup-go@v4
        with:
          go-version: '1.20.x'
      - uses: actions/checkout@v3
      - uses: ko-build/setup-ko@v0.6
      - run: ko build
      - name: Login to the GitHub Container Registry
        uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.repository_owner }}
          password: ${{ secrets.GITHUB_TOKEN }}
      - name: Publish
        run: KO_DOCKER_REPO=ghcr.io/endorlabs/hello-sign ko publish --bare github.com/endorlabs/hello-sign
      - name: Get Image Digest to Sign
        run: |
          IMAGE_SHA=$(docker inspect ghcr.io/endorlabs/hello-sign:latest | jq -r '.[].Id')
          SIGNING_TARGET="ghcr.io/endorlabs/hello-sign@$IMAGE_SHA"
          echo ARTIFACT="$SIGNING_TARGET" >> $GITHUB_ENV
      - name: Sign with Endor Labs
        uses: endorlabs/github-action/sign@version
        with:
          namespace: "example"
          artifact_name: ${{ env.ARTIFACT }}
```

### Provenance information in signed artifacts

The signed artifacts contain provenance metadata that describe the origin, history, and ownership of an artifact throughout its lifecycle. Including this information in signed artifacts enhances transparency, trustworthiness, and accountability.

The following provenance information is included in the signed artifacts.

| Type | Description | Example |
| --- | --- | --- |
| Build Config Digest | Specific version of the top-level/initiating build instructions (workflow SHA) | 729595ed884ce7600925633e585016a4f855929d |
| Build Config Name | Name of the top-level/initiating build instructions (workflow) | Release |
| Runner Environment | Name of the platform-hosted or self-hosted infrastructure | self-hosted |
| Source Repository | The source repository that the build was based on | `endorlabs/monorepo` |
| Source Repository Digest | Specific version of the source code that the build was based on (commit SHA) | 729595ed884ce7600925633e585016a4f855929d |
| Source Repository Owner | Owner of the source repository that the build was based on | `endorlabs` |
| Source Repository Ref | Source repository ref that the build was based on | `refs/tags/v1.6.133` |
| Certificate OIDC Issuer | Issuer of the OIDC certificate used for verification | * `https://example.com/auth` * `https://token.actions.githubusercontent.com` |
| Certificate Identity | The identity expected in a valid certificate | `repo:org/monorepo:ref:refs/tags/v1.2.3` |

## Sign artifacts using endorctl

Use the `endorctl` CLI to sign an artifact. Ensure you have downloaded the latest `endorctl` binary.

To sign an artifact, run the following command.

```
endorctl artifact sign --name string --source-repository-ref string --certificate-oidc-issuer string
```

Specify the following options with the `endorctl artifact sign` command to include provenance information in your signed artifacts.

| Options | Required | Description |
| --- | --- | --- |
| `--name string` | Mandatory | Name of the artifact. For example, `ghcr.io/org/image@sha256:digest`. |
| `--build-config-digest string` | Optional | Specific version of top-level/initiating build instructions. For example, `workflow sha`. |
| `--build-config-name string` | Optional | Name of top-level/initiating build instructions. For example, `workflow`. |
| `--runner-environment string` | Optional | Name of platform-hosted or self-hosted infrastructure. For example, `self-hosted`. |
| `--source-repository string` | Optional | Source repository that the build was based upon. For example, `org/repo`. |
| `--source-repository-digest string` | Optional | Specific version of the source code that the build was based upon. For example, `commit sha`. |
| `--source-repository-owner string` | Optional | Owner of the source repository that the build was based upon. For example, `my-org`. |
| `--source-repository-ref string` | Mandatory | Source repository ref that the build run was based upon. |
| Certificate OIDC Issuer | Mandatory | Issuer of the OIDC certificate used for verification. For example,  * `https://example.com/auth` * `https://token.actions.githubusercontent.com` |
| Certificate Identity | Optional | The identity expected in a valid certificate. For example, `repo:org/monorepo:ref:refs/tags/v1.2.3`. |

### View the signed artifacts

To view the signed artifacts:

1. Sign in to Endor Labs and select **CI/CD > Artifacts** from the left sidebar.

   You can view the list of signed artifacts with their created date, and last updated date.
2. Use **Type** to filter artifacts by type.
3. Select an artifact to view the artifact digests associated with the artifact including its provenance information.
4. Select an artifact in the row to view **Artifact Digest Details** to view metadata, build configuration, and source configuration details in the right sidebar.

![View artifacts](../images/view_signed_artifacts.png)

### Understand the signing process

When you run the `endorctl artifact sign <image>` command, Endor Labs initiates the following processes:

* **Authentication:** Initiates regular authentication and retrieves a token from the OIDC or workflow provider while using an authentication option such as `--enable-github-action-token` or API keys.
* **Key Generation:** Generates a public and private key using ECDSA-256.
* **Certificate Request:** Sends a certificate request to the private Certificate Authority to obtain a short-lived certificate.
* **Provenance Inclusion:** Incorporates provenance information from the token (if available) or provided with the CLI, adding it as a set of extensions to the certificate using ASN.1 encoding.
* **Image Signing:** Uses the private key to actively sign the image.
* **Certificate Storage:** Stores the certificate containing provenance information along with the signature in the database.
* **Timestamp:** Adds a timestamp of the signing event.

## Verify the signed artifacts

To verify a signed artifact, use the following command:

```
endorctl artifact verify --name <artifact> --certificate-oidc-issuer <issuer>
```

Use the following command-line options with `endorctl artifact verify`:

| Options | Description |
| --- | --- |
| `--name <name>` | Name of the artifact to verify. For example, `ghcr.io/org/image@sha256:digest` |
| `--certificate-oidc-issuer <issuer>` | Issuer of the OIDC certificate used for verification. For example,  * `https://example.com/auth` * `https://token.actions.githubusercontent.com` |

### Understand the verification process

When you run the `endorctl artifact verify --name <artifact> --certificate-oidc-issuer string` command, Endor Labs initiates the following verification processes:

* **Authentication:** Initiates regular authentication and retrieves a token from the OIDC or workflow provider while using an authentication option such as `--enable-github-action-token` or API keys.
* **Signature Retrieval:** Retrieves a signature entry from the database using the artifact name.
  + If the entry is not found, the verification process fails.
* **Certificate Authority Check:** Checks for a trusted Certificate Authority.
* **Image Signature Validation:** Validates the image signature using the public key from the certificate.
* **Timestamp Validation:** Validates that the timestamp in the signature entry is within the certificate’s validity.
* **OIDC Issuer Verification:** Checks whether the issuer provided matches the contents of the certificate.
* **Provenance Verification:** Ensures that any provenance information from the CLI matches the ones in the certificate.

## Revoke the artifact signature

You can revoke a signature of a signed artifact for reasons such as a precautionary measure to safeguard against security risks, to maintain compliance, or to uphold trust and integrity.

To revoke a signature linked to an artifact and prevent its usage, use the following command:

```
endorctl artifact revoke-signature --name <image> --source-repository-ref "ref"
```

Specify the following command-line options for `endorctl artifact revoke-signature`:

| Options | Required | Description |
| --- | --- | --- |
| `--name string` | Mandatory | Name of the artifact whose signature needs to be revoked |
| `--source-repository-ref string` | Mandatory | Reference to the source repository of the artifact. For example, `refs/tags/v1.0.1`. This identifies the specific signature and revokes it. |

Revoking the artifact signature invalidates the corresponding database entry and ensures that any attempts to verify the signature will fail.

## Best practices

* While specifying the artifact name during the signing process, for the container images, adhere to the structure `registry.example.com/repository/image@sha256:digest`.
* The signing process does not support tags. Ensure that you specify a SHA256 digest with the artifact you are signing to represent a cryptographic hash of the image’s content. This ensures a unique digest is created for every minor alteration in the image.

## Feedback

Was this page helpful?

Yes
No

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

Thanks for the feedback. Write to us at support@endor.ai to tell us more.
