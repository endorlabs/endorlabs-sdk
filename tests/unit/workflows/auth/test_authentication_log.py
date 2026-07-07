"""Unit tests for authentication log workflow helpers."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from unittest.mock import MagicMock

from endorlabs.operations.list_response import GroupBucket
from endorlabs.workflows.auth.authentication_log import (
    aggregate_login_activity,
    authentication_log_row_to_dict,
    build_authentication_log_filter,
    create_time_lower_bound_filter,
    extract_user_identifiers,
    fetch_authentication_logs,
    interactive_uri_filter,
    is_api_key_noise,
    is_sso_login_uri,
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


def test_build_authentication_log_filter_composes_interactive_login_filter() -> None:
    anchor = datetime(2026, 7, 7, 12, 0, 0, tzinfo=UTC)
    filt = build_authentication_log_filter(7, now=anchor)
    assert "meta.create_time>=date(" in filt
    assert "spec.success!=false" in filt
    assert interactive_uri_filter() in filt
    assert "tenant_meta.namespace" not in filt


def test_build_authentication_log_filter_can_disable_interactive_uri_filter() -> None:
    filt = build_authentication_log_filter(7, interactive_only=False)
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
    assert is_sso_login_uri("/v1/auth/saml-callback?tenant=cyera")
    assert not is_sso_login_uri("/v1/auth/api-key")


def test_authentication_log_row_to_dict_from_masked_dict() -> None:
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
    normalized = authentication_log_row_to_dict(row)
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


def test_aggregate_login_activity_groups_by_identity() -> None:
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
    activity = aggregate_login_activity(rows, days=7)
    assert len(activity) == 2
    alice = next(item for item in activity if item.identity == "alice@example.com")
    bob = next(item for item in activity if item.identity == "bob@example.com")
    assert alice.login_count == 2
    assert alice.last_login == "2026-07-02T10:00:00Z"
    assert bob.login_count == 1


def test_fetch_authentication_logs_uses_tenant_list_path_defaults() -> None:
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

    rows = fetch_authentication_logs(
        client,
        days=30,
        namespace="cyera",
        traverse=False,
    )
    assert len(rows) == 1
    assert rows[0]["claims"] == ["email=alice@example.com"]

    _, kwargs = client.AuthenticationLog.list.call_args
    assert kwargs["namespace"] == "cyera"
    assert kwargs["traverse"] is False
    assert "meta.create_time>=date(" in kwargs["filter"]
    assert "spec.success!=false" in kwargs["filter"]
    assert "tenant_meta.namespace" not in kwargs["filter"]
