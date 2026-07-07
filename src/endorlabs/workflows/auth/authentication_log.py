"""AuthenticationLog helpers for login counts and auth RCA.

Composable layers (build bottom-up):

1. **Filters** — ``auth_log_filter``, ``interactive_uri_filter``, claim helpers.
2. **Normalize** — ``normalize_auth_log`` turns list rows into uniform dicts.
3. **Fetch** — ``list_auth_logs`` (login-count defaults) or ``probe_auth_logs`` (RCA).
4. **Narrow / export** — ``filter_auth_logs_by_email``, ``auth_log_snapshot``.
5. **Aggregate** — ``count_logins_from_groups`` (default) or ``count_logins_from_rows``.

**Tenant scoping:** pass ``namespace=<tenant>`` on list calls with ``traverse=False``.
Do **not** filter ``tenant_meta.namespace`` in MQL — wire rows may show ``system`` but
are returned on the tenant list path; that filter usually yields zero rows.

**Recipes:** login-count → ``count_logins_from_groups``; auth RCA →
``probe_auth_logs`` → ``filter_auth_logs_by_email`` → ``auth_log_snapshot``;
custom → ``auth_log_filter`` + ``client.AuthenticationLog.list`` →
``normalize_auth_log``.
"""

from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any, cast

from endorlabs.operations.list_response import GroupBucket, group_bucket_count
from endorlabs.workflows.wire_access import dict_str, nested_dict

if TYPE_CHECKING:
    from endorlabs import Client

AUTHENTICATION_LOG_LIST_MASK = (
    "meta.create_time,spec.claims,spec.uri,spec.success,spec.remote_address"
)

AUTHENTICATION_LOG_INVESTIGATION_MASK = (
    "meta.create_time,spec.claims,spec.uri,spec.success,spec.remote_address,"
    "spec.authorized_tenants"
)

API_KEY_URI_FRAGMENTS = (
    "/auth/api-key",
    "issuing_user=",
)

SSO_URI_FRAGMENTS = (
    "auth/saml-callback",
    "auth/sso",
    "auth/google/callback",
    "auth/oidc",
)

# Server-side Matches filter for interactive human login callbacks (see API spec
# spec.uri and insider-threat catalog: google/saml/sso paths only).
INTERACTIVE_URI_REGEX = (
    r".*(/auth/google/callback|/auth/saml-callback|/auth/sso|/auth/oidc).*"
)


@dataclass(frozen=True)
class LoginActivityRow:
    """One identity row in a login-activity report.

    ``identity`` is the aggregation key from claims; ``user_identifiers`` holds
    all ``email=`` / ``user=`` / ``id=`` strings for that identity. Use
    :meth:`to_csv_row` for the skill CSV column schema.
    """

    identity: str
    user_identifiers: tuple[str, ...]
    last_login: str
    login_count: int
    days: int

    def to_csv_row(self) -> dict[str, str]:
        """Return one CSV row dict using the skill column schema."""
        count_column = f"login count in {self.days} days"
        return {
            "identity": self.identity,
            "user identifiers": "; ".join(self.user_identifiers),
            "last login": self.last_login,
            count_column: str(self.login_count),
        }


def parse_create_time(value: str | None) -> datetime | None:
    """Parse an API ``meta.create_time`` string into UTC."""
    if not value:
        return None
    normalized = value.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except (TypeError, ValueError):
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def create_time_lower_bound_filter(
    days: int,
    *,
    now: datetime | None = None,
) -> str:
    """Return an MQL lower-bound filter for ``meta.create_time``."""
    if days < 1:
        raise ValueError("days must be >= 1")
    anchor = now or datetime.now(tz=UTC)
    cutoff = anchor - timedelta(days=days)
    iso = cutoff.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    return f"meta.create_time>=date({iso})"


def interactive_uri_filter() -> str:
    """Return server-side filter for interactive SSO/OIDC callback URIs."""
    return f"spec.uri matches '{INTERACTIVE_URI_REGEX}'"


def auth_log_filter(
    days: int,
    *,
    successful_only: bool = True,
    interactive_only: bool = True,
    now: datetime | None = None,
) -> str:
    """Compose the MQL ``filter`` for AuthenticationLog list/group calls.

    Default parts: time lower bound, ``spec.success!=false`` (unset counts as
    success), and interactive SSO/OIDC URI match. Pair with ``namespace=<tenant>``
    on the list path — never add ``tenant_meta.namespace`` here.
    """
    parts = [create_time_lower_bound_filter(days, now=now)]
    if successful_only:
        # spec.success is often unset on successful callbacks; exclude explicit false.
        parts.append("spec.success!=false")
    if interactive_only:
        parts.append(interactive_uri_filter())
    return " and ".join(parts)


