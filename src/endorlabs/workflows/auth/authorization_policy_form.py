"""AuthorizationPolicy claim/namespace form heuristics.

Used by skill ``endor-audit-authorization-policies``. Pure functions over
normalized AuthorizationPolicyRecord dicts — no Client I/O.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Literal

Severity = Literal["critical", "warning", "info"]

_PROVIDER_TAGS = frozenset(
    {
        "google",
        "github",
        "gitlab",
        "email",
        "azureadv2",
        "sso",
        "github-action",
    }
)
_DOUBLE_PROVIDER_RE = re.compile(
    r"^user=.+@(github|gitlab|google)@(github|gitlab|google)$",
    re.IGNORECASE,
)
_USER_CLAIM_RE = re.compile(r"^user=(.+)$", re.IGNORECASE)


@dataclass(frozen=True)
class FormFinding:
    """One form-audit finding for a policy."""

    severity: Severity
    code: str
    message: str
    policy_uuid: str | None
    policy_name: str
    field: str
    observed: str
    suggestion: str


def _split_csv_blob(value: str) -> list[str]:
    return [part.strip() for part in value.split(",") if part.strip()]


def audit_target_namespaces(
    *,
    policy_uuid: str | None,
    policy_name: str,
    target_namespaces: list[str],
) -> list[FormFinding]:
    """Flag CSV blobs and empty targets."""
    findings: list[FormFinding] = []
    if not target_namespaces:
        findings.append(
            FormFinding(
                severity="warning",
                code="empty_target_namespaces",
                message="target_namespaces is empty.",
                policy_uuid=policy_uuid,
                policy_name=policy_name,
                field="spec.target_namespaces",
                observed="[]",
                suggestion="Set one or more namespace paths as separate list elements.",
            )
        )
        return findings

    for entry in target_namespaces:
        if "," in entry:
            parts = _split_csv_blob(entry)
            findings.append(
                FormFinding(
                    severity="critical",
                    code="comma_separated_namespace_blob",
                    message=(
                        "A single target_namespaces entry contains commas; "
                        "the API expects one namespace path per list element."
                    ),
                    policy_uuid=policy_uuid,
                    policy_name=policy_name,
                    field="spec.target_namespaces",
                    observed=entry,
                    suggestion=(
                        "Split into separate list elements: " + json.dumps(parts)
                    ),
                )
            )
        elif ";" in entry:
            findings.append(
                FormFinding(
                    severity="critical",
                    code="semicolon_separated_namespace_blob",
                    message=(
                        "A target_namespaces entry looks like a joined "
                        "multi-path string."
                    ),
                    policy_uuid=policy_uuid,
                    policy_name=policy_name,
                    field="spec.target_namespaces",
                    observed=entry,
                    suggestion="Split on ';' into separate list elements.",
                )
            )
    return findings


def audit_clause(
    *,
    policy_uuid: str | None,
    policy_name: str,
    clause: list[str],
) -> list[FormFinding]:
    """Flag clause shape and IdP claim footguns."""
    findings: list[FormFinding] = []
    if not clause:
        findings.append(
            FormFinding(
                severity="warning",
                code="empty_clause",
                message="clause is empty.",
                policy_uuid=policy_uuid,
                policy_name=policy_name,
                field="spec.clause",
                observed="[]",
                suggestion=(
                    "Add claim predicates (and IdP tag) matching the identity provider."
                ),
            )
        )
        return findings

    provider_tags = [c for c in clause if c.strip().lower() in _PROVIDER_TAGS]
    predicates = [c for c in clause if c.strip().lower() not in _PROVIDER_TAGS]

    for entry in clause:
        if "," in entry and ("." in entry or " " in entry):
            findings.append(
                FormFinding(
                    severity="critical",
                    code="comma_blob_in_clause",
                    message=(
                        "A clause entry looks like a comma-joined blob "
                        "(namespaces or claims)."
                    ),
                    policy_uuid=policy_uuid,
                    policy_name=policy_name,
                    field="spec.clause",
                    observed=entry,
                    suggestion=(
                        "Split into separate clause strings; namespaces belong in "
                        "target_namespaces."
                    ),
                )
            )
        if _DOUBLE_PROVIDER_RE.match(entry.strip()):
            findings.append(
                FormFinding(
                    severity="critical",
                    code="double_provider_suffix",
                    message=(
                        "user claim appears to include the IdP twice "
                        "(UI Value was probably 'handle@gitlab' instead of 'handle')."
                    ),
                    policy_uuid=policy_uuid,
                    policy_name=policy_name,
                    field="spec.clause",
                    observed=entry,
                    suggestion=(
                        "For GitHub/GitLab set UI Value to the platform handle only "
                        "(e.g. handle → user=handle@gitlab)."
                    ),
                )
            )

    for entry in predicates:
        match = _USER_CLAIM_RE.match(entry.strip())
        if not match:
            continue
        value = match.group(1)
        if "@" in value:
            local, _, maybe_provider = value.rpartition("@")
            if maybe_provider.lower() in {"gitlab", "github"} and "@" in local:
                findings.append(
                    FormFinding(
                        severity="warning",
                        code="gitlab_github_user_looks_like_email",
                        message=(
                            "GitHub/GitLab user claim local part contains '@'; "
                            "docs expect the platform handle, not an email."
                        ),
                        policy_uuid=policy_uuid,
                        policy_name=policy_name,
                        field="spec.clause",
                        observed=entry,
                        suggestion="Use Key=user Value=<handle> only (not email).",
                    )
                )

    if any(p.lower().startswith("email=") for p in predicates) and any(
        t.lower() in {"gitlab", "github"} for t in provider_tags
    ):
        findings.append(
            FormFinding(
                severity="warning",
                code="email_key_with_social_provider",
                message=(
                    "clause uses email= with a GitLab/GitHub provider tag; "
                    "product docs reserve email claims for Email IdP "
                    "(and some cloud principals)."
                ),
                policy_uuid=policy_uuid,
                policy_name=policy_name,
                field="spec.clause",
                observed=json.dumps(clause),
                suggestion="For GitLab/GitHub use Key=user with the platform handle.",
            )
        )

    if predicates and not provider_tags:
        findings.append(
            FormFinding(
                severity="info",
                code="missing_provider_tag",
                message=(
                    "No obvious IdP tag element in clause (may be fine for custom IdP)."
                ),
                policy_uuid=policy_uuid,
                policy_name=policy_name,
                field="spec.clause",
                observed=json.dumps(clause),
                suggestion="Compare with a known-good peer policy for the same IdP.",
            )
        )

    return findings


def audit_policy_record(policy: dict[str, Any]) -> list[FormFinding]:
    """Run all form checks on one normalized policy dict."""
    uuid = policy.get("uuid")
    name = str(policy.get("name") or "unnamed")
    clause = list(policy.get("clause") or [])
    targets = list(policy.get("target_namespaces") or [])
    findings = audit_target_namespaces(
        policy_uuid=uuid if isinstance(uuid, str) else None,
        policy_name=name,
        target_namespaces=[str(t) for t in targets],
    )
    findings.extend(
        audit_clause(
            policy_uuid=uuid if isinstance(uuid, str) else None,
            policy_name=name,
            clause=[str(c) for c in clause],
        )
    )
    return findings


def audit_authorization_policy_forms(
    policies: list[dict[str, Any]],
) -> list[FormFinding]:
    """Audit a list of normalized AuthorizationPolicy records."""
    findings: list[FormFinding] = []
    for policy in policies:
        findings.extend(audit_policy_record(policy))
    return findings
