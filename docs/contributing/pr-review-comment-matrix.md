# Finding attributes vs GitHub pull request review comments (matrix)

Manual crosswalk: **what GitHub’s REST API expects** for review comments created via [Create a review for a pull request](https://docs.github.com/en/rest/pulls/reviews#create-a-review-for-a-pull-request) versus **what Endor exposes on `Finding`**. Not generated from code. (In-repo posting scripts were removed from CI; this matrix remains a reference for custom integrations.)

## GitHub side (official)

Each element of `comments` in the create-review payload is a [pull request review comment](https://docs.github.com/en/rest/pulls/comments) object. Commonly used fields in this repo:

| Field | Required | Notes (summary) |
|--------|-----------|------------------|
| `path` | Yes | File path relative to repo root; must appear in the PR diff. |
| `body` | Yes | Markdown (includes dedupe marker + Endor metadata in our script). |
| `line` | Yes* | Line on the chosen `side` of the diff; *multi-line uses `start_line` / `line` pair per API rules. |
| `side` | Yes | This repo uses **`RIGHT`** (head side of the PR). |
| `start_line`, `start_side` | No | Set when `line_end` from metadata spans multiple lines on the same side. |
| `commit_id` | On review | Set at review level (`commit_id` on the parent review), not per comment in our batching. |

GitHub only accepts comments on lines that exist in the **unified diff** for the PR. A finding with a valid file+line in the tree still produces **no** review comment if that line is not part of a **RIGHT-side** hunk for this PR.

## Endor side (API model)

`Finding` is defined in the platform OpenAPI (`v1Finding` / `v1FindingSpec` / `v1FindingMetadata` in [`.endorlabs-context/platform/openapi/openapiv2.swagger.json`](../../.endorlabs-context/platform/openapi/openapiv2.swagger.json)). Line anchoring depends on category and what the scanner populated; see `extract_location` sources below.

## Matrix — review comment field → source

| GitHub field | Source in this repo | Typical coverage |
|--------------|---------------------|------------------|
| `path` | `Finding` location extraction (file path hints in metadata / dependency paths) → must match a PR-changed file | **Variable:** must match a PR-changed file for a comment to be posted. |
| `line` / `start_line` / `side` | Line from metadata; GitHub requires `side: RIGHT` on unified-diff hunks | **Often the gap:** no comment if line is not in a RIGHT-side hunk. |
| `body` | Markdown from level, category, summary, blob link, optional snippet | **Good** when `spec` fields are populated. |

## Matrix — Endor signal → use in review comments

| Endor / derived signal | Role |
|------------------------|------|
| `spec.level`, `spec.category`, `spec.summary` / `explanation` | Shown in comment markdown body. |
| `meta.name`, `uuid` | Identity and dedupe marker. |
| `spec.finding_metadata.security_review_data.code_snippet` | Primary path + line for PR security review–style findings (OpenAPI `PullRequestSecurityReviewResultInfoCodeSnippet`). |
| `spec.finding_metadata.custom` | SAST-style `path` + `start.line` / `end.line` when structured like Semgrep/OpenGrep. |
| `spec.dependency_file_paths` | Path hints; line often from `custom` or summary heuristics. |
| `spec.finding_metadata.location` (`path:line`) | Path + line when present. |
| GitHub `blob/.../path#Ln` in spec text | Parsed for path + line when present. |

## UI vs API scoping (conceptual)

Endor’s web UI may filter findings differently than `Finding.list` / `Finding.get` for a single `RepositoryVersion`. Automation should follow **documented list filters** and parent kinds when matching scan results to a PR.

## References

- [Create a review for a pull request (REST)](https://docs.github.com/en/rest/pulls/reviews#create-a-review-for-a-pull-request)
- [Pull request review comments](https://docs.github.com/en/rest/pulls/comments)
- Guide: [PR review comments from Endor findings](pr-review-comments.md)
- Local OpenAPI: [`.endorlabs-context/platform/openapi/openapiv2.swagger.json`](../../.endorlabs-context/platform/openapi/openapiv2.swagger.json) (`v1Finding`, `v1FindingSpec`, `v1FindingMetadata`)
