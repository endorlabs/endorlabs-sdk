"""Console entrypoint: ``endor-auth check`` and ``endor-auth refresh``."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from endorlabs.auth_server import OAUTH_CALLBACK_PORT_COUNT, OAUTH_CALLBACK_PORT_START

from .session import (
    BrowserAuthMethod,
    redact_sensitive_text,
    refresh_token_to_dotenv,
    resolve_api_environment,
    resolve_sso_tenant,
    verify_auth,
)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Probe, verify, or refresh Endor Labs SDK authentication.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    check = subparsers.add_parser(
        "check",
        help="Probe env keys, endorctl, and Client().whoami() (no secret output).",
    )
    _ = check.add_argument(
        "--tenant",
        default=None,
        help="Optional tenant namespace for Client(tenant=...).",
    )
    _ = check.add_argument(
        "--json",
        action="store_true",
        help="Print structured JSON summary.",
    )

    refresh = subparsers.add_parser(
        "refresh",
        help="Interactive browser OAuth; upsert ENDOR_TOKEN in a .env file.",
    )
    _ = refresh.add_argument(
        "--env-file",
        type=Path,
        default=Path(".env"),
        help="Dotenv path to create or update (default: .env).",
    )
    _ = refresh.add_argument(
        "--method",
        choices=["sso", "google", "github", "gitlab", "email"],
        default="sso",
        help="Browser auth provider (default: sso).",
    )
    _ = refresh.add_argument(
        "-n",
        "--namespace",
        default=None,
        help="Tenant namespace for SSO (root segment used). Fallback: ENDOR_NAMESPACE.",
    )
    _ = refresh.add_argument(
        "--email",
        default=None,
        help="Email address when --method=email.",
    )
    _ = refresh.add_argument(
        "--environment",
        default=None,
        help="API host segment (default: from ENDOR_API or endorlabs.com).",
    )
    _ = refresh.add_argument(
        "--timeout",
        type=int,
        default=120,
        help="Seconds to wait for OAuth callback (default: 120).",
    )
    return parser


def _run_check(args: argparse.Namespace) -> int:
    result = verify_auth(args.tenant)
    if args.json:
        print(result.to_json())
    else:
        print(f"status: {result.status}")
        env = result.environment
        print(
            "environment:",
            f"token={'yes' if env.has_bearer_token else 'no'},",
            f"api_key_pair={'yes' if env.has_api_key_pair else 'no'},",
            f"dual_mode={'yes' if env.dual_mode_conflict else 'no'}",
        )
        ctl = result.endorctl
        print(
            "endorctl:",
            f"on_path={'yes' if ctl.on_path else 'no'}",
            f"version={ctl.version or 'n/a'}",
            f"config={'yes' if ctl.config_exists else 'no'}",
        )
        if result.whoami and result.whoami.identity:
            print(f"whoami: {result.whoami.identity}")
            if result.whoami.expires_in_seconds is not None:
                print(f"expires_in_seconds: {result.whoami.expires_in_seconds:.0f}")
        if result.error:
            print(f"error: {redact_sensitive_text(result.error)}", file=sys.stderr)
        if result.next_steps:
            print("\nnext_steps:")
            for step in result.next_steps:
                print(f"  - {step}")
    if result.status == "ready":
        return 0
    return 1


def _run_refresh(args: argparse.Namespace) -> int:
    method: BrowserAuthMethod = args.method
    env_file = Path(args.env_file)
    environment = args.environment or resolve_api_environment(env_file)

    if method == "sso":
        tenant = resolve_sso_tenant(namespace=args.namespace, env_file=env_file)
        port_range = (
            f"localhost:{OAUTH_CALLBACK_PORT_START}-"
            f"{OAUTH_CALLBACK_PORT_START + OAUTH_CALLBACK_PORT_COUNT - 1}"
        )
        if tenant:
            print(
                f"Opening browser for tenant SSO (tenant={tenant}). "
                f"Waiting for callback on {port_range}...",
                file=sys.stderr,
            )
        else:
            print(
                f"Opening browser for tenant SSO. "
                f"Waiting for callback on {port_range}...",
                file=sys.stderr,
            )
    else:
        port_range = (
            f"localhost:{OAUTH_CALLBACK_PORT_START}-"
            f"{OAUTH_CALLBACK_PORT_START + OAUTH_CALLBACK_PORT_COUNT - 1}"
        )
        print(
            f"Opening browser for {method} authentication. "
            f"Waiting for callback on {port_range}...",
            file=sys.stderr,
        )

    try:
        updated = refresh_token_to_dotenv(
            env_file,
            method=method,
            namespace=args.namespace,
            environment=environment,
            timeout=args.timeout,
            email=args.email,
        )
    except (ValueError, RuntimeError) as exc:
        print(redact_sensitive_text(str(exc)) or str(exc), file=sys.stderr)
        return 1

    print(f"Updated {updated} (ENDOR_TOKEN set)", file=sys.stderr)
    return 0


def main(argv: list[str] | None = None) -> int:
    """Dispatch ``endor-auth`` subcommands."""
    parser = _build_parser()
    args = parser.parse_args(argv)
    if args.command == "check":
        return _run_check(args)
    if args.command == "refresh":
        return _run_refresh(args)
    parser.error(f"unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
