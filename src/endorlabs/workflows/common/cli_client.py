"""Shared argparse helpers for constructing ``Client`` from CLI auth flags.

Workflow CLIs stay non-interactive: refresh via ``endor-auth refresh``, then
pass env credentials or these override flags. Do not open a browser here.
"""

from __future__ import annotations

import argparse
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import endorlabs


def add_client_auth_arguments(parser: argparse.ArgumentParser) -> None:
    """Add ``--token`` / ``--api-key`` / ``--api-secret`` / ``--api`` flags.

    Mirrors env names in the errors-and-auth contract and endor-auth-setup skill:
    ``ENDOR_TOKEN``, ``ENDOR_API_CREDENTIALS_KEY``, ``ENDOR_API_CREDENTIALS_SECRET``,
    ``ENDOR_API``.
    """
    _ = parser.add_argument(
        "--token",
        default=None,
        help="Bearer token override (else ENDOR_TOKEN / env).",
    )
    _ = parser.add_argument(
        "--api-key",
        default=None,
        dest="api_key",
        help="API key override (else ENDOR_API_CREDENTIALS_KEY).",
    )
    _ = parser.add_argument(
        "--api-secret",
        default=None,
        dest="api_secret",
        help="API secret override (else ENDOR_API_CREDENTIALS_SECRET).",
    )
    _ = parser.add_argument(
        "--api",
        default=None,
        dest="api",
        help="API base URL override (else ENDOR_API).",
    )


def client_kwargs_from_args(args: argparse.Namespace) -> dict[str, Any]:
    """Map parsed auth flags to ``Client`` / ``APIClient`` constructor kwargs."""
    kwargs: dict[str, Any] = {}
    token = getattr(args, "token", None)
    if token:
        kwargs["token"] = str(token)
    api_key = getattr(args, "api_key", None)
    if api_key:
        kwargs["key"] = str(api_key)
    api_secret = getattr(args, "api_secret", None)
    if api_secret:
        kwargs["secret"] = str(api_secret)
    api = getattr(args, "api", None)
    if api:
        kwargs["base_url"] = str(api)
    return kwargs


def client_from_namespace_args(
    namespace: str,
    args: argparse.Namespace,
) -> endorlabs.Client:
    """Build ``Client(tenant=namespace, …)`` from shared auth CLI flags."""
    import endorlabs as _endorlabs

    return _endorlabs.Client(tenant=namespace, **client_kwargs_from_args(args))
