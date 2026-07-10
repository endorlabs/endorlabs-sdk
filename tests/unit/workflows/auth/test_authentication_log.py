"""Unit tests for authentication log workflow helpers."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from unittest.mock import MagicMock

from endorlabs.operations.list_response import GroupBucket
from endorlabs.workflows.auth.authentication_log import (
    auth_log_filter,
    count_logins_from_rows,
    create_time_lower_bound_filter,
    extract_user_identifiers,
    interactive_uri_filter,
    is_api_key_noise,
    is_sso_login_uri,
    list_auth_logs,
    normalize_auth_log,
    parse_claims_from_group_bucket,
    primary_identity,
)

GROUP_KEY = json.dumps(
    [
        {
            "key": "spec.claims",
            "value": [
                "ID=116341557942666677054",
                "email=darcher@endor.ai",
                "user=darcher@endor.ai@google",
            ],
        }
    ]
)


def test_create_time_lower_bound_filter_uses_iso_date() -> None:
    anchor = datetime(2026, 7, 7, 12, 0, 0, tzinfo=UTC)
    filt = create_time_lower_bound_filter(90, now=anchor)
    assert filt.startswith("meta.create_time>=date(")
    assert "2026-04-" in filt


def test_auth_log_filter_composes_interactive_login_filter() -> None:
    anchor = datetime(2026, 7, 7, 12, 0, 0, tzinfo=UTC)
    filt = auth_log_filter(7, now=anchor)
    assert "meta.create_time>=date(" in filt
    assert "spec.success!=false" in filt
    assert interactive_uri_filter() in filt
    assert "tenant_meta.namespace" not in filt


def test_auth_log_filter_can_disable_interactive_uri_filter() -> None:
    filt = auth_log_filter(7, interactive_only=False)
    assert "spec.uri matches" not in filt


def test_extract_user_identifiers_dedupes_claims() -> None:
    claims = [
        "email=user@example.com",
        "email=user@example.com",
        "user=user@example.com@x509",
        "ID=12345",
        "issuer=https://api.endorlabs.com/v1",
    ]
    assert extract_user_identifiers(claims) == [
        "email=user@example.com",
        "user=user@example.com@x509",
        "id=12345",
    ]


def test_primary_identity_prefers_email() -> None:
    identifiers = extract_user_identifiers(
        ["email=scheduler", "email=user@example.com", "ID=1"]
    )
    assert primary_identity(identifiers) == "user@example.com"


def test_is_api_key_noise_detects_automation_paths() -> None:
    assert is_api_key_noise("/v1/auth/api-key")
    assert is_api_key_noise(
        "https://api.endorlabs.com/v1/auth/api-key?issuing_user=bot"
    )
    assert not is_api_key_noise("/v1/auth/saml-callback?tenant=tenant")


def test_is_sso_login_uri_detects_interactive_callbacks() -> None:
    assert is_sso_login_uri("/v1/auth/google/callback?state=abc")
    assert is_sso_login_uri("/v1/auth/saml-callback?tenant=example-tenant")
    assert not is_sso_login_uri("/v1/auth/api-key")


def test_normalize_auth_log_from_masked_dict() -> None:
    row = {
        "uuid": "log-1",
        "tenant_meta": {"namespace": "system"},
        "meta": {"create_time": "2026-07-01T10:00:00Z"},
        "spec": {
            "uri": "/v1/auth/saml-callback",
            "success": True,
            "claims": ["email=user@example.com"],
            "remote_address": "203.0.113.1",
        },
    }
    normalized = normalize_auth_log(row)
    assert normalized["namespace"] == "system"
    assert normalized["created"] == "2026-07-01T10:00:00Z"
    assert normalized["claims"] == ["email=user@example.com"]


def test_parse_claims_from_group_bucket_reads_spec_claims() -> None:
    bucket = GroupBucket(
        key=GROUP_KEY,
        parsed={"spec.claims": "[]"},
        data={"aggregation_count": {"count": 3}},
        count=0,
    )
    claims = parse_claims_from_group_bucket(bucket)
    assert claims == [
        "ID=116341557942666677054",
        "email=darcher@endor.ai",
        "user=darcher@endor.ai@google",
    ]


def test_count_logins_from_rows_groups_by_identity() -> None:
    rows = [
        {
            "created": "2026-07-01T10:00:00Z",
            "claims": ["email=alice@example.com"],
            "uri": "/v1/auth/sso",
            "success": True,
        },
        {
            "created": "2026-07-02T10:00:00Z",
            "claims": ["email=alice@example.com"],
            "uri": "/v1/auth/sso",
            "success": True,
        },
        {
            "created": "2026-07-03T10:00:00Z",
            "claims": ["email=bob@example.com"],
            "uri": "/v1/auth/sso",
            "success": True,
        },
    ]
    activity = count_logins_from_rows(rows, days=7)
    assert len(activity) == 2
    alice = next(item for item in activity if item.identity == "alice@example.com")
    bob = next(item for item in activity if item.identity == "bob@example.com")
    assert alice.login_count == 2
    assert alice.last_login == "2026-07-02T10:00:00Z"
    assert bob.login_count == 1


def test_probe_auth_logs_uses_tenant_path() -> None:
    client = MagicMock()
    client.AuthenticationLog.list.return_value = []

    from endorlabs.workflows.auth.authentication_log import (
        AUTHENTICATION_LOG_INVESTIGATION_MASK,
        probe_auth_logs,
    )

    probe_auth_logs(
        client,
        namespace="tenant.ns",
        days=14,
        max_pages=3,
    )

    client.AuthenticationLog.list.assert_called_once()
    kwargs = client.AuthenticationLog.list.call_args.kwargs
    assert kwargs["namespace"] == "tenant.ns"
    assert kwargs["traverse"] is False
    assert kwargs["mask"] == AUTHENTICATION_LOG_INVESTIGATION_MASK
    assert "meta.create_time>=date(" in kwargs["filter"]
    assert "spec.uri matches" not in kwargs["filter"]


def test_filter_auth_logs_by_email_matches_claims() -> None:
    from endorlabs.workflows.auth.authentication_log import filter_auth_logs_by_email

    rows = [
        {
            "uri": "/auth/sso",
            "claims": ["email=user@example.com"],
            "authorized_tenants": [],
        },
        {
            "uri": "/auth/sso",
            "claims": ["email=other@example.com"],
            "authorized_tenants": [],
        },
    ]
    matched = filter_auth_logs_by_email(rows, "user@example.com")
    assert len(matched) == 1


def test_auth_log_snapshot() -> None:
    from endorlabs.workflows.auth.authentication_log import auth_log_snapshot

    snap = auth_log_snapshot(
        {
            "uri": "/auth/saml-callback",
            "claims": ["email=user@example.com"],
            "authorized_tenants": ["tenant-a"],
            "success": True,
            "created": "2026-07-01T00:00:00Z",
        }
    )
    assert snap["user"] == "user@example.com"
    assert snap["authorized_tenants"] == ["tenant-a"]
    assert set(snap) == {"user", "uri", "authorized_tenants", "success", "created"}


def test_filter_auth_logs_by_email_empty_returns_all() -> None:
    from endorlabs.workflows.auth.authentication_log import filter_auth_logs_by_email

    rows = [{"claims": ["email=a@example.com"]}, {"claims": ["email=b@example.com"]}]
    assert filter_auth_logs_by_email(rows, "") == rows
    assert filter_auth_logs_by_email(rows, "   ") == rows


def test_list_auth_logs_excludes_failed_login() -> None:
    client = MagicMock()
    client.AuthenticationLog.list.return_value = [
        {
            "uuid": "ok",
            "meta": {"create_time": "2026-07-01T10:00:00Z"},
            "spec": {
                "uri": "/v1/auth/saml-callback",
                "success": True,
                "claims": ["email=ok@example.com"],
            },
        },
        {
            "uuid": "fail",
            "meta": {"create_time": "2026-07-01T11:00:00Z"},
            "spec": {
                "uri": "/v1/auth/saml-callback",
                "success": False,
                "claims": ["email=fail@example.com"],
            },
        },
    ]

    rows = list_auth_logs(client, days=7, namespace="tenant")
    assert len(rows) == 1
    assert rows[0]["uuid"] == "ok"


def test_probe_auth_logs_includes_failed_login() -> None:
    client = MagicMock()
    client.AuthenticationLog.list.return_value = [
        {
            "uuid": "fail",
            "meta": {"create_time": "2026-07-01T11:00:00Z"},
            "spec": {
                "uri": "/v1/auth/api-key",
                "success": False,
                "claims": ["email=fail@example.com"],
                "authorized_tenants": ["tenant-a"],
            },
        },
    ]

    from endorlabs.workflows.auth.authentication_log import probe_auth_logs

    rows = probe_auth_logs(client, namespace="tenant", days=7)
    assert len(rows) == 1
    assert rows[0]["success"] is False
    assert rows[0]["authorized_tenants"] == ["tenant-a"]


def test_count_logins_from_groups_aggregates_buckets() -> None:
    from endorlabs.workflows.auth.authentication_log import count_logins_from_groups

    bucket = GroupBucket(
        key=GROUP_KEY,
        parsed={"spec.claims": "[]"},
        data={"aggregation_count": {"count": 4}},
        count=0,
    )
    client = MagicMock()
    client.AuthenticationLog.list_groups.return_value = [bucket]
    client.AuthenticationLog.list.return_value = [
        {
            "meta": {"create_time": "2026-07-02T10:00:00Z"},
            "spec": {"claims": ["email=darcher@endor.ai"]},
        }
    ]

    activity = count_logins_from_groups(
        client,
        days=30,
        namespace="tenant",
        traverse=False,
    )
    assert len(activity) == 1
    row = activity[0]
    assert row.identity == "darcher@endor.ai"
    assert row.login_count == 4
    assert row.last_login == "2026-07-02T10:00:00Z"
    assert row.days == 30

    client.AuthenticationLog.list_groups.assert_called_once()
    group_kwargs = client.AuthenticationLog.list_groups.call_args.kwargs
    assert group_kwargs["namespace"] == "tenant"
    assert group_kwargs["paths"] == ["spec.claims"]
    assert "spec.success!=false" in group_kwargs["filter"]


def test_list_auth_logs_uses_tenant_list_path_defaults() -> None:
    client = MagicMock()
    client.AuthenticationLog.list.return_value = [
        {
            "uuid": "1",
            "meta": {"create_time": "2026-07-01T10:00:00Z"},
            "spec": {
                "uri": "/v1/auth/saml-callback",
                "success": True,
                "claims": ["email=alice@example.com"],
            },
        },
        {
            "uuid": "2",
            "meta": {"create_time": "2026-07-01T11:00:00Z"},
            "spec": {
                "uri": "/v1/auth/api-key",
                "success": True,
                "claims": ["email=bot@example.com"],
            },
        },
    ]

    rows = list_auth_logs(
        client,
        days=30,
        namespace="example-tenant",
        traverse=False,
    )
    assert len(rows) == 1
    assert rows[0]["claims"] == ["email=alice@example.com"]

    _, kwargs = client.AuthenticationLog.list.call_args
    assert kwargs["namespace"] == "example-tenant"
    assert kwargs["traverse"] is False
    assert "meta.create_time>=date(" in kwargs["filter"]
    assert "spec.success!=false" in kwargs["filter"]
    assert "tenant_meta.namespace" not in kwargs["filter"]
