## Summary

<!-- One paragraph: what changed and why -->

## Changelog intake

<!-- Agents/maintainers: see agent-knowledge/rules/endor-changelog.md -->

- [ ] **Not user-facing** — no edit to `docs/changelog.md` **Unreleased**
- [ ] **User-facing** — add one bullet under **Added**, **Changed**, or **Breaking** in [`docs/changelog.md`](../docs/changelog.md) **Unreleased** (same PR when possible)

| Field | Value |
|-------|-------|
| **Section** | `Added` \| `Changed` \| `Breaking` \| `none` |
| **Summary** | <!-- one imperative sentence; no ticket IDs --> |
| **Audience** | `sdk-user` \| `agent-skill` \| `both` |
| **Migration** | <!-- Breaking only: old → new, or "see changelog table" --> |

**PR title hint (optional):** `feat(cli): …` · `fix(sdk): …` · `chore(model-sync): …` (usually `none` for changelog)

## Test plan

- [ ] <!-- e.g. uv run pytest … -->
