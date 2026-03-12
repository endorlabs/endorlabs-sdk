# Stainless-First Feasibility (Prototype)

This document evaluates a Stainless-first path for keeping SDK surfaces aligned
to the OpenAPI contract while preserving the existing transport/auth runtime.

## Target Outcome

Use generated, spec-synced resource models and thin operation bindings for
`client.<resource>.<operation>()`, while retaining:

- `APIClient` for auth, retries, logging, and HTTP behavior
- current demo/workflow UX on top of generated or adapter surfaces

## Current Inputs and Constraints

- Primary API contract source:
  `.endorlabs-context/openapiv2.swagger.json`
- Existing generation assets:
  `scripts/generate_client_stub.py`,
  `scripts/generate_reference_docs.py`,
  `.github/scripts/model_consistency.py`
- Current runtime architecture:
  registry-driven facades over `BaseResourceOperations`

## Stainless Fit Assessment

Stainless is a good fit for:

- generating model classes and endpoint bindings directly from OpenAPI
- reducing manual drift in high-churn resources
- producing predictable, machine-updated SDK surfaces

Integration constraints for this repo:

- current `Client` facade methods include convenience behaviors (`lookup`,
  identity kwarg filter mapping, tag helpers) that are beyond strict OpenAPI
  parity and would need an adapter layer
- path/parameter naming inconsistencies in the spec (for example, some update
  endpoints use `object.tenant_meta.namespace`) require normalization rules
- release quality gate must verify generated outputs are committed

## Proposed Prototype Integration

1. Keep `APIClient` as transport/session layer.
2. Add generated thin-slice resources for vulnerability and malware domains.
3. Expose generated resources through the existing registry/facade shape first
   to avoid broad breaking changes.
4. Treat current facade UX as an adapter layer, not the source of truth.

## Fallback Strategy

If Stainless cannot be integrated quickly in CI:

- continue with in-repo spec-driven generation extensions using current scripts
- enforce parity by expanding model-consistency and OpenAPI parity checks
- keep generator interfaces adapter-compatible so Stainless can replace the
  backend generator later without changing SDK consumer APIs

## Decision for This Prototype

- Primary direction: Stainless-first architecture and integration path
- Implementation path this cycle: in-repo thin-slice compatible with later
  Stainless replacement
