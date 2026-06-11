"""Unit tests for Policy nested finding/notification configs."""

from __future__ import annotations

from endorlabs.resources.policy import Policy


def test_policy_parses_typed_finding_and_notification() -> None:
    policy = Policy(
        uuid="policy-uuid",
        meta={"name": "test-policy", "kind": "Policy", "version": "v1"},
        tenant_meta={"namespace": "tenant.ns"},
        spec={
            "policy_type": "POLICY_TYPE_USER_FINDING",
            "finding": {"target_kind": "FINDING_TARGET_KIND_PACKAGE_VERSION"},
            "notification": {
                "notification_target_uuids": ["target-1"],
                "aggregation_type": "AGGREGATION_TYPE_PROJECT",
            },
        },
    )
    assert policy.spec is not None
    assert policy.spec.finding is not None
    assert policy.spec.finding.target_kind == "FINDING_TARGET_KIND_PACKAGE_VERSION"
    assert policy.spec.notification is not None
    assert policy.spec.notification.notification_target_uuids == ["target-1"]
