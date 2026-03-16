# Self-Validation Scorecard and Replay

Run the SDK against real tenant data and emit deterministic evidence artifacts that
support demos, nightlies, and customer-facing posture reviews.

## What this workflow produces

For each repository:

- Session context artifacts (`project-summary.md`, findings/policies/versions summaries)
- Dependency and call graph snapshot bundle
- `self_validation_scorecard.json` with normalized risk/reliability/dependency/policy metrics

Default output root: `.endorlabs-context/self-validation/`.

## Local run

Linux/macOS:

```bash
uv run python scripts/self_validation_scorecard.py \
  --repository-url "https://github.com/Endor-Solutions-Architecture/endorlabs-sdk.git" \
  --tenant "$ENDOR_NAMESPACE" \
  --output-dir ".endorlabs-context/self-validation" \
  --deterministic
```

PowerShell:

```powershell
uv run python scripts/self_validation_scorecard.py `
  --repository-url "https://github.com/Endor-Solutions-Architecture/endorlabs-sdk.git" `
  --tenant "$env:ENDOR_NAMESPACE" `
  --output-dir ".endorlabs-context/self-validation" `
  --deterministic
```

## Determinism contract

When `--deterministic` is set:

- Summary timestamps are pinned to `1970-01-01T00:00:00Z`
- Findings and dependency metadata are written in stable sorted order
- Scorecard JSON is emitted with sorted keys

This allows straightforward diffing between runs.

## Nightly workflow

Workflow: `.github/workflows/nightly-self-validation-scorecard-and-replay.yml`

Triggers:

- `schedule` (nightly)
- `workflow_dispatch` (manual)
- `repository_dispatch` (remote automation)

Manual dispatch inputs:

- `mode`: `smoke` or `full`
- `repository_url`: target repository URL
- `deterministic`: enable stable artifacts
- `strict_threat_claims`: enforce threat-model claim verification when a threat model is present

Artifacts are uploaded as `self-validation-artifacts-*`.

## Engineering maturity mapping

- **Bronze**: nightly `smoke` + deterministic scorecard artifact retention
- **Silver**: remote dispatch + trend diffs + full mode hygiene checks
- **Gold**: strict claim verification + policy/release gates from scorecard thresholds