def normalize_auth_log(row: Any) -> dict[str, Any]:
    """Normalize a model or masked-dict AuthenticationLog row.

    Returns keys: ``uuid``, ``namespace`` (from ``tenant_meta``, display-only),
    ``created``, ``uri``, ``success``, ``claims``, ``remote_address``,
    ``authorized_tenants``. Downstream helpers expect this shape.
    """
    if isinstance(row, dict):
        row_dict = cast("dict[str, Any]", row)
        meta = nested_dict(row_dict, "meta")
        spec = nested_dict(row_dict, "spec")
        tenant_meta = nested_dict(row_dict, "tenant_meta")
        claims_raw = spec.get("claims")
        authorized_raw = spec.get("authorized_tenants")
        return {
            "uuid": row_dict.get("uuid"),
            "namespace": tenant_meta.get("namespace"),
            "created": meta.get("create_time") or meta.get("created"),
            "uri": dict_str(spec, "uri"),
            "success": spec.get("success"),
            "claims": [str(c) for c in cast("list[Any]", claims_raw)]
            if isinstance(claims_raw, list)
            else [],
            "remote_address": spec.get("remote_address"),
            "authorized_tenants": [str(t) for t in cast("list[Any]", authorized_raw)]
            if isinstance(authorized_raw, list)
            else [],
        }

    spec = getattr(row, "spec", None)
    meta = getattr(row, "meta", None)
    tenant_meta = getattr(row, "tenant_meta", None)
    created = None
    if meta is not None:
        created = getattr(meta, "create_time", None) or getattr(meta, "created", None)
    return {
        "uuid": getattr(row, "uuid", None),
        "namespace": getattr(tenant_meta, "namespace", None) if tenant_meta else None,
        "created": str(created or ""),
        "uri": str(getattr(spec, "uri", "") or "") if spec else "",
        "success": getattr(spec, "success", None) if spec else None,
        "claims": list(getattr(spec, "claims", []) or []) if spec else [],
        "remote_address": getattr(spec, "remote_address", None) if spec else None,
        "authorized_tenants": list(getattr(spec, "authorized_tenants", []) or [])
        if spec
        else [],
    }


def is_api_key_noise(uri: str) -> bool:
    """Return whether *uri* looks like API-key automation rather than user login."""
    lowered = (uri or "").lower()
    return any(fragment in lowered for fragment in API_KEY_URI_FRAGMENTS)


def is_sso_login_uri(uri: str) -> bool:
    """Return whether *uri* matches common interactive SSO/OIDC callback paths."""
    lowered = (uri or "").lower()
    return any(fragment in lowered for fragment in SSO_URI_FRAGMENTS)


def extract_user_identifiers(claims: list[str]) -> list[str]:
    """Collect stable user-facing identifiers from AuthenticationLog claims."""
    identifiers: list[str] = []
    seen: set[str] = set()
    for claim in claims:
        if not claim or "=" not in claim:
            continue
        key, _, value = claim.partition("=")
        key = key.strip().lower()
        value = value.strip()
        if not value:
            continue
        if key not in {"email", "user", "id"}:
            continue
        normalized = f"{key}={value}"
        if normalized in seen:
            continue
        seen.add(normalized)
        identifiers.append(normalized)
    return identifiers


def primary_identity(identifiers: list[str]) -> str:
    """Pick a stable aggregation key from extracted claim identifiers."""
    emails: list[str] = []
    for item in identifiers:
        _, _, value = item.partition("=")
        value = value.strip()
        if "@" in value:
            emails.append(value.lower())
    if emails:
        return sorted(emails)[0]

    for prefix in ("email=", "user=", "id="):
        for item in identifiers:
            if item.lower().startswith(prefix):
                return item.partition("=")[2].strip().lower() or item.lower()

    if identifiers:
        return identifiers[0].lower()
    return "(unknown)"


def _is_countable_login(
    row: dict[str, Any],
    *,
    successful_only: bool,
    exclude_api_key: bool,
    interactive_only: bool,
) -> bool:
    uri = str(row.get("uri") or "")
    if interactive_only and not is_sso_login_uri(uri):
        return False
    if exclude_api_key and is_api_key_noise(uri):
        return False
    return not (successful_only and row.get("success") is False)


def auth_log_snapshot(row: dict[str, Any]) -> dict[str, Any]:
    """Compact export dict for troubleshooting / SSO correlation.

    Keys: ``user``, ``uri``, ``authorized_tenants``, ``success``, ``created``.
    Input must be a :func:`normalize_auth_log` dict (or equivalent).
    """
    identifiers = extract_user_identifiers(list(row.get("claims") or []))
    return {
        "user": primary_identity(identifiers),
        "uri": str(row.get("uri") or ""),
        "authorized_tenants": list(row.get("authorized_tenants") or []),
        "success": row.get("success"),
        "created": row.get("created"),
    }


