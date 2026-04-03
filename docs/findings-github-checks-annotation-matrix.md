# Finding attributes vs GitHub Checks annotations (matrix)

This note compares **what the GitHub REST Checks API expects** for per-line annotations with **what Endor Labs exposes on `Finding` resources** and what this repo’s helpers actually use. It is a **manual** crosswalk (OpenAPI / GitHub docs / in-tree scripts), not a generated report from a script.

## GitHub side (official)

Annotations are submitted on a check run under `output.annotations` when you [create](https://docs.github.com/en/rest/checks/runs?apiVersion=2022-11-28#create-a-check-run) or [update](https://docs.github.com/en/rest/checks/runs?apiVersion=2022-11-28#update-a-check-run) a check run. The update endpoint documents each annotation field:

| Field | Required | Constraints (summary) |
|--------|-----------|------------------------|
| `path` | Yes | Repo-relative file path. |
| `start_line` | Yes | Line numbers are 1-based. |
| `end_line` | Yes | For a single line, equals `start_line`. |
| `annotation_level` | Yes | One of `notice`, `warning`, `failure`. |
| `message` | Yes | Short description; large max size (64 KB). |
| `title` | No | Max 255 characters. |
| `raw_details` | No | Optional extra detail (64 KB). |
| `start_column` / `end_column` | No | Only when `start_line` and `end_line` are the **same** line. Omitting them is always valid. |

**Limits:** Up to **50 annotations per request**; further annotations require additional update calls (appended). See the same [Update a check run](https://docs.github.com/en/rest/checks/runs?apiVersion=2022-11-28#update-a-check-run) section.

**Heuristic lines (e.g. “use line 1” or “1 through end of file”):** GitHub’s schema only requires positive line numbers and `end_line` ≥ `start_line`. The API will usually accept a placeholder such as `start_line` = `end_line` = `1` if you have a `path` but no real line. That does **not** mean the UI points at the real issue—it marks an arbitrary span. Spanning to “end of file” needs a line count (e.g. fetch file at the checked-out ref), adds cost and failure modes, and is still a guess if the finding is not file-local. Product choice: omit annotations and keep detail in check `summary` / `text`, vs. accept misleading markers.

**UI:** Annotations are intended to show in the PR experience; details of how they appear on the diff are described under GitHub’s [About status checks](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/collaborating-on-repositories-with-code-quality-features/about-status-checks) (linked from the REST docs).

## Endor side (API model)

`Finding` is defined in the platform OpenAPI (`v1Finding` / `v1FindingSpec` / `v1FindingMetadata` in [`.endorlabs-context/openapiv2.swagger.json`](../.endorlabs-context/openapiv2.swagger.json)). Findings carry at least:

- **`spec`:** `level`, `summary`, `explanation`, `remediation`, `finding_metadata`, `dependency_file_paths`, `finding_categories`, `method`, etc.
- **`meta`:** includes `name`, `parent_uuid`, `parent_kind` (parent may be `RepositoryVersion`, `PackageVersion`, etc., per API descriptions).
- **`finding_metadata`:** includes optional `security_review_data` (with `code_snippet` per `v1SecurityReviewFindingData` → `PullRequestSecurityReviewResultInfoCodeSnippet`: required `file` and `line`; optional `line_end`, `snippet`, … — **no column fields in the typed schema**), **`custom`** (OpenAPI: untyped “custom finding metadata”; live payloads from tools like Semgrep/OpenGrep often include `start`/`end` with line and sometimes column), vulnerability/package metadata, etc.

Whether a given finding is **line-anchored** is not a single boolean on the resource; it depends on category (SCA vs SAST vs PR security review) and what the scanner populated in **`spec` / `finding_metadata` in real API responses**.

## Matrix 1 — GitHub annotation field → Endor / local mapping

| GitHub field | Endor / automation source (this repo) | Typical coverage |
|--------------|----------------------------------------|------------------|
| `path` | [`endor_scan_findings.extract_location`](../.github/scripts/endor_scan_findings.py): `security_review_data.code_snippet`, `finding_metadata` path fields, `custom` (Semgrep-style), `dependency_file_paths`, `location` string, blob URLs in `summary` / `explanation` / etc. | **Variable:** path often available for SCA/policy-style rows via `dependency_file_paths` or text; must be a valid repo-relative path for GitHub. |
| `start_line` / `end_line` | Same `extract_location` logic; `end_line` from snippet or inferred. | **Often the gap:** many findings have no reliable line; GitHub **requires** both lines. Without a line, you cannot emit a valid annotation (only check `summary` / `text`). |
| `annotation_level` | [`post_github_check_run`](../.github/scripts/post_github_check_run.py) (`_finding_annotation_level`): maps `spec.level` to `failure` / `warning` / `notice`. | **Good** when `spec.level` is set. |
| `message` | Built from UUID, level, and first non-empty of `summary` / `description` / `explanation`. | **Good** for human-readable text. |
| `title` | `meta.name`, `spec.rule_name`, or UUID. | **Good** (truncate to 255 for GitHub). |
| `raw_details` | **API:** always optional for GitHub. **Endor:** long text is available on `spec` (`remediation`, `explanation`, etc.). | **Possible:** map those fields into `raw_details` (truncate to API limits). **Code:** extend annotation dict assembly in [`post_github_check_run.py`](../.github/scripts/post_github_check_run.py). |
| `start_column` / `end_column` | **GitHub:** optional. **Endor OpenAPI:** not on `PullRequestSecurityReviewResultInfoCodeSnippet`; **`custom`** may carry tool-specific columns in live findings (e.g. Semgrep-style `start.col`). | **Possible** when columns exist under `finding_metadata.custom` (or future typed fields). **Code:** extend [`endor_scan_findings.py`](../.github/scripts/endor_scan_findings.py) (`_location_from_custom` / `extract_location` return shape) and pass columns from [`build_annotations`](../.github/scripts/post_github_check_run.py) only when `start_line == end_line`. |

**Practical conclusion:** You can almost always attach **check run output** (title, summary, conclusion). **Per-line annotations** need a repo-relative **`path`** plus **`start_line` / `end_line`** (GitHub-required). That pair is **possible** when Endor (or parsed text) supplies them; otherwise you either **skip** the annotation (current behavior) or **heuristic-anchor** (API-allowed but can mislead—see above).

## Matrix 2 — Endor signal → GitHub Checks use

| Endor / derived signal | Role for Checks |
|------------------------|-----------------|
| `spec.level` | Severity → `annotation_level`. |
| `meta.name`, `spec.rule_name` | `title`. |
| `spec.summary`, `explanation`, `remediation`, `description` | `message` / optional `raw_details`. |
| `spec.finding_metadata.security_review_data.code_snippet` (`file`, `line`, …) | Primary source for PR security review–style **path + line** (matches OpenAPI `PullRequestSecurityReviewResultInfoCodeSnippet`). |
| `spec.finding_metadata.custom` | SAST/tooling path + line when structured like Semgrep/OpenGrep. |
| `spec.dependency_file_paths` | Often supplies **path** for dependency/policy findings; line usually needs `custom` or text heuristics. |
| `spec.finding_metadata.location` (`path:line`) | Path + line when present. |
| GitHub `blob/.../path#Ln` in spec text | Parsed in-repo for path + line when present in `summary` / `explanation` / etc. |

## Is it possible? What to change in code?

| Goal | Possible? | Code / behavior |
|------|-----------|-----------------|
| Post check run with summary + conclusion for all findings | **Yes** | Already: findings feed check body; annotations are the optional part. |
| Post **accurate** line annotations | **Yes when** live finding has path + line (snippet, `custom`, `location`, blob URL in text, heuristics on `dependency_file_paths` + text). | Already covered by [`extract_location`](../.github/scripts/endor_scan_findings.py) + [`build_annotations`](../.github/scripts/post_github_check_run.py). |
| Post annotations for “path only” findings (e.g. lockfile path, no line in API) | **API:** yes if you invent lines. **Accuracy:** no unless you fetch content or accept a dummy line. | Optional: add fallback `start_line`/`end_line` (e.g. `1`) or integrate git/blob line-count lookup; document the tradeoff. |
| Add `raw_details` | **Yes** | Add fields to the dict built in `build_annotations` from `spec`. |
| Add column range | **Yes if** tool payload includes columns under `custom` (not guaranteed by spec). | Plumb optional `start_column`/`end_column` from `extract_location` → `build_annotations` with GitHub’s same-line rule. |

## UI vs API scoping (conceptual)

Endor’s web UI can show “findings for a version” using **product filters** that may not equal a single `Finding.list(meta.parent_uuid == <RepositoryVersion uuid>)` query. For automation, assume you must align with **documented list filters** and parent kinds (`RepositoryVersion` vs `PackageVersion`) rather than assuming the URL segment alone is the same as `meta.parent_uuid` on every row the UI shows.

## References

- [Create a check run (REST)](https://docs.github.com/en/rest/checks/runs?apiVersion=2022-11-28#create-a-check-run)
- [Update a check run (REST) — `output.annotations`](https://docs.github.com/en/rest/checks/runs?apiVersion=2022-11-28#update-a-check-run)
- [About status checks](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/collaborating-on-repositories-with-code-quality-features/about-status-checks)
- Local: [`.github/scripts/endor_scan_findings.py`](../.github/scripts/endor_scan_findings.py), [`.github/scripts/post_github_check_run.py`](../.github/scripts/post_github_check_run.py), [`.github/scripts/smoke_github_check_annotation.py`](../.github/scripts/smoke_github_check_annotation.py) (minimal Checks POST for validation)
- Guide: [PR comments and GitHub Checks — validating annotations](guides/pr-comment-config-and-parallel-comments.md#validating-check-annotations-end-to-end)
- Local: [`.endorlabs-context/openapiv2.swagger.json`](../.endorlabs-context/openapiv2.swagger.json) (`v1Finding`, `v1FindingSpec`, `v1FindingMetadata`, `v1SecurityReviewFindingData`)
