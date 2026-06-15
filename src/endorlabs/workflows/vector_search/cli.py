"""Vector store query CLI for agent workflows."""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path
from typing import Any

import endorlabs
from endorlabs.utils.logging_config import get_resource_logger
from endorlabs.utils.path_safety import safe_write_text
from endorlabs.workflows.projects.discovery import resolve_project_candidate
from endorlabs.workflows.vector_search.query import (
    list_tenant_vector_stores,
    probe_store_indexed_for_project,
    query_vector_store,
)

LOGGER = get_resource_logger(__name__)


def parse_vector_query_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse ``endor-vector-query`` arguments."""
    p = argparse.ArgumentParser(description="List or query tenant vector stores.")
    p.add_argument("--tenant", required=True, help="Client tenant (auth context).")
    p.add_argument(
        "--namespace",
        default="",
        help="Namespace for list/query (default: --tenant).",
    )
    p.add_argument(
        "--list-stores",
        action="store_true",
        help="List vector stores (optional --store-name filter).",
    )
    p.add_argument(
        "--store-name",
        default="",
        help="Substring filter on store meta.name.",
    )
    p.add_argument(
        "--store-uuid",
        default="",
        help="Vector store UUID for query/probe (required unless --list-stores).",
    )
    p.add_argument(
        "--query",
        default="",
        help="Natural-language query string.",
    )
    p.add_argument(
        "--metadata-repo",
        default="",
        help="metadata_filter.repo value for scoped query.",
    )
    p.add_argument(
        "--probe-project",
        default="",
        help="Project name/UUID: probe whether store is indexed for that project.",
    )
    p.add_argument(
        "--out",
        default="",
        help="Optional output JSON path (stdout if omitted).",
    )
    return p.parse_args(argv)


def _emit(payload: dict[str, Any], out: str) -> None:
    text = json.dumps(payload, indent=2, ensure_ascii=False)
    if out:
        out_path = Path(out).resolve()
        safe_write_text(out_path.parent, out_path, text)
        LOGGER.info("Wrote output: %s", out_path)
    else:
        print(text)


def run_vector_query_main(argv: list[str] | None = None) -> int:
    """CLI entry for vector store list/query/probe."""
    args = parse_vector_query_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    ns = (args.namespace or args.tenant).strip()

    client = endorlabs.Client(tenant=args.tenant)
    try:
        if args.list_stores:
            stores = list_tenant_vector_stores(
                client,
                namespace=ns,
                name_substring=args.store_name,
            )
            payload: dict[str, Any] = {
                "stores_total": len(stores),
                "stores": [
                    {
                        "uuid": vs.uuid,
                        "name": vs.meta.name if vs.meta else None,
                        "namespace": vs.namespace,
                    }
                    for vs in stores
                ],
            }
            _emit(payload, args.out)
            return 0

        if not args.store_uuid:
            LOGGER.error("--store-uuid is required unless --list-stores is set.")
            return 2

        store = client.VectorStore.get(args.store_uuid, namespace=ns)

        if args.probe_project:
            proj = resolve_project_candidate(client, args.probe_project, namespace=ns)
            project_name = proj.meta.name if proj.meta and proj.meta.name else proj.uuid
            payload = probe_store_indexed_for_project(client, store, project_name)
            payload["project_meta_name"] = project_name
            _emit(payload, args.out)
            return 0

        if not args.query:
            LOGGER.error("--query is required for vector store query.")
            return 2

        metadata_filter = {"repo": args.metadata_repo} if args.metadata_repo else None
        result = query_vector_store(
            client,
            store,
            args.query,
            metadata_filter=metadata_filter,
        )
        spec = getattr(result, "spec", None)
        documents = getattr(spec, "documents", None) if spec else None
        payload = {
            "store_uuid": store.uuid,
            "query": args.query,
            "metadata_filter": metadata_filter,
            "documents_total": len(documents or []),
            "documents": documents or [],
        }
        _emit(payload, args.out)
        return 0
    finally:
        client.close()


def main() -> int:
    """``endor-vector-query`` entrypoint."""
    return run_vector_query_main()


if __name__ == "__main__":
    raise SystemExit(main())
