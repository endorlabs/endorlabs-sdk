"""Integration tests for live call-graph path search."""

from __future__ import annotations

import os

import pytest

import endorlabs
from endorlabs.workflows.callgraph.path_cli import run_path_search
from endorlabs.workflows.callgraph.resolve import (
    build_callgraph_pv_inventory,
    list_package_versions_for_project,
    order_pvs_for_callgraph,
    resolve_package_version_with_callgraph,
)
from endorlabs.workflows.projects.discovery import resolve_project_candidate
from tests.conftest import CANONICAL_SDK_REPO_URL


@pytest.mark.integration
class TestCallgraphPath:
    """Validate path search against a real tenant project when available."""

    @pytest.fixture(autouse=True)
    def setup_fast(self, api_client, namespace) -> None:
        self.client = endorlabs.Client(tenant=namespace, api_client=api_client)
        self.namespace = namespace

    def test_path_get_to_httpx_request_on_endorlabs_sdk(self) -> None:
        """Multi-hop path from APIClient.get to httpx Client.request when CG exists."""
        repo_url = os.getenv("TEST_REPO_URL", CANONICAL_SDK_REPO_URL)
        try:
            proj = resolve_project_candidate(
                self.client,
                repo_url,
                namespace=self.namespace,
                traverse=True,
                max_pages=1,
            )
        except ValueError:
            pytest.skip(f"No project matched repo URL: {repo_url}")

        project_ns = (
            proj.tenant_meta.namespace
            if proj.tenant_meta and proj.tenant_meta.namespace
            else self.namespace
        )
        pvs = list_package_versions_for_project(
            self.client,
            proj,
            namespace=project_ns,
            max_pages=10,
            page_size=100,
        )
        inventory = build_callgraph_pv_inventory(proj, pvs, namespace=project_ns)
        if inventory["call_graph_available_count"] == 0:
            pytest.skip(inventory["message"])

        ordered = order_pvs_for_callgraph(pvs)
        assert ordered, "inventory promised call_graph_available PVs"

        resolved = resolve_package_version_with_callgraph(
            self.client,
            proj,
            namespace=project_ns,
            max_pages=10,
            page_size=100,
            inventory_out=inventory,
        )
        if resolved is None:
            pytest.skip(inventory.get("message", "decode failed for all candidates"))

        payload = run_path_search(
            self.client,
            namespace=project_ns,
            project=proj,
            from_patterns=["APIClient", "get"],
            to_patterns=["Client.request"],
            max_depth=6,
            max_pages=10,
            page_size=100,
            max_attempts=None,
        )
        assert payload["status"] == "success", payload.get("message")
        assert payload["path_found"] is True
        assert payload["paths"]
        hops = payload["paths"][0]
        assert len(hops) >= 2
        assert "get" in hops[0]["uri"].lower() or "APIClient" in hops[0]["uri"]
