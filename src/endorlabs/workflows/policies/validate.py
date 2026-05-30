"""Validate policies via PolicyValidation API (POST .../policy/validate).

Loads a stored policy, builds ``spec.request`` from template or rule fields,
and POSTs to ``/v1/namespaces/{namespace}/policy/validate``.

See ``skills-src/validate-policy/`` and ``python -m endorlabs.workflows.policies.validate``.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass, field
from typing import Any

import endorlabs
from endorlabs.core.exceptions import EndorAPIError, PermissionDeniedError
from endorlabs.resources.policy import Policy  # noqa: TC001


@dataclass
class PolicyValidationResult:
    """Parsed validation response plus optional finding match check."""

    namespace: str
    policy_uuid: str
    project_uuid: str | None
    response: dict[str, Any]
    finding_uuid: str | None = None
    finding_matched: bool | None = None
    errors: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        """True when validation succeeded and no auxiliary errors were recorded."""
        result = (self.response.get("spec") or {}).get("result") or self.response
        return bool(result.get("valid_policy")) and not self.errors


def _enum_value(value: Any) -> Any:
    if hasattr(value, "value"):
        return value.value
    return value


def _policy_target_kind(policy: Policy) -> str | None:
    spec = policy.spec
    if spec is None or not spec.finding:
        return None
    finding_cfg = spec.finding
    tk = getattr(finding_cfg, "target_kind", None)
    if tk is None and hasattr(finding_cfg, "get"):
        tk = finding_cfg.get("target_kind")
    return str(tk) if tk else None


def build_validation_body(
    *,
    namespace: str,
    policy: Policy,
    project_uuid: str | None,
    disable_preview: bool,
    request_name: str = "policy-validation-request",
) -> dict[str, Any]:
    """Build PolicyValidation POST body from a stored policy."""
    spec = policy.spec
    if spec is None:
        raise ValueError("Policy has no spec")

    request: dict[str, Any] = {"disable_preview": disable_preview}
    if project_uuid:
        request["project_uuid"] = project_uuid
    if spec.policy_type is not None:
        request["policy_type"] = _enum_value(spec.policy_type)

    if spec.template_uuid:
        request["template_uuid"] = spec.template_uuid
        if spec.template_values:
            request["template_values"] = spec.template_values
    else:
        if not spec.rule:
            raise ValueError(
                "Policy has no template_uuid; spec.rule is required for validate"
            )
        request["rule"] = spec.rule
        if spec.query_statements:
            request["query_statements"] = list(spec.query_statements)
        if spec.resource_kinds:
            request["resource_kinds"] = list(spec.resource_kinds)

    if spec.project_selector:
        request["project_selector"] = list(spec.project_selector)
    if spec.project_exceptions:
        request["project_exceptions"] = list(spec.project_exceptions)

    target_kind = _policy_target_kind(policy)
    if target_kind:
        request["target_kind"] = target_kind

    return {
        "tenant_meta": {"namespace": namespace},
        "meta": {"name": request_name},
        "spec": {"request": request},
    }


def validate_policy(
    client: endorlabs.Client,
    *,
    namespace: str,
    body: dict[str, Any],
) -> dict[str, Any]:
    """POST policy/validate and return parsed JSON."""
    api = client._client  # noqa: SLF001
    if api is None:
        raise RuntimeError("Client has no API connection")
    path = f"v1/namespaces/{namespace}/policy/validate"
    try:
        response = api.post(path, json=body)
        response.raise_for_status()
    except (EndorAPIError, PermissionDeniedError) as exc:
        msg = (
            f"POST /v1/namespaces/{namespace}/policy/validate failed. "
            "PolicyValidation is x-internal; use tenant-scoped credentials "
            "(ENDOR_NAMESPACE matching the customer namespace), not cross-tenant "
            "endor-admin read against customer namespaces."
        )
        raise PermissionDeniedError(msg) from exc
    data = response.json()
    if not isinstance(data, dict):
        raise TypeError("Unexpected non-object validation response")
    return data


def _collect_uuids(obj: Any, out: set[str]) -> None:
    if isinstance(obj, dict):
        for key, value in obj.items():
            if key in {"uuid", "resource_uuid", "finding_uuid"} and isinstance(
                value, str
            ):
                out.add(value)
            _collect_uuids(value, out)
    elif isinstance(obj, list):
        for item in obj:
            _collect_uuids(item, out)


def finding_in_validation_output(finding_uuid: str, validation: dict[str, Any]) -> bool:
    found: set[str] = set()
    _collect_uuids(validation, found)
    normalized = {u.lower() for u in found}
    return finding_uuid.lower() in normalized


def summarize_validation(validation: dict[str, Any]) -> str:
    """Return a short human-readable summary of a validation response."""
    lines: list[str] = []
    result = (validation.get("spec") or {}).get("result") or validation
    if "valid_policy" in result or "allow" in result:
        lines.append(f"valid_policy: {result.get('valid_policy')}")
        lines.append(f"allow: {result.get('allow')}")
        if result.get("validation_error"):
            lines.append(f"validation_error: {result['validation_error']}")
    matching = result.get("policy_output") or validation.get("matching_findings")
    if isinstance(matching, dict):
        lines.append(f"policy_output projects: {len(matching)}")
        for proj_uuid, output in list(matching.items())[:3]:
            if isinstance(output, dict):
                vr = output.get("violating_resources") or {}
                lines.append(f"  project {proj_uuid}: resource groups {len(vr)}")
    elif isinstance(matching, list):
        lines.append(f"matching_findings: {len(matching)}")
    return "\n".join(lines)


def run_validate_policy(
    *,
    namespace: str,
    policy_uuid: str,
    project_uuid: str | None = None,
    finding_uuid: str | None = None,
    disable_preview: bool = False,
) -> PolicyValidationResult:
    """Load policy (and optional finding), call validate API, return result."""
    client = endorlabs.Client(tenant=namespace)
    policy = client.Policy.get(policy_uuid, namespace=namespace)
    if policy.spec is None:
        raise ValueError("Policy has no spec")

    resolved_project = project_uuid
    if finding_uuid:
        finding = client.Finding.get(finding_uuid, namespace=namespace)
        if finding.spec and finding.spec.project_uuid:
            resolved_project = finding.spec.project_uuid
        elif not resolved_project and not disable_preview:
            raise ValueError("Finding has no spec.project_uuid; pass project_uuid")

    if not resolved_project and not disable_preview:
        raise ValueError("Provide project_uuid, finding_uuid, or disable_preview")

    body = build_validation_body(
        namespace=namespace,
        policy=policy,
        project_uuid=resolved_project,
        disable_preview=disable_preview,
    )
    response = validate_policy(client, namespace=namespace, body=body)

    finding_matched: bool | None = None
    if finding_uuid:
        finding_matched = finding_in_validation_output(finding_uuid, response)

    return PolicyValidationResult(
        namespace=namespace,
        policy_uuid=policy_uuid,
        project_uuid=resolved_project,
        response=response,
        finding_uuid=finding_uuid,
        finding_matched=finding_matched,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Validate a policy via POST /v1/namespaces/{namespace}/policy/validate."
        ),
    )
    parser.add_argument(
        "--namespace",
        default=os.environ.get("ENDOR_NAMESPACE", "").strip(),
        help="Customer tenant namespace (default: ENDOR_NAMESPACE)",
    )
    parser.add_argument("--policy-uuid", required=True, help="Policy resource UUID")
    parser.add_argument(
        "--finding-uuid",
        help="Finding UUID; sets project_uuid from finding.spec.project_uuid",
    )
    parser.add_argument(
        "--project-uuid",
        help="Project UUID for spec.request.project_uuid",
    )
    parser.add_argument(
        "--disable-preview",
        action="store_true",
        help="Set spec.request.disable_preview=true (syntax-only, no project data)",
    )
    parser.add_argument(
        "--output-json",
        action="store_true",
        help="Print full validation response JSON",
    )
    args = parser.parse_args(argv)

    if not args.namespace:
        print("Set ENDOR_NAMESPACE or pass --namespace", file=sys.stderr)
        return 1

    client = endorlabs.Client(tenant=args.namespace)
    policy = client.Policy.get(args.policy_uuid, namespace=args.namespace)
    if not policy.meta.name:
        print("Policy missing meta.name", file=sys.stderr)
        return 1
    print(f"Policy: {policy.meta.name} ({args.policy_uuid})")

    project_uuid = args.project_uuid
    if args.finding_uuid:
        finding = client.Finding.get(args.finding_uuid, namespace=args.namespace)
        if finding.meta:
            print(f"Finding: {finding.meta.name} ({args.finding_uuid})")
        if finding.spec and finding.spec.project_uuid:
            project_uuid = finding.spec.project_uuid
        elif not project_uuid and not args.disable_preview:
            print(
                "Finding has no spec.project_uuid; pass --project-uuid", file=sys.stderr
            )
            return 1

    if not project_uuid and not args.disable_preview:
        print(
            "Provide --project-uuid, --finding-uuid, or --disable-preview",
            file=sys.stderr,
        )
        return 1

    if project_uuid:
        print(f"Project UUID: {project_uuid}")

    try:
        result = run_validate_policy(
            namespace=args.namespace,
            policy_uuid=args.policy_uuid,
            project_uuid=project_uuid,
            finding_uuid=args.finding_uuid,
            disable_preview=args.disable_preview,
        )
    except (EndorAPIError, PermissionDeniedError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 1

    if args.output_json:
        json.dump(result.response, sys.stdout, indent=2)
        sys.stdout.write("\n")
    else:
        print(summarize_validation(result.response))

    if result.finding_uuid is not None and result.finding_matched is not None:
        print(
            f"Finding {result.finding_uuid} in validation output: "
            f"{'YES' if result.finding_matched else 'NO'}"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