def filter_auth_logs_by_email(
    rows: list[dict[str, Any]],
    email: str,
) -> list[dict[str, Any]]:
    """Keep rows whose claims, derived identity, or URI mention *email*.

    Case-insensitive substring match. Empty *email* returns *rows* unchanged.
    """
    needle = email.strip().lower()
    if not needle:
        return rows

    matched: list[dict[str, Any]] = []
    for row in rows:
        uri = str(row.get("uri") or "").lower()
        if needle in uri:
            matched.append(row)
            continue
        claims_raw = row.get("claims")
        claims = (
            [str(claim) for claim in cast("list[Any]", claims_raw)]
            if isinstance(claims_raw, list)
            else []
        )
        if any(needle in claim.lower() for claim in claims):
            matched.append(row)
            continue
        identity = primary_identity(extract_user_identifiers(claims))
        if needle in identity.lower():
            matched.append(row)
    return matched


def list_auth_logs(
    client: Client,
    *,
    days: int = 90,
    namespace: str | None = None,
    traverse: bool = False,
    max_pages: int | None = None,
    successful_only: bool = True,
    interactive_only: bool = True,
    exclude_api_key: bool = True,
    concurrent: bool = False,
    mask: str | None = None,
) -> list[dict[str, Any]]:
    """List and normalize AuthenticationLog rows for the trailing window.

    Defaults match login-count: successful interactive logins, API-key URIs
    dropped client-side. Pass ``namespace=<tenant>`` — do not filter
    ``tenant_meta.namespace`` in MQL.

    For auth RCA (failures, api-key events, ``authorized_tenants``), use
    :func:`probe_auth_logs`. Aggregate via :func:`count_logins_from_rows` or
    prefer server-side :func:`count_logins_from_groups`.
    """
    filter_expr = auth_log_filter(
        days,
        successful_only=successful_only,
        interactive_only=interactive_only,
    )

    list_kwargs: dict[str, Any] = {
        "namespace": namespace,
        "traverse": traverse,
        "filter": filter_expr,
        "mask": mask or AUTHENTICATION_LOG_LIST_MASK,
        "concurrent": concurrent,
    }
    if max_pages is not None:
        list_kwargs["max_pages"] = max_pages

    raw_rows = client.AuthenticationLog.list(**list_kwargs)
    rows = [normalize_auth_log(item) for item in raw_rows]
    return [
        row
        for row in rows
        if _is_countable_login(
            row,
            successful_only=successful_only,
            exclude_api_key=exclude_api_key,
            interactive_only=interactive_only,
        )
    ]


def probe_auth_logs(
    client: Client,
    *,
    namespace: str,
    days: int = 30,
    traverse: bool = False,
    max_pages: int | None = 10,
    successful_only: bool = False,
    interactive_only: bool = False,
    exclude_api_key: bool = False,
    concurrent: bool = False,
) -> list[dict[str, Any]]:
    """Fetch normalized auth-log rows for SSO / login RCA.

    Preset over :func:`list_auth_logs`: broader defaults (includes failures and
    non-interactive URIs), investigation mask with ``authorized_tenants``, tenant
    list path (``namespace=<tenant>``, ``traverse=False``). Narrow with
    :func:`filter_auth_logs_by_email`; export with :func:`auth_log_snapshot`.
    """
    return list_auth_logs(
        client,
        days=days,
        namespace=namespace,
        traverse=traverse,
        max_pages=max_pages,
        successful_only=successful_only,
        interactive_only=interactive_only,
        exclude_api_key=exclude_api_key,
        concurrent=concurrent,
        mask=AUTHENTICATION_LOG_INVESTIGATION_MASK,
    )


def count_logins_from_rows(
    rows: list[dict[str, Any]],
    *,
    days: int,
) -> list[LoginActivityRow]:
    """Aggregate normalized rows by primary identity (client-side fallback).

    Use after :func:`list_auth_logs` when ``list_groups`` is unavailable or
    ``--list-rows`` parity is required. Prefer :func:`count_logins_from_groups`
    for large windows.
    """
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    identifier_map: dict[str, set[str]] = defaultdict(set)

    for row in rows:
        identifiers = extract_user_identifiers(list(row.get("claims") or []))
        identity = primary_identity(identifiers)
        grouped[identity].append(row)
        identifier_map[identity].update(identifiers or [identity])

    activity: list[LoginActivityRow] = []
    for identity, events in grouped.items():
        sorted_events = sorted(
            events,
            key=lambda item: str(item.get("created") or ""),
            reverse=True,
        )
        last_login = str(sorted_events[0].get("created") or "")
        activity.append(
            LoginActivityRow(
                identity=identity,
                user_identifiers=tuple(sorted(identifier_map[identity])),
                last_login=last_login,
                login_count=len(events),
                days=days,
            )
        )

    activity.sort(key=lambda item: (-item.login_count, item.identity.lower()))
    return activity


