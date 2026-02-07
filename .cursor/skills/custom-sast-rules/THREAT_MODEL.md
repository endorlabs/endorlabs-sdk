# Threat Modeling a Repository for Custom SAST Rules

How to systematically identify what custom static-analysis rules a codebase
needs, using first principles and the CWE Top 25 as a framework.

---

## 1. Establish the Threat Model Canvas

Before writing any rule, answer these questions about the repository:

| Question | Why it matters |
|----------|---------------|
| What **credential types** does the code handle? | Determines which CWEs apply (log leak, hardcoded creds, missing encryption). |
| What **trust boundaries** exist? | Raw HTTP clients, subprocess calls, and third-party libraries each create surfaces where safety layers can be bypassed. |
| Who **consumes** this code? | An SDK used by many teams amplifies any vulnerability; a one-off script does not. |
| What **log/debug frameworks** are active? | Frameworks like `httpx`, `httpcore`, and stdlib `logging` emit headers and bodies at DEBUG level. If the code handles secrets, these are leak vectors. |
| What **safety measures** already exist? | You cannot write an absence-detection rule unless you know what the "safe" pattern looks like. |

### Worked example: Endor Cockpit SDK

The SDK handles three credential types:

1. **API key + secret** -- sent as JSON in an auth POST through raw
   `httpx.Client` (bypassing the SDK's own `APIClient.post`).
2. **Bearer token** -- returned from auth and attached as an
   `Authorization` header on every request.
3. **OAuth callback token** -- carried as a `?token=...` query parameter
   in the auth-server redirect URL.

The safety measure is `RedactingFilter` (in `src/endorlabs/utils/redaction.py`)
attached to every module-level logger via `addFilter()`. The threat is any
logger that *lacks* this filter.

---

## 2. Map the Credential Lifecycle

For each credential type, trace four stages:

```
ENTER --> TRANSIT --> REST --> EXIT
```

| Stage | Questions | SAST rule opportunity |
|-------|-----------|----------------------|
| **Enter** | Where does the secret first appear in code? Environment variable? Config file? API response? | Detect hardcoded secrets (CWE-798). |
| **Transit** | How is it passed between functions/modules? Is it logged, serialized, or stored in an intermediate variable? | Detect log leaks (CWE-532), error-message exposure (CWE-209). |
| **Rest** | Is it stored anywhere? In-memory cache? Temp file? Database? | Detect plaintext storage (CWE-311), insecure temp files (CWE-377). |
| **Exit** | How does it leave the process? HTTP header? Response body? Log line? | Detect missing TLS (CWE-319), overly-broad error responses (CWE-209). |

Focus SAST rules on the **Transit** and **Exit** stages -- these are
where accidental exposure happens and where static patterns are most
reliable.

---

## 3. CWE Top 25 Checklist for SDKs

Not every CWE applies to every repository. For an SDK or client library,
prioritize these:

| CWE | Name | SDK relevance | Detection pattern |
|-----|------|---------------|-------------------|
| CWE-798 | Use of Hard-coded Credentials | API keys, tokens in source | Presence: literal strings matching credential patterns |
| CWE-532 | Insertion of Sensitive Info into Log File | Logging secrets at DEBUG level | **Absence**: logger without redaction filter |
| CWE-209 | Generation of Error Message Containing Sensitive Info | Stack traces, auth errors leaking tokens | Presence: `except` blocks that log/return raw exception |
| CWE-311 | Missing Encryption of Sensitive Data | Secrets stored in plaintext files or env without protection | Presence: writing secrets to files without encryption |
| CWE-319 | Cleartext Transmission of Sensitive Info | HTTP (not HTTPS) for auth endpoints | Presence: `http://` in auth URLs |
| CWE-522 | Insufficiently Protected Credentials | Weak hashing, no rotation | Context-dependent; harder to detect statically |
| CWE-276 | Incorrect Default Permissions | Config files, temp files created world-readable | Presence: `open()` / `os.chmod()` with permissive modes |
| CWE-20 | Improper Input Validation | Namespace, UUID, filter inputs not validated | Absence: missing validation before use in API calls |
| CWE-94 | Improper Control of Code Generation | `eval()`, `exec()`, `logging.config.listen()` | Presence: dangerous function calls |

### The key insight: Absence vs Presence

Most SAST rules detect the **presence** of something dangerous
(`eval(...)`, `logging.config.listen(...)`). But some of the most
impactful SDK vulnerabilities are about the **absence** of something
safe.

Ask: *"What safety measure SHOULD be here but might be missing?"*

Examples of absence-detection rules:
- Logger created without a redaction filter
- HTTP client instantiated without TLS verification
- API response parsed without schema validation
- User input used without sanitization

These require a different pattern strategy
(`pattern` + `pattern-not-inside`) than simple presence rules.

---

## 4. Structured Questions to Ask

Walk through these for every module in the repository:

### Data handling
1. Does this module touch credentials, tokens, or PII?
2. If yes, what is the full lifecycle (enter/transit/rest/exit)?
3. Are there code paths where the secret could be emitted unredacted?

### Logging and debugging
4. Does this module create a logger?
5. Does the logger have the project's redaction/sanitization filter?
6. Could a consumer enable DEBUG logging and see secrets?

### Trust boundaries
7. Does this module call external HTTP clients directly?
8. Does it bypass the project's standard client/wrapper?
9. Are there subprocess calls that could leak env vars?

### Error handling
10. Do exception handlers expose secret material in messages?
11. Are stack traces returned to callers or logged verbatim?

### Dependencies
12. Does this module use libraries that have their own logging?
13. Are those library loggers also covered by the redaction filter?

### Configuration
14. Are default configurations secure? (TLS on, verification on, restrictive permissions)
15. Can a consumer accidentally weaken security by passing wrong options?

---

## 5. From Threat Model to Rule Specification

Once you have identified a threat, capture it in a structured format
before writing any YAML:

```
Threat:       [short description]
CWE:          [CWE-NNN]
Detection:    [presence / absence]
Safe pattern: [what compliant code looks like]
Unsafe pattern: [what non-compliant code looks like]
Scope:        [which files/directories to scan]
Confidence:   [HIGH / MEDIUM / LOW]
Impact:       [HIGH / MEDIUM / LOW]
```

Example:

```
Threat:       Module-level logger missing RedactingFilter
CWE:          CWE-532
Detection:    Absence
Safe pattern: logger = logging.getLogger(__name__)
              logger.addFilter(RedactingFilter([...]))
Unsafe pattern: logger = logging.getLogger(__name__)
                # no addFilter call
Scope:        src/endorlabs/
Confidence:   HIGH
Impact:       HIGH
```

This specification maps directly to the OpenGrep/Semgrep YAML structure.
See [AUTHORING.md](AUTHORING.md) for the next step.

---

## References

- [CWE Top 25 (2024)](https://cwe.mitre.org/top25/archive/2024/2024_cwe_top25.html)
- [OWASP Top 10 (2021)](https://owasp.org/Top10/)
- [CWE-532: Insertion of Sensitive Information into Log File](https://cwe.mitre.org/data/definitions/532.html)
- [OWASP A09:2021 Security Logging and Monitoring Failures](https://owasp.org/Top10/A09_2021-Security_Logging_and_Monitoring_Failures/)
