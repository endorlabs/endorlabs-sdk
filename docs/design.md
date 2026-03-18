# SDK Design Notes

Non-normative rationale and tradeoffs for SDK behavior.
Normative agreements are defined in `docs/contracts.md`.

## Why contracts are separate

- Keep enforceable behavior in one place for humans and agents.
- Reduce drift by preventing repeated semantics across guides/reference docs.

## DevEx vs maintainability principles

- Prefer ergonomic facade helpers when they are explicit and testable.
- Keep convenience behavior documented as SDK-specific (not assumed API contract).
- Keep operation availability and payload matrices in `docs/reference/`.

## Current design choices to preserve

- Resource-object namespace anchoring for `get/update/delete` to avoid cross-namespace mismatch.
- Flat list kwargs on facades for common workflows.
- Optional auto-derived `update_mask` only for resource-instance update kwargs.

## Placement rules

- `docs/contracts.md`: normative behavior agreements.
- `docs/reference/*`: API/resource inventories and payload references.
- `docs/guides/*`: user workflows and examples.
- `docs/rules-of-engagement/*`: contributor/agent process and implementation checklists.
