#!/usr/bin/env python3
"""Create or upsert a ServiceRequest to enable nat_network_requests for a tenant.

This script:
1) Loads a template ServiceRequest from endor-admin by UUID.
2) Resolves the target tenant SystemConfig UUID.
3) Builds a similar ServiceRequest payload for the target tenant.
4) Upserts in endor-admin namespace:
   - create if no existing matching request is found
   - optionally delete + recreate when --replace-existing is set
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any

from endorlabs.api_client import APIClient

_NAMESPACE_ENV_KEY = "ENDOR_NAMESPACE"
DEFAULT_TEMPLATE_REQUEST_UUID = "69700bbbcb7b6d4001d5b4e9"
DEFAULT_ADMIN_NAMESPACE = "endor-admin"
DEFAULT_APPROVERS = [
    "ypulse@endor.ai",
    "kdogra@endor.ai",
    "lmoreno@endor.ai",
]


def _resolve_target_tenant(cli_tenant: str | None) -> str:
    tenant = (cli_tenant or os.getenv(_NAMESPACE_ENV_KEY) or "").strip()
    if not tenant:
        raise ValueError(
            f"Target tenant required: pass --target-tenant or set {_NAMESPACE_ENV_KEY}."
        )
    return tenant


def _require_dict(value: Any, *, name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"Expected {name} to be a JSON object")
    return value


def _get_service_request(
    client: APIClient, *, admin_namespace: str, request_uuid: str
) -> dict[str, Any]:
    response = client.get(
        f"v1/namespaces/{admin_namespace}/service-requests/{request_uuid}"
    )
    return _require_dict(response.json(), name="service request response")


def _resolve_target_system_config_uuid(client: APIClient, *, tenant: str) -> str:
    response = client.get(
        f"v1/namespaces/{tenant}/system-config",
        params={"list_parameters.page_size": "1"},
    )
    payload = _require_dict(response.json(), name="system-config list response")
    list_block = _require_dict(payload.get("list"), name="system-config list block")
    objects = list_block.get("objects")
    if not isinstance(objects, list) or not objects:
        raise ValueError(f"No SystemConfig found for tenant '{tenant}'")
    first_obj = _require_dict(objects[0], name="system-config object")
    system_config_uuid = first_obj.get("uuid")
    if not isinstance(system_config_uuid, str) or not system_config_uuid:
        raise ValueError(f"SystemConfig UUID missing for tenant '{tenant}'")
    return system_config_uuid


def _build_payload(
    *,
    source_request: dict[str, Any],
    target_tenant: str,
    target_system_config_uuid: str,
    approvers_override: list[str] | None,
) -> dict[str, Any]:
    source_spec = _require_dict(source_request.get("spec"), name="source spec")
    source_data = _require_dict(source_spec.get("data"), name="source spec.data")
    request_block = _require_dict(source_data.get("request"), name="source data.request")
    object_block = _require_dict(source_data.get("object"), name="source data.object")
    _ = _require_dict(object_block.get("spec"), name="source object.spec")

    source_approvers = source_spec.get("approvers")
    approvers = (
        approvers_override
        if approvers_override
        else (source_approvers if isinstance(source_approvers, list) else [])
    )

    description = (
        f"SystemConfig - {target_tenant} - enable nat_network_requests"
    )
    name = f"SystemConfig - {target_tenant}"

    return {
        "meta": {
            "name": name,
            "description": description,
        },
        "spec": {
            "description": description,
            "resource": source_spec.get("resource") or "SystemConfig",
            "target_namespace": target_tenant,
            "approvers": approvers,
            "status": "REQUEST_STATUS_UNSPECIFIED",
            "method": source_spec.get("method") or "METHOD_UPDATE",
            "data": {
                "@type": source_data.get("@type"),
                "request": {
                    "update_mask": "spec.cloud_deployment",
                    "force": request_block.get("force"),
                },
                "object": {
                    "uuid": target_system_config_uuid,
                    "spec": {
                        "cloud_deployment": {
                            "nat_network_requests": True,
                        }
                    },
                },
            },
        },
    }


def _find_existing(
    client: APIClient,
    *,
    admin_namespace: str,
    name: str,
    target_tenant: str,
) -> list[dict[str, Any]]:
    filter_expr = (
        f'meta.name=="{name}" AND spec.target_namespace=="{target_tenant}"'
    )
    response = client.get(
        f"v1/namespaces/{admin_namespace}/service-requests",
        params={
            "list_parameters.filter": filter_expr,
            "list_parameters.page_size": "50",
        },
    )
    payload = _require_dict(response.json(), name="service-request list response")
    list_block = _require_dict(payload.get("list"), name="service-request list block")
    objects = list_block.get("objects")
    if not isinstance(objects, list):
        return []
    return [obj for obj in objects if isinstance(obj, dict)]


def _create_request(
    client: APIClient, *, admin_namespace: str, payload: dict[str, Any]
) -> dict[str, Any]:
    response = client.post(
        f"v1/namespaces/{admin_namespace}/service-requests",
        json=payload,
    )
    return _require_dict(response.json(), name="created service request")


def _delete_request(client: APIClient, *, admin_namespace: str, request_uuid: str) -> None:
    _ = client.delete(f"v1/namespaces/{admin_namespace}/service-requests/{request_uuid}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--template-request-uuid",
        default=DEFAULT_TEMPLATE_REQUEST_UUID,
        help="Source ServiceRequest UUID in endor-admin to clone data from.",
    )
    parser.add_argument(
        "--admin-namespace",
        default=DEFAULT_ADMIN_NAMESPACE,
        help="Namespace that stores ServiceRequest resources (default: endor-admin).",
    )
    parser.add_argument(
        "--target-tenant",
        default=None,
        help=(
            "Tenant namespace to target. "
            f"Falls back to {_NAMESPACE_ENV_KEY} when omitted."
        ),
    )
    parser.add_argument(
        "--approver",
        action="append",
        default=list(DEFAULT_APPROVERS),
        help="Approver email. Repeatable; overrides template approvers when set.",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Actually create/update in backend (default is dry-run preview).",
    )
    parser.add_argument(
        "--replace-existing",
        action="store_true",
        help="If matching request exists, delete it and create a fresh one.",
    )
    args = parser.parse_args()

    client = APIClient(auth_method="admin")
    try:
        target_tenant = _resolve_target_tenant(args.target_tenant)
        source_request = _get_service_request(
            client,
            admin_namespace=args.admin_namespace,
            request_uuid=args.template_request_uuid,
        )
        target_system_config_uuid = _resolve_target_system_config_uuid(
            client, tenant=target_tenant
        )
        payload = _build_payload(
            source_request=source_request,
            target_tenant=target_tenant,
            target_system_config_uuid=target_system_config_uuid,
            approvers_override=list(args.approver),
        )

        name = payload["meta"]["name"]
        existing = _find_existing(
            client,
            admin_namespace=args.admin_namespace,
            name=name,
            target_tenant=target_tenant,
        )

        result: dict[str, Any] = {
            "mode": "apply" if args.apply else "dry-run",
            "admin_namespace": args.admin_namespace,
            "target_tenant": target_tenant,
            "template_request_uuid": args.template_request_uuid,
            "target_system_config_uuid": target_system_config_uuid,
            "existing_count": len(existing),
            "payload_preview": payload,
        }

        if not args.apply:
            print(json.dumps(result, indent=2))
            return 0

        if existing and not args.replace_existing:
            result["action"] = "noop_existing"
            result["existing_request_uuids"] = [obj.get("uuid") for obj in existing]
            print(json.dumps(result, indent=2))
            return 0

        if existing and args.replace_existing:
            for obj in existing:
                req_uuid = obj.get("uuid")
                if isinstance(req_uuid, str) and req_uuid:
                    _delete_request(
                        client,
                        admin_namespace=args.admin_namespace,
                        request_uuid=req_uuid,
                    )
            result["deleted_existing_count"] = len(existing)

        created = _create_request(
            client,
            admin_namespace=args.admin_namespace,
            payload=payload,
        )
        result["action"] = "created"
        result["created_uuid"] = created.get("uuid")
        print(json.dumps(result, indent=2))
        return 0
    except Exception as exc:  # noqa: BLE001
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    finally:
        client.close()


if __name__ == "__main__":
    raise SystemExit(main())
