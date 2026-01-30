---
url: https://docs.endorlabs.com/deployment/ci-scans/keyless-authentication/github-keyless-auth/
title: Keyless authentication in GitHub | Endor Labs Docs
downloaded: 2026-01-26 10:07:29
---

Keyless authentication in GitHub | Endor Labs Docs



* Type to search...

[Print entire section](/deployment/ci-scans/keyless-authentication/github-keyless-auth/_print.html)



# Keyless authentication in GitHub

Learn how to implement keyless authentication in GitHub.

To enable Keyless Authentication for GitHub Actions, you’ll need to perform the following steps:

1. Ensure you are using the Endor Labs [GitHub Action](https://github.com/endorlabs/github-action.git) in your GitHub workflow.
2. Edit your GitHub Action workflow to add permission settings for the GitHub `id-token` and `contents`.
3. Create an authorization policy for `GitHub Action OIDC`.
4. Test that you can successfully scan a project using `GitHub Action OIDC`.

### Add a GitHub Action OIDC authorization policy

To ensure that the GitHub Action OIDC identity can successfully login to Endor Labs, create an authorization policy in Endor Labs.

To create an authorization policy:

1. Select **Access Control** from the left sidebar.
2. Select **Auth Policy**.
3. Click on **Add Auth Policy**.
4. Select **GitHub Action OIDC** as your identity provider.
5. Select the permission for the GitHub Action. This permission should be `Code Scanner`.
6. For the claim use the key `user` and put in a matching value that maps to the organization of your GitHub repository.

### Configure your GitHub Action workflow

To configure your GitHub Action workflow with GitHub Action OIDC you can use the following example as a baseline.

The important items in this workflow are:

1. The Usage of the Endor Labs GitHub Action.
2. Setting Job level permissions to allow writing to the GitHub `id-token` and reading repository `contents`.

```
name: Example Scan of OWASP Java
on: workflow_dispatch
jobs:
  create_project_owasp:
    permissions:
      id-token: write # This is required for requesting the JWT
      contents: read # This is required to checkout and read your repository code
    runs-on: ubuntu-latest
    steps:
      - name: Checkout Repo
        uses: actions/checkout@v3
        with:
          repository: OWASP-Benchmark/BenchmarkJava
      - name: Setup Java
        uses: actions/setup-java@v3
        with:
          distribution: 'microsoft'
          java-version: '17'
      - name: Compile Package
        run: mvn clean install
      - name: Scan with Endor Labs
        uses: endorlabs/github-action@main # This workflow uses the Endor Labs GitHub action to scan.
        with:
          namespace: 'demo'
          scan_summary_output_type: 'json'
          pr: false
          scan_secrets: true
          scan_dependencies: true
```

Now that you’ve successfully configured your GitHub Action workflow file you can use this workflow file or one of your own designs to run a test scan using Keyless authentication for GitHub Actions.

## Feedback

Was this page helpful?

Yes
No

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

Thanks for the feedback. Write to us at support@endor.ai to tell us more.
