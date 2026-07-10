"""Unit tests for AuthorizationPolicy normalize/map helpers."""

from __future__ import annotations

from types import SimpleNamespace

from endorlabs.workflows.auth.authorization_policy import (
    build_claim_namespace_map,
    expand_namespace_scope,
    normalize_authorization_policy,
)


def test_expand_namespace_scope_without_propagation() -> None:
    scope = expand_namespace_scope(["root"], propagate=False)
    assert scope.direct_namespaces == ["root"]
    assert scope.propagated_namespace_prefixes == []


def test_expand_namespace_scope_with_propagation() -> None:
    scope = expand_namespace_scope(["root.A"], propagate=True)
    assert scope.direct_namespaces == ["root.A"]
    assert scope.propagated_namespace_prefixes == ["root.A.*"]


def test_build_claim_namespace_map_detects_overlap() -> None:
    policies = [
        {
            "name": "policy-a",
            "clause": ["group=eng-a"],
            "target_namespaces": ["root.A"],
            "propagate": False,
        },
        {
            "name": "policy-b",
            "clause": ["group=eng-b"],
            "target_namespaces": ["root.A", "root.B"],
            "propagate": False,
        },
    ]
    report = build_claim_namespace_map(policies)
    assert "group=eng-a" in report.claims
    assert "group=eng-b" in report.claims
    assert "root.A" in report.overlap.direct_namespace_to_claim_keys
    assert set(report.overlap.direct_namespace_to_claim_keys["root.A"]) == {
        "group=eng-a",
        "group=eng-b",
    }


def test_normalize_authorization_policy() -> None:
    policy = SimpleNamespace(
        uuid="abc",
        meta=SimpleNamespace(name="policy-x"),
        tenant_meta=SimpleNamespace(namespace="tenant"),
        spec=SimpleNamespace(
            clause=["user=a@gitlab", "gitlab"],
            target_namespaces=["tenant.child"],
            propagate=True,
            permissions=SimpleNamespace(
                model_dump=lambda: {"roles": ["SYSTEM_ROLE_READ_ONLY"]}
            ),
        ),
    )
    record = normalize_authorization_policy(policy)
    assert record.get("uuid") == "abc"
    assert record.get("name") == "policy-x"
    assert record.get("clause") == ["user=a@gitlab", "gitlab"]
    assert record.get("target_namespaces") == ["tenant.child"]
    assert record.get("propagate") is True
    assert record.get("namespace") == "tenant"
