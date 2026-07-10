# Unit tests

Maintainer guidance for writing and reviewing unit (and related) tests:

- Canonical rule: [agent-knowledge/rules/endor-unit-tests.md](../../agent-knowledge/rules/endor-unit-tests.md)
- Cursor: [`.cursor/rules/endor-unit-tests.mdc`](../../.cursor/rules/endor-unit-tests.mdc)

Not shipped in the wheel. Covers YAGNI (behavior vs smoke), contract-vs-copy
asserts, domain buckets, runtime hygiene (no accidental OAuth/server sleeps),
**defense-in-depth pre-commit guards** (blocked paths, portable examples /
PII / `-n` flags, change-aware `run-selected-tests`, ship-artifact drift),
and the PR checklist.

For live API resource list/get/create order and pagination profiles, see
[integration-resource-tests.md](integration-resource-tests.md).
