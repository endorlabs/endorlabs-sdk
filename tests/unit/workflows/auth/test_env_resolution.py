"""Unit tests for auth env resolution helpers."""

from __future__ import annotations

from endorlabs.workflows.auth.env_resolution import (
    browser_method_from_auth_payload,
    browser_method_from_authentication_source,
    browser_method_from_user_identity,
    normalize_browser_auth_method,
    resolve_bearer_browser_method,
)


def test_browser_method_from_authentication_source_google() -> None:
    assert browser_method_from_authentication_source("google") == "google"
    assert browser_method_from_authentication_source("GoogleOAuth") == "google"


def test_browser_method_from_authentication_source_sso() -> None:
    assert browser_method_from_authentication_source("sso") == "sso"
    assert browser_method_from_authentication_source("saml-callback") == "sso"


def test_resolve_bearer_browser_method_prefers_explicit() -> None:
    assert (
        resolve_bearer_browser_method(
            explicit="google",
            authentication_source="sso",
        )
        == "google"
    )


def test_browser_method_from_user_identity_google() -> None:
    assert browser_method_from_user_identity("user@corp.com@google") == "google"


def test_browser_method_from_authentication_source_email_magic_link() -> None:
    assert browser_method_from_authentication_source("endor") == "email"
    assert browser_method_from_authentication_source("email") == "email"


def test_browser_method_from_authentication_source_sso_object_id() -> None:
    assert (
        browser_method_from_authentication_source("65d5495cd71c1bffbb149eb9") == "sso"
    )


def test_browser_method_from_user_identity_email_magic_link() -> None:
    assert browser_method_from_user_identity("timmy166@hotmail.com@endor") == "email"


def test_browser_method_from_user_identity_sso_object_id() -> None:
    assert (
        browser_method_from_user_identity("tgowan@endor.ai@65d5495cd71c1bffbb149eb9")
        == "sso"
    )


def test_browser_method_from_auth_payload_email_identity() -> None:
    assert (
        browser_method_from_auth_payload(
            {
                "authentication_source": "opaque-id",
                "user": {"spec": {"email": "tgowan@endor.ai@google"}},
            }
        )
        == "google"
    )


def test_browser_method_from_auth_payload_email_magic_link() -> None:
    assert (
        browser_method_from_auth_payload(
            {
                "authentication_source": "endor",
                "user": {
                    "meta": {"name": "timmy166@hotmail.com@endor"},
                    "spec": {"email": "timmy166@hotmail.com"},
                },
            }
        )
        == "email"
    )


def test_browser_method_from_auth_payload_sso_object_id() -> None:
    assert (
        browser_method_from_auth_payload(
            {
                "authentication_source": "65d5495cd71c1bffbb149eb9",
                "user": {
                    "meta": {"name": "tgowan@endor.ai@65d5495cd71c1bffbb149eb9"},
                    "spec": {"email": "tgowan@endor.ai"},
                },
            }
        )
        == "sso"
    )


def test_normalize_browser_auth_method_legacy_admin() -> None:
    assert normalize_browser_auth_method("admin") == "browser-auth"
    assert normalize_browser_auth_method("browser") == "browser-auth"
    assert normalize_browser_auth_method("browser-auth") == "browser-auth"
