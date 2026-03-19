# OIDC Migration Runbook (Tenant + CI)

This runbook documents how this repository uses GitHub OIDC keyless authentication
for Endor Labs CLI/action workflows, while keeping API-key auth for SDK integration
tests until the SDK harness supports token-mode auth.

## Goals

- Use short-lived GitHub OIDC identities for Endor action and `endorctl` CI jobs.
- Keep SDK integration tests stable on API key auth.
- Fail early with clear errors when auth policy claims, role, or scope drift.

## Tenant prerequisites

1. Ensure the root tenant namespace exists (for this repo: `endor-solutions-tgowan`).
2. Create a GitHub Action OIDC authorization policy with:
   - **Name**: `github-oidc-code-scanner`
   - **Claims**: include both `github-action` and `user=<github-org>` (for this repo: `user=Endor-Solutions-Architecture`)
   - **Role**: `SYSTEM_ROLE_CODE_SCANNER`
   - **Target namespace**: root tenant namespace
   - **Propagate**: `true`
3. Keep repository `vars.ENDOR_NAMESPACE` aligned with the target namespace.

## Temporary policy bootstrap script

Use the temporary SDK script to create/verify the policy idempotently:

```bash
uv run --env-file .env python scripts/ensure_github_oidc_policy.py
uv run --env-file .env python scripts/ensure_github_oidc_policy.py --apply
uv run --env-file .env python scripts/ensure_github_oidc_policy.py --verify-only
```

Notes:
- Default tenant/namespace: `endor-solutions-tgowan`
- Default claim: `user=Endor-Solutions-Architecture`
- Script no-ops when a matching policy already exists.

## CI prerequisites

- Grant `id-token: write` permissions to OIDC-enabled jobs.
- Keep `contents: read` (and other minimum permissions) on those jobs.
- Pin Endor GitHub Actions to immutable commit SHA.
  - Current pin in this repo: `ea13ac38613bbf08ee75ec21ddec172e648976b7`
  - Release tag: `v1.1.11`

## What is OIDC now

- `continuous-integration-and-quality-gates.yml`
  - `ai-security-review` uses OIDC via `endorlabs/github-action`.
  - `oidc-smoke` validates OIDC auth with `endorctl api list`.
- `nightly-self-validation-scorecard-and-replay.yml`
  - Adds OIDC setup + policy validation + smoke command.
  - Main SDK scripts still use API-key credentials for now.
- `release-validation-and-publish.yml`
  - Uses OIDC setup and policy validation.
  - Signs and verifies release artifacts with
    `endorlabs/github-action/sign` and `endorlabs/github-action/verify`.

## Current constraints (intentional)

- SDK integration tests remain API-key based today because the test harness requires:
  - `ENDOR_API_CREDENTIALS_KEY`
  - `ENDOR_API_CREDENTIALS_SECRET`
  - `APIClient(auth_method="api-key")`
- Do not remove API-key secrets until integration tests gain supported token/OIDC mode.

## Troubleshooting matrix

- **401/403 on OIDC jobs**
  - Confirm job has `permissions.id-token: write`.
  - Confirm policy claims include both `github-action` and `user=${{ github.repository_owner }}`.
  - Confirm policy target namespace matches `vars.ENDOR_NAMESPACE`.
- **Policy validation step fails**
  - Re-run `scripts/ensure_github_oidc_policy.py --verify-only` locally.
  - Re-apply with `--apply` if policy drifted.
- **Release sign/verify fails**
  - Verify artifact name includes a digest (`...@sha256:<digest>`).
  - Verify `certificate_oidc_issuer` is `https://token.actions.githubusercontent.com`.
- **SDK integration tests fail with auth errors**
  - This path still requires API key/secret and is independent of OIDC setup.

## Safe rollout sequence

1. Dry-run and apply policy bootstrap script.
2. Confirm policy verification succeeds in CI.
3. Confirm OIDC smoke check is green on PR and push runs.
4. Confirm release sign/verify path is green on a release candidate tag.
5. After several stable runs, remove API keys only from jobs that no longer need them.
