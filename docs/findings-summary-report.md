# Endor Scan Findings Summary Report

**Note:** `sync_external_docs.py` was removed from this repo; any finding referencing it is obsolete.

**Source**: GitHub Actions CI run (endorctl scan), retrieved via `gh run view` and log parsing.  
**Run**: Latest CI workflow run (e.g. run id from `gh run list --workflow=ci.yml --limit 1`).  
**Namespace**: `endor-solutions-tgowan.tgowan-endor`  
**Repository**: Endor-Solutions-Architecture/endor-cockpit

---

## Summary counts (from pipeline)

| Severity | Count |
|----------|-------|
| Critical | 0 |
| High     | 6 |
| Medium   | 6 |
| Low      | 3 |
| Dismissed | 0 |
| **Total** | **15** |

**Policy violations (3 WARN, non-blocking)**  
- Vulnerabilities  
- Secrets  
- In-house Python SAST Rules  

---

## Findings by category

### 1. Secrets (Medium) – **Snoozed / use mocked values**

| ID     | Description | File | Line |
|--------|-------------|------|------|
| #41f3fb | Potential secret leak: Endorlabs API Credentials | `src/endor_cockpit/resources/authorization_policy.py` | 140 |

**Triage**: Snoozed. Use mocked/placeholder values in docstrings (e.g. `<api-key>` or explicit “example/mocked” text) so the finding stays justified and future scans do not re-flag.

---

### 2. SAST – Python path traversal (High)

All are **Python Path Traversal (Enhanced)**; remediation: validate/sanitize inputs, use `os.path.normpath()` / `os.path.abspath()`, ensure resolved path stays under a base directory.

| ID     | File |
|--------|------|
| #8b5ac8  | `scripts/validate_environment.py` |
| #17ba4d  | `.github/scripts/sync_external_docs.py` |
| #194616  | `scripts/traverse_findings_estate.py` |
| #15a35c  | `scripts/setup_environment.py` |

**Triage (TP/FP assessment)**:

| File | Verdict | Reason |
|------|---------|--------|
| **.github/scripts/sync_external_docs.py** | **True positive** | `--openapi-output` and `--user-docs-output` are CLI arguments; their values are used directly as `Path(...)` and in `open()` / `write_text()`. A caller can pass e.g. `--openapi-output ../../../etc/passwd` or `--user-docs-output /tmp/escape` and write outside the intended directory. Paths should be resolved and confined to a base directory (e.g. repo root). |
| **scripts/setup_environment.py** | **False positive** | Paths are **hardcoded literals**: `Path(".env")` and `Path("env.example")`. No user input, env vars, or config affect them. The scanner is flagging the pattern `open(path)` without proving the path is user-controlled. |
| **scripts/traverse_findings_estate.py** | **False positive** | Path is derived from `Path(__file__).resolve().parent.parent` and literal `".env"`. Only script location and a fixed filename; no user input. |
| **scripts/validate_environment.py** | **False positive** | `save_results(output_path=...)` has a default `".workspace/validation.log"`; `main()` calls `save_results()` with no args, so only the default is used. No CLI or other caller passes user-controlled `output_path`. The pattern (parameter used in `open()`) is theoretically risky if the API were ever used with untrusted input; as written, no such input reaches it. |

**Conclusion**: Only **sync_external_docs.py** is a genuine path-traversal risk (user-controlled CLI paths). The other three are **false positives** for current code; fixing sync_external_docs.py (resolve + confine to base dir) is the one change that meaningfully improves security. Adding safe-path helpers to the other scripts is optional defense-in-depth and can satisfy the scanner.

---

### 3. Vulnerabilities – Phantom/transitive (High)

| GHSA / issue | Package | Description |
|--------------|---------|-------------|
| GHSA-5rjg-fvgr-3xxf | setuptools@56.0.0 | Path traversal in PackageIndex.download → Arbitrary File Write. Fixed in 78.1.1. |
| GHSA-cx63-2mw6-8hw5 | setuptools@56.0.0 | Command injection via package URL. Fixed in 70.0.0. |

**Triage**: setuptools@56.0.0 is a **transitive dependency** of endor-cockpit (via pyyaml@6.0.3). Platform exception for setuptools when introduced transitively has been updated; no further code change in repo required.

---

## Admission policy summary (from run log)

- **Vulnerabilities**: 2 finding UUIDs (setuptools vulns).
- **Secrets**: 1 finding UUID (authorization_policy.py).
- **In-house Python SAST Rules**: 4 finding UUIDs (path traversal in the four scripts above).

PR comments failed (401 Bad credentials) for the run; the scan itself completed and produced the above results.

---

## Recommended next steps

1. **Secrets**: Replace any secret-like examples in `authorization_policy.py` (and related docstrings) with placeholders; add `endorctl:allow` at the location if already snoozed.
2. **SAST path traversal**:
   - **sync_external_docs.py** (TP): Resolve `--openapi-output` and `--user-docs-output` to absolute paths and ensure they stay under a base directory (e.g. repo root); reject or normalize if they escape. This is the only finding that is a real path-traversal risk.
   - **setup_environment.py**, **traverse_findings_estate.py**, **validate_environment.py** (FP): No user-controlled paths reach file operations. Options: add `endorctl:allow` with a short comment at the open/path line to suppress, or add optional safe-path checks for defense-in-depth.
3. **Phantom deps**: No repo code change; maintain platform exception for setuptools when introduced transitively.

---

## Why exception policy 695c1815fb59143c33c66da4 did not capture the SAST findings

Policy **"Scripts Directory Exception - Path Traversal (Templated)"** (UUID `695c1815fb59143c33c66da4`) was fetched with `endorctl api get -r Policy --uuid 695c1815fb59143c33c66da4`. It does not apply to the blocking findings for two reasons:

### 1. Scope: policy does not apply in the child namespace

- **Policy namespace**: `tenant_meta.namespace` = `endor-solutions-tgowan` (parent).
- **Propagate**: `propagate: false` — the policy does **not** propagate to child namespaces.
- **Scan/findings namespace**: CI and findings run in `endor-solutions-tgowan.tgowan-endor` (child).

Exception policies in a parent namespace only apply in child namespaces when **Propagate this policy to all child namespaces** is enabled. With `propagate: false`, this policy is evaluated only in `endor-solutions-tgowan`, not in `endor-solutions-tgowan.tgowan-endor`, so it never runs against the findings from your CI scan.

**Fix**: In the Endor UI, edit the policy → **Advanced** → enable **Propagate this policy to all child namespaces**. Or create the same policy in the `endor-solutions-tgowan.tgowan-endor` namespace.

### 2. File path: one finding is outside `scripts/`

The Rego rule requires `file_path_match(finding, "scripts/")` (i.e. the finding’s file path must be under `scripts/`). The four blocking findings are in:

| File | Under `scripts/`? |
|------|-------------------|
| scripts/setup_environment.py | Yes |
| scripts/traverse_findings_estate.py | Yes |
| scripts/validate_environment.py | Yes |
| **.github/scripts/sync_external_docs.py** | **No** |

So even after fixing scope, the finding in `.github/scripts/sync_external_docs.py` would still not match this policy. To cover it you can either:

- Add a second exception policy that matches `.github/scripts/` (e.g. `file_path_match(finding, ".github/scripts/")`), or  
- Broaden this policy’s path condition (e.g. match both `scripts/` and `.github/scripts/`) if you want one policy for all four.
