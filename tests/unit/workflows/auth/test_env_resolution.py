"""Unit tests for auth env resolution helpers."""

from __future__ import annotations

from endorlabs.workflows.auth.env_resolution import (
    browser_method_from_auth_payload,
    browser_method_from_authentication_source,
    browser_method_from_user_identity,
    resolve_bearer_browser_method,
)


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


def test_browser_method_from_authentication_source_email_magic_link() -> None:
    assert browser_method_from_authentication_source("endor") == "email"
    assert browser_method_from_authentication_source("email") == "email"


def test_browser_method_from_authentication_source_sso_object_id() -> None:
    assert (
        browser_method_from_authentication_source("aaaaaaaaaaaaaaaaaaaaaaaa") == "sso"
    )


def test_browser_method_from_user_identity_email_magic_link() -> None:
    assert browser_method_from_user_identity("user@endor.ai@endor") == "email"


def test_browser_method_from_user_identity_sso_object_id() -> None:
    assert (
        browser_method_from_user_identity("tgowan@endor.ai@aaaaaaaaaaaaaaaaaaaaaaaa")
        == "sso"
    )


def test_browser_method_from_auth_payload_email_magic_link() -> None:
    assert (
        browser_method_from_auth_payload(
            {
                "authentication_source": "endor",
                "user": {
                    "meta": {"name": "user@endor.ai@endor"},
                    "spec": {"email": "user@endor.ai"},
                },
            }
        )
        == "email"
    )


def test_browser_method_from_auth_payload_sso_object_id() -> None:
    assert (
        browser_method_from_auth_payload(
            {
                "authentication_source": "aaaaaaaaaaaaaaaaaaaaaaaa",
                "user": {
                    "meta": {"name": "tgowan@endor.ai@aaaaaaaaaaaaaaaaaaaaaaaa"},
                    "spec": {"email": "tgowan@endor.ai"},
                },
            }
        )
        == "sso"
    )
