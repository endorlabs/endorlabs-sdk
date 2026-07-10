"""Unit tests for credential expiry workflow helpers."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock

from endorlabs.workflows.auth.credential_expiry import (
    CredentialExpiryRow,
    audit_api_key_expiry,
    build_credential_expiry_row,
    classify_expiration,
    expiry_upper_bound_filter,
)


def test_classify_expiration_marks_expired_and_soon() -> None:
    now = datetime(2026, 7, 8, 12, 0, 0, tzinfo=UTC)
    expired = datetime(2026, 7, 1, 12, 0, 0, tzinfo=UTC)
    soon = datetime(2026, 7, 20, 12, 0, 0, tzinfo=UTC)
    later = datetime(2026, 9, 1, 12, 0, 0, tzinfo=UTC)

    assert classify_expiration(expired, within_days=30, now=now) == ("expired", -7)
    assert classify_expiration(soon, within_days=30, now=now) == ("expiring_soon", 12)
    assert classify_expiration(later, within_days=30, now=now) == ("ok", 55)


def test_build_credential_expiry_row_from_wire_dict() -> None:
    now = datetime(2026, 7, 8, 12, 0, 0, tzinfo=UTC)
    row = {
        "uuid": "key-uuid",
        "propagate": True,
        "tenant_meta": {"namespace": "tenant.child"},
        "meta": {"name": "ci-readonly"},
        "spec": {
            "key": "key-id-123",
            "expiration_time": "2026-07-20T00:00:00Z",
            "issuing_user": {
                "uuid": "user-1",
                "meta": {"name": "automation@example.com"},
            },
        },
    }
    built = build_credential_expiry_row(row, within_days=30, now=now)
    assert built == CredentialExpiryRow(
        kind="APIKey",
        name="ci-readonly",
        namespace="tenant.child",
        uuid="key-uuid",
        key_id="key-id-123",
        expiration_time="2026-07-20T00:00:00Z",
        status="expiring_soon",
        days_until_expiry=11,
        propagate=True,
        issuing_user="automation@example.com",
    )


def test_audit_api_key_expiry_filters_healthy_rows() -> None:
    client = MagicMock()
    client.APIKey.list.return_value = [
        {
            "uuid": "expired",
            "tenant_meta": {"namespace": "tenant"},
            "meta": {"name": "old"},
            "spec": {"expiration_time": "2026-01-01T00:00:00Z", "key": "k1"},
        },
        {
            "uuid": "healthy",
            "tenant_meta": {"namespace": "tenant"},
            "meta": {"name": "fresh"},
            "spec": {"expiration_time": "2027-01-01T00:00:00Z", "key": "k2"},
        },
    ]
    now = datetime(2026, 7, 8, 12, 0, 0, tzinfo=UTC)
    rows = audit_api_key_expiry(
        client,
        namespace="tenant",
        within_days=30,
        now=now,
    )
    assert len(rows) == 1
    assert rows[0].uuid == "expired"
    client.APIKey.list.assert_called_once_with(
        traverse=False,
        mask=(
            "meta.name,meta.description,meta.create_time,"
            "tenant_meta.namespace,uuid,propagate,"
            "spec.expiration_time,spec.key,spec.issuing_user"
        ),
        namespace="tenant",
    )


def test_expiry_upper_bound_filter_uses_date_literal() -> None:
    now = datetime(2026, 7, 8, 12, 0, 0, tzinfo=UTC)
    filt = expiry_upper_bound_filter(30, now=now)
    assert filt == "spec.expiration_time<=date(2026-08-07)"
