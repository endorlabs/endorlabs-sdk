"""APIKey expiration audit helpers for tenant credential hygiene.

Composable layers:

1. **Normalize** — ``normalize_api_key_row`` turns list rows into uniform dicts.
2. **Classify** — ``classify_expiration`` maps ``spec.expiration_time`` to status.
3. **Fetch** — ``list_api_keys`` lists keys on a namespace path.
4. **Audit** — ``audit_api_key_expiry`` returns rows that are expired or expiring soon.

**Tenant scoping:** pass ``namespace=<tenant>`` on list calls. Use ``traverse=True``
(``--platform-wide`` in the skill script) when auditing child namespaces.

**Out of scope:** bearer ``ENDOR_TOKEN`` session expiry (``verify_auth`` /
``endor-auth check``); ``SCMCredential`` until the SDK facade ships.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any, Literal

from endorlabs.workflows.wire_access import (
    dict_str,
    model_to_dict,
    nested_dict,
    nested_str,
)

if TYPE_CHECKING:
    from endorlabs import Client

API_KEY_LIST_MASK = (
    "meta.name,meta.description,meta.create_time,"
    "tenant_meta.namespace,uuid,propagate,"
    "spec.expiration_time,spec.key,spec.issuing_user"
)

ExpiryStatus = Literal["expired", "expiring_soon", "ok", "unknown"]


@dataclass(frozen=True)
class CredentialExpiryRow:
    """One API key row in a credential-expiry audit report."""

    kind: str
    name: str
    namespace: str
    uuid: str
    key_id: str
    expiration_time: str
    status: ExpiryStatus
    days_until_expiry: int | None
    propagate: bool
    issuing_user: str

    def to_csv_row(self) -> dict[str, str]:
        """Return one CSV row dict using the skill column schema."""
        days = str(self.days_until_expiry) if self.days_until_expiry is not None else ""
        return {
            "kind": self.kind,
            "name": self.name,
            "namespace": self.namespace,
            "uuid": self.uuid,
            "key id": self.key_id,
            "expiration time": self.expiration_time,
            "status": self.status,
            "days until expiry": days,
            "propagate": "yes" if self.propagate else "no",
            "issuing user": self.issuing_user,
        }


def parse_expiration_time(
    value: str | datetime | None,
    *,
    now: datetime | None = None,  # noqa: ARG001
) -> datetime | None:
    """Parse ``spec.expiration_time`` from wire values."""
    if value is None:
        return None
    if isinstance(value, datetime):
        parsed = value
    else:
        text = str(value).strip()
        if not text:
            return None
        normalized = text.replace("Z", "+00:00")
        try:
            parsed = datetime.fromisoformat(normalized)
        except ValueError:
            return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def classify_expiration(
    expiration: datetime | None,
    *,
    within_days: int,
    now: datetime | None = None,
) -> tuple[ExpiryStatus, int | None]:
    """Classify an expiration timestamp relative to *now*."""
    anchor = now or datetime.now(UTC)
    if anchor.tzinfo is None:
        anchor = anchor.replace(tzinfo=UTC)
    else:
        anchor = anchor.astimezone(UTC)

    if expiration is None:
        return "unknown", None

    delta = expiration - anchor
    days = int(delta.total_seconds() // 86400)
    if delta.total_seconds() <= 0:
        return "expired", days
    if days <= within_days:
        return "expiring_soon", days
    return "ok", days


def issuing_user_label(row: dict[str, Any]) -> str:
    """Best-effort label for ``spec.issuing_user`` without secret fields."""
    user = nested_dict(row, "spec", "issuing_user")
    if not user:
        return ""
    meta = nested_dict(user, "meta")
    for key in ("name", "description"):
        label = dict_str(meta, key)
        if label:
            return label
    uuid = dict_str(user, "uuid")
    return uuid


def normalize_api_key_row(row: Any) -> dict[str, Any]:
    """Normalize an APIKey list row to a wire dict."""
    return model_to_dict(row)


def list_api_keys(
    client: Client,
    *,
    namespace: str | None = None,
    traverse: bool = False,
    max_pages: int | None = None,
    mask: str = API_KEY_LIST_MASK,
) -> list[dict[str, Any]]:
    """List APIKey rows for expiry auditing."""
    kwargs: dict[str, Any] = {
        "traverse": traverse,
        "mask": mask,
    }
    if namespace is not None:
        kwargs["namespace"] = namespace
    if max_pages is not None:
        kwargs["max_pages"] = max_pages

    rows = client.APIKey.list(**kwargs)
    return [normalize_api_key_row(row) for row in rows]


def build_credential_expiry_row(
    row: dict[str, Any],
    *,
    within_days: int,
    now: datetime | None = None,
) -> CredentialExpiryRow:
    """Build one :class:`CredentialExpiryRow` from a normalized APIKey wire row."""
    expiration_raw = nested_str(row, "spec", "expiration_time")
    expiration = parse_expiration_time(expiration_raw, now=now)
    status, days = classify_expiration(
        expiration,
        within_days=within_days,
        now=now,
    )
    return CredentialExpiryRow(
        kind="APIKey",
        name=nested_str(row, "meta", "name"),
        namespace=nested_str(row, "tenant_meta", "namespace"),
        uuid=dict_str(row, "uuid"),
        key_id=nested_str(row, "spec", "key"),
        expiration_time=expiration_raw,
        status=status,
        days_until_expiry=days,
        propagate=bool(row.get("propagate")),
        issuing_user=issuing_user_label(row),
    )


def audit_api_key_expiry(
    client: Client,
    *,
    namespace: str,
    within_days: int = 30,
    traverse: bool = False,
    max_pages: int | None = None,
    include_healthy: bool = False,
    now: datetime | None = None,
) -> list[CredentialExpiryRow]:
    """Return APIKey expiry rows for a tenant namespace path."""
    if within_days < 0:
        msg = "within_days must be >= 0"
        raise ValueError(msg)

    rows = list_api_keys(
        client,
        namespace=namespace,
        traverse=traverse,
        max_pages=max_pages,
    )
    audited = [
        build_credential_expiry_row(row, within_days=within_days, now=now)
        for row in rows
    ]

    def _status_rank(status: str) -> int:
        if status == "expired":
            return 0
        if status == "expiring_soon":
            return 1
        return 2

    audited.sort(
        key=lambda item: (
            _status_rank(item.status),
            item.days_until_expiry if item.days_until_expiry is not None else 999999,
            item.namespace,
            item.name,
        )
    )
    if include_healthy:
        return audited
    return [
        row for row in audited if row.status in {"expired", "expiring_soon", "unknown"}
    ]


def expiry_upper_bound_filter(
    within_days: int,
    *,
    now: datetime | None = None,
) -> str:
    """Optional server-side filter for keys expiring on or before *within_days*."""
    anchor = now or datetime.now(UTC)
    if anchor.tzinfo is None:
        anchor = anchor.replace(tzinfo=UTC)
    else:
        anchor = anchor.astimezone(UTC)
    upper = (anchor + timedelta(days=within_days)).date().isoformat()
    return f"spec.expiration_time<=date({upper})"
