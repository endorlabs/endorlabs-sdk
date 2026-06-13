"""Unit tests for policy validation workflow helpers."""

from __future__ import annotations

from endorlabs.resources.consumer.wire_compat import ConsumerPolicySpec
from endorlabs.resources.policy import Policy, PolicyType
from endorlabs.workflows.policies.validate import build_validation_body


def test_build_validation_body_template_policy() -> None:
    policy = Policy.model_construct(
        uuid="policy-1",
        meta={"name": "test-exception"},
        spec=ConsumerPolicySpec.model_construct(
            policy_type=PolicyType.EXCEPTION.value,
            template_uuid="6839f54bfc0b87f4c01f2d83",
            template_values={
                "VulnID": {"values": ["CVE-2026-42033"]},
            },
        ),
    )
    body = build_validation_body(
        namespace="customer.ns",
        policy=policy,
        project_uuid="proj-1",
        disable_preview=False,
    )
    assert body["tenant_meta"] == {"namespace": "customer.ns"}
    request = body["spec"]["request"]
    assert request["project_uuid"] == "proj-1"
    assert request["policy_type"] == "POLICY_TYPE_EXCEPTION"
    assert request["template_uuid"] == "6839f54bfc0b87f4c01f2d83"
    assert request["template_values"]["VulnID"]["values"] == ["CVE-2026-42033"]
    assert request["disable_preview"] is False
    assert "rule" not in request


def test_build_validation_body_rule_policy() -> None:
    policy = Policy.model_construct(
        uuid="policy-2",
        meta={"name": "rego-only"},
        spec=ConsumerPolicySpec.model_construct(
            policy_type=PolicyType.EXCEPTION.value,
            rule="package example\n",
            query_statements=["data.example.match_finding"],
            resource_kinds=["Finding"],
        ),
    )
    body = build_validation_body(
        namespace="customer.ns",
        policy=policy,
        project_uuid=None,
        disable_preview=True,
    )
    request = body["spec"]["request"]
    assert request["disable_preview"] is True
    assert "project_uuid" not in request
    assert request["rule"].startswith("package example")
    assert request["query_statements"] == ["data.example.match_finding"]
    assert request["resource_kinds"] == ["Finding"]
    assert "template_uuid" not in request
