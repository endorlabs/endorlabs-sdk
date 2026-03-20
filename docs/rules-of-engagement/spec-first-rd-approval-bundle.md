# Spec-First Prototype: R&D Approval Bundle

This bundle summarizes what changed in the prototype branch, what remains
deferred, and how to make a go/no-go decision for broader rollout.

## Change Summary

Implemented in prototype:

- Added first-class OSS resources:
  - `client.vulnerability` (`list`, `get`)
  - `client.malware` (`list`, `get`)
- Added first-class OSS query resources:
  - `client.query_vulnerability` (`create`)
  - `client.query_malware` (`create`)
- Updated generated SDK surfaces:
  - `src/endorlabs/client_surface.pyi`
  - `docs/generated-reference/resources.md`
  - `docs/generated-reference/create-update-payloads.md`
  - `docs/generated-reference/api-surfaces.md`
- Strengthened release alignment:
  - `.github/workflows/release-tag-publish.yml` now verifies generated stubs/docs are
    up to date before packaging.

Preserved (explicitly unchanged by design):

- `src/endorlabs/api_client.py` auth/transport/session behavior
- `src/endorlabs/client_surface.py` entrypoint and facade attachment model
- `src/endorlabs/_demo/demo_cli.py` runbook/demo UX

Deferred:

- full cross-resource facade rewrite for strict 1:1 operation dispatch
- full generated-model replacement across all resources
- removal of convenience facade methods currently used by workflows/demos

## Decision Log

1. **Spec-first direction accepted for prototype.**  
   We treated OpenAPI as the contract source and added resources directly tied
   to dedicated API endpoints (`vulnerabilities`, `malware`, `queries/*`).

2. **Thin slice over big-bang refactor.**  
   We implemented two domains end-to-end to validate approach and integration
   points before broad migration.

3. **Adapter continuity prioritized.**  
   Existing auth, client, and demo flows were preserved to avoid regressions
   while proving spec-first additions.

4. **Stainless-first architecture, adapter-compatible implementation.**  
   Feasibility notes are captured in
   `spec-first-stainless-feasibility.md`; current prototype remains compatible
   with a future Stainless-backed generator integration.

## Risk Assessment

Primary risks:

- **Spec inconsistency risk:** some endpoints use different namespace path
  placeholders in OpenAPI (for example `tenant_meta.namespace` vs
  `object.tenant_meta.namespace`), which requires normalization in generators.
- **Query payload shape risk:** query endpoints can validate package version
  naming formats strictly, which may vary by environment/data source.
- **Dual-surface drift risk:** generated surfaces and hand-maintained adapter
  behavior can diverge if generation checks are not enforced in all gates.

Mitigations in prototype:

- release workflow now fails if generated stub/reference docs are stale
- integration tests added for list/get and query create behavior
- parity/docs workflow documentation updated for release alignment expectations

## Go / No-Go Criteria

Go for expansion if all are true:

1. R&D accepts Stainless-first target architecture and fallback path.
2. Prototype resource surfaces (`vulnerability`, `malware`, query resources)
   are stable in CI and target integration environments.
3. Release gates continue passing with generated artifact checks.
4. No regression reported in auth/session and demo/runbook behavior.

No-go (hold) if any are true:

1. Generator path cannot normalize key OpenAPI inconsistencies safely.
2. Query endpoint contracts remain too unstable to support typed generation.
3. Release parity checks cause unresolved workflow instability.

## Recommended Next Increment

1. Expand spec-first slice to the next highest-impact resource group.
2. Introduce a formal generated-vs-adapter contract test set.
3. Pilot Stainless (or equivalent generator) on a non-critical subset while
   preserving the current adapter facade for consumers.