def parse_claims_from_group_bucket(bucket: GroupBucket) -> list[str]:
    """Parse ``spec.claims`` values from a grouped ``spec.claims`` bucket key."""
    try:
        payload = json.loads(bucket.key)
    except json.JSONDecodeError:
        return []
    if not isinstance(payload, list):
        return []
    for raw_entry in cast("list[Any]", payload):
        if not isinstance(raw_entry, dict):
            continue
        entry_dict = cast("dict[str, Any]", raw_entry)
        if entry_dict.get("key") != "spec.claims":
            continue
        value = entry_dict.get("value")
        if isinstance(value, list):
            return [str(claim) for claim in cast("list[Any]", value) if claim]
    return []


def fetch_last_logins_for_identities(
    client: Client,
    *,
    filter_expr: str,
    identities: set[str],
    namespace: str | None = None,
    traverse: bool = False,
    max_pages: int | None = None,
) -> dict[str, str]:
    """Fetch newest ``meta.create_time`` per identity.

    Uses one sorted-desc page when it covers all identities; otherwise scans
    unsorted rows (sorted pagination often 400s past page 1 on this resource).
    """
    if not identities:
        return {}

    last_login: dict[str, str] = {}
    sorted_page = client.AuthenticationLog.list(
        namespace=namespace,
        traverse=traverse,
        filter=filter_expr,
        mask="meta.create_time,spec.claims",
        sort_by="meta.create_time",
        desc=True,
        max_pages=1,
    )
    for item in sorted_page:
        row = normalize_auth_log(item)
        identity = primary_identity(
            extract_user_identifiers(list(row.get("claims") or []))
        )
        if identity in last_login:
            continue
        created = str(row.get("created") or "")
        if created:
            last_login[identity] = created

    if identities.issubset(last_login.keys()):
        return last_login

    best: dict[str, str] = {}
    scan_kwargs: dict[str, Any] = {
        "namespace": namespace,
        "traverse": traverse,
        "filter": filter_expr,
        "mask": "meta.create_time,spec.claims",
    }
    if max_pages is not None:
        scan_kwargs["max_pages"] = max_pages

    for item in client.AuthenticationLog.list_iter(**scan_kwargs):
        row = normalize_auth_log(item)
        identity = primary_identity(
            extract_user_identifiers(list(row.get("claims") or []))
        )
        if identity not in identities:
            continue
        created = str(row.get("created") or "")
        if not created:
            continue
        prior = best.get(identity)
        if prior is None or created > prior:
            best[identity] = created

    return best


def count_logins_from_groups(
    client: Client,
    *,
    days: int,
    namespace: str | None = None,
    traverse: bool = False,
    max_pages: int | None = None,
    successful_only: bool = True,
    interactive_only: bool = True,
    last_login_max_pages: int | None = None,
) -> list[LoginActivityRow]:
    """Aggregate login counts via server-side ``list_groups`` on ``spec.claims``.

    Default path for login-count skills. Applies :func:`auth_log_filter`, then
    fetches per-identity ``last login`` via a supplemental sorted list (see
    :func:`fetch_last_logins_for_identities`). Fallback:
    :func:`list_auth_logs` → :func:`count_logins_from_rows`.
    """
    filter_expr = auth_log_filter(
        days,
        successful_only=successful_only,
        interactive_only=interactive_only,
    )
    group_kwargs: dict[str, Any] = {
        "namespace": namespace,
        "traverse": traverse,
        "filter": filter_expr,
        "paths": ["spec.claims"],
    }
    if max_pages is not None:
        group_kwargs["max_pages"] = max_pages

    buckets = list(client.AuthenticationLog.list_groups(**group_kwargs))

    pending: list[tuple[str, tuple[str, ...], int]] = []
    identities: set[str] = set()
    for bucket in buckets:
        claims = parse_claims_from_group_bucket(bucket)
        identifiers = extract_user_identifiers(claims)
        identity = primary_identity(identifiers)
        count = group_bucket_count(bucket)
        if count <= 0:
            continue
        identities.add(identity)
        pending.append(
            (
                identity,
                tuple(sorted(identifiers or [identity])),
                count,
            )
        )

    last_login = fetch_last_logins_for_identities(
        client,
        filter_expr=filter_expr,
        identities=identities,
        traverse=traverse,
        namespace=namespace,
        max_pages=last_login_max_pages,
    )

    activity = [
        LoginActivityRow(
            identity=identity,
            user_identifiers=user_identifiers,
            last_login=last_login.get(identity, ""),
            login_count=count,
            days=days,
        )
        for identity, user_identifiers, count in pending
    ]
    activity.sort(key=lambda item: (-item.login_count, item.identity.lower()))
    return activity
