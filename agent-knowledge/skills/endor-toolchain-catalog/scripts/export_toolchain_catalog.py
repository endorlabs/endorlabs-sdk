"""Export SupportedToolChainVersion catalog to ScanProfile-shaped CSV.

The resource is x-internal (no Client facade). Transport uses
``Client._client.get_all`` like AgentHookEvent list helpers.

Requires privileged read for the default ``system`` namespace (employee SSO
via ``endor-admin``). Tenant API keys typically receive 403.
"""

from __future__ import annotations

import argparse
import csv
import sys
from collections.abc import Iterable, Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, TextIO, cast

from endorlabs.context.paths import flat_task_dir
from endorlabs.workflows.common.cli_client import (
    add_client_auth_arguments,
    client_from_namespace_args,
)
from endorlabs.workflows.wire_access import as_dict, nested_dict

if TYPE_CHECKING:
    from endorlabs.client_surface import Client

_RESOURCE_PATH = "supported-toolchain-versions"
DEFAULT_NAMESPACE = "system"

CSV_COLUMNS: tuple[str, ...] = (
    "os",
    "arch",
    "ecosystem",
    "name",
    "relative_tool_chain_path",
    "sha256_sum",
    "url",
)


def _api_transport(client: Client) -> Any:
    # No SupportedToolChainVersion facade — raw list transport only.
    api = client._client
    if api is None:
        raise RuntimeError("Client has no API transport (closed?)")
    return api


def _wire_str(value: Any) -> str:
    """Normalize wire scalars (plain str or ``{\"value\": …}`` wrappers)."""
    if value is None:
        return ""
    if isinstance(value, Mapping):
        inner = value.get("value")
        if inner is None:
            return ""
        return str(inner)
    return str(value)


def _version_blob(spec: Mapping[str, Any]) -> dict[str, Any]:
    """Return ``ToolChainVersion`` dict from ``spec.version`` nesting."""
    supported = as_dict(spec.get("version"))
    if not supported:
        return {}
    inner = as_dict(supported.get("version"))
    return inner or supported


def flatten_catalog_rows(
    objects: Iterable[Mapping[str, Any]],
) -> list[dict[str, str]]:
    """Flatten API objects to one CSV row per download URL.

    Columns match ScanProfile ``V1ToolChainVersion`` plus placement keys.
    Empty ``urls`` still yields one row with blank ``url``.
    """
    rows: list[dict[str, str]] = []
    for obj in objects:
        spec = nested_dict(dict(obj), "spec")
        if not spec:
            continue
        version = _version_blob(spec)
        base = {
            "os": _wire_str(spec.get("os")),
            "arch": _wire_str(spec.get("arch")),
            "ecosystem": _wire_str(spec.get("toolchain")),
            "name": _wire_str(version.get("name")),
            "relative_tool_chain_path": _wire_str(
                version.get("relative_tool_chain_path")
            ),
            "sha256_sum": _wire_str(version.get("sha256_sum")),
        }
        urls_raw = version.get("urls")
        urls: list[str]
        if isinstance(urls_raw, Sequence) and not isinstance(urls_raw, (str, bytes)):
            urls = [_wire_str(u) for u in urls_raw if _wire_str(u)]
        else:
            urls = []
        if not urls:
            rows.append({**base, "url": ""})
            continue
        for url in urls:
            rows.append({**base, "url": url})
    return rows


def list_supported_toolchain_versions(
    client: Client,
    *,
    namespace: str = DEFAULT_NAMESPACE,
    filter_expr: str | None = None,
) -> list[dict[str, Any]]:
    """Paginate SupportedToolChainVersion as plain dicts."""
    api = _api_transport(client)
    url = f"v1/namespaces/{namespace}/{_RESOURCE_PATH}"
    params: dict[str, Any] = {}
    if filter_expr:
        params["list_parameters.filter"] = filter_expr
    out: list[dict[str, Any]] = []
    for row in api.get_all(url, params=params):
        if isinstance(row, dict):
            out.append(cast("dict[str, Any]", row))
            continue
        dump = getattr(row, "model_dump", None)
        if callable(dump):
            data = dump(mode="json", exclude_none=False)
            if isinstance(data, dict):
                out.append(cast("dict[str, Any]", data))
                continue
        raise TypeError(f"Unsupported catalog row type: {type(row)!r}")
    return out


def write_csv(
    rows: Sequence[Mapping[str, str]],
    dest: Path | TextIO,
    *,
    columns: Sequence[str] = CSV_COLUMNS,
) -> int:
    """Write CSV with header; return row count (excluding header)."""
    if isinstance(dest, Path):
        dest.parent.mkdir(parents=True, exist_ok=True)
        with dest.open("w", encoding="utf-8", newline="") as fh:
            return write_csv(rows, fh, columns=columns)

    writer = csv.DictWriter(dest, fieldnames=list(columns), extrasaction="ignore")
    writer.writeheader()
    for row in rows:
        writer.writerow({col: row.get(col, "") for col in columns})
    return len(rows)


def default_output_path() -> Path:
    """``.endorlabs/tasks/inventory/toolchain-catalog-<UTC>.csv``."""
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    return flat_task_dir("inventory") / f"toolchain-catalog-{stamp}.csv"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Export SupportedToolChainVersion catalog to CSV "
            "(ScanProfile ToolChainVersion fields only)."
        ),
    )
    _ = parser.add_argument(
        "-n",
        "--namespace",
        default=DEFAULT_NAMESPACE,
        help=f"Catalog namespace (default: {DEFAULT_NAMESPACE}).",
    )
    _ = parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help=(
            "Output CSV path (default: "
            ".endorlabs/tasks/inventory/toolchain-catalog-<UTC>.csv)."
        ),
    )
    _ = parser.add_argument(
        "--filter",
        default=None,
        dest="filter_expr",
        help="Optional list_parameters.filter (MQL).",
    )
    add_client_auth_arguments(parser)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    namespace = str(args.namespace).strip() or DEFAULT_NAMESPACE
    output: Path = args.output if args.output is not None else default_output_path()

    client = client_from_namespace_args(namespace, args)
    try:
        objects = list_supported_toolchain_versions(
            client,
            namespace=namespace,
            filter_expr=args.filter_expr,
        )
        rows = flatten_catalog_rows(objects)
        count = write_csv(rows, output)
    finally:
        client.close()

    print(f"Wrote {count} row(s) to {output}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
