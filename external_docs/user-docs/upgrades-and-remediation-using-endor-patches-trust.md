---
url: https://docs.endorlabs.com/upgrades-and-remediation/using-endor-patches/trust/
title: Patch transparency | Endor Labs Docs
downloaded: 2025-11-20 11:50:01
---

Patch transparency | Endor Labs Docs



* Type to search...
* ---

[Print entire section](/upgrades-and-remediation/using-endor-patches/trust/_print.html)



# Patch transparency

Build trust in your Endor patches.

In security, trust is crucial. Therefore, the patch details of an Endor patch are fully transparent. You can audit the exact code changes, builds, build steps, and logs. The builds are reproducible and hermetic.

## Review patch transparency information

To review patches, build, test and deploy process used to create an Endor patch, use the `AssuredPackageVersion` API.

The commands and logs used to test, deploy and build this package are stored for each version of a package as an attestation.

## Review attestations

To see all information about the patch, build, test and deploy process for this Endor patch use the command:

```
endorctl api get -r AssuredPackageVersion -n oss --name="mvn://com.fasterxml.jackson.core:jackson-databind@2.9.10.3"
```

## Review security attestations

To see the exact changes used for a given security patch, Endor Labs provides a security attestation which shows:

1. Fixed vulnerabilities
2. Exact code changes for each package
3. Exact commits used and if they are upstream commits or commits applied by Endor Labs directly

To see a security attestation use the following command with the name of the package version you’d like to inspect. For this example we’ll use `com.fasterxml.jackson.core:jackson-databind@2.9.10.3`:

```
endorctl api get -r AssuredPackageVersion -n oss --name="mvn://com.fasterxml.jackson.core:jackson-databind@2.9.10.3" --field-mask="spec.security_attestation"
```

## Review build attestations

To see the build steps and build logs for an Endor patch, you can see that patch build attestation.

To see a build attestation use the following command with the name of the package version you’d like to inspect. For this example we’ll use `com.fasterxml.jackson.core:jackson-databind@2.9.10.3`

```
endorctl api get -r AssuredPackageVersion -n oss --name="mvn://com.fasterxml.jackson.core:jackson-databind@2.9.10.3" --field-mask="spec.build_attestation"
```

## Reviewing Test Attestations

To see the test steps and test logs for an Endor patch, you can see that patch test attestation.

To see a deployment attestation use the following command with the name of the package version you’d like to inspect. For this example we’ll use `com.fasterxml.jackson.core:jackson-databind@2.9.10.3`

```
endorctl api get -r AssuredPackageVersion -n oss --name="mvn://com.fasterxml.jackson.core:jackson-databind@2.9.10.3" --field-mask="spec.test_attestation"
```

## Review deploy attestations

To review the deployment steps and logs for an Endor patch, check the patch deployment attestation.

To see a deployment attestation, use the following command with the name of the package version you’d like to inspect. For this example, we’ll use `com.fasterxml.jackson.core:jackson-databind@2.9.10.3`.

```
endorctl api get -r AssuredPackageVersion -n oss --name="mvn://com.fasterxml.jackson.core:jackson-databind@2.9.10.3" --field-mask="spec.deploy_attestation"
```

## Reproducible Build

To download the reproducible build of the patched artifact, with the name of the package version you’d like to inspect. For this example, we’ll use `com.fasterxml.jackson.core:jackson-databind@2.9.10.3`.

```
endorctl api get -r AssuredPackageVersion -n oss --name="mvn://com.fasterxml.jackson.core:jackson-databind@2.9.10.3" --field-mask="spec.reproducible_build_source_code_url"
```

Use the URL to download the source code to reproduce the build. You can find instructions on building the artifact in the README of the downloaded tar.

#### Note

You will need Bazel and Docker installed on your host.

## Feedback

Was this page helpful?

Yes
No

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

Thanks for the feedback. Write to us at support@endor.ai to tell us more.
