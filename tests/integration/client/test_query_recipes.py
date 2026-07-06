"""Live integration tests for Query facade recipes and validation."""

from __future__ import annotations

import pytest

from endorlabs.core.exceptions import ServerError
from endorlabs.query import (
    count_findings_by_category,
    count_pv_by_project,
    discover_topology,
    validate_sample,
)
from tests.conftest import TEST_MAX_PAGES_TRAVERSE
from tests.integration.client.conftest import require_first_project


def _sample_projects(client, *, limit: int = 3) -> list[object]:
    """Return up to ``limit`` projects with a leaf namespace for Query grouping."""
    try:
        projects = client.Project.list(
            traverse=True,
            max_pages=TEST_MAX_PAGES_TRAVERSE,
        )
    except ServerError as err:
        pytest.skip(f"Project list unavailable: {err}")
    with_ns = [
        p
        for p in projects
        if getattr(getattr(p, "tenant_meta", None), "namespace", None)
    ]
    if not with_ns:
        pytest.skip("No projects with leaf namespace in scope")
    return with_ns[:limit]


@pytest.mark.integration
class TestQueryRecipes:
    """Validate graph-join count recipes against live tenant data."""

    @pytest.fixture(autouse=True)
    def setup_client(self, facade_root_client) -> None:
        self.client = facade_root_client

    def test_query_facade_count_pv_by_project(self) -> None:
        projects = _sample_projects(self.client)
        try:
            counts = self.client.Query.count_pv_by_project(projects)
        except ServerError as err:
            pytest.skip(f"Query PV count unavailable: {err}")
        assert isinstance(counts, dict)
        for uid, value in counts.items():
            assert isinstance(uid, str)
            assert isinstance(value, int)
            assert value >= 0

    def test_query_module_count_findings_by_category(self) -> None:
        projects = _sample_projects(self.client)
        try:
            counts = count_findings_by_category(self.client, projects)
        except ServerError as err:
            pytest.skip(f"Query finding count unavailable: {err}")
        assert isinstance(counts, dict)
        for uid, categories in counts.items():
            assert isinstance(uid, str)
            assert isinstance(categories, dict)
            for label, value in categories.items():
                assert isinstance(label, str)
                assert isinstance(value, int)
                assert value >= 0

    def test_validate_sample_pv_matches_facade_count(self) -> None:
        projects = _sample_projects(self.client, limit=2)
        try:
            result = validate_sample(
                self.client,
                projects,
                recipe="pv",
                sample_size=2,
            )
        except ServerError as err:
            pytest.skip(f"Query validation unavailable: {err}")
        assert result.recipe == "pv"
        assert result.sample_size <= 2
        if not result.matched:
            pytest.fail(
                f"Query vs facade PV count mismatch: {result.to_dict()['mismatches']}"
            )

    def test_discover_topology_returns_shards(self, root_namespace: str) -> None:
        project = require_first_project(self.client)
        ns = getattr(getattr(project, "tenant_meta", None), "namespace", None)
        if not ns:
            pytest.skip("Project has no namespace for topology discovery")
        try:
            topology = discover_topology(self.client, root_namespace)
        except ServerError as err:
            pytest.skip(f"Topology discovery unavailable: {err}")
        assert topology.tenant == root_namespace
        assert topology.namespace_shards
        shard_ns = {s.namespace for s in topology.namespace_shards}
        assert ns in shard_ns

    def test_count_pv_by_project_module_entry(self) -> None:
        projects = _sample_projects(self.client, limit=1)
        try:
            counts = count_pv_by_project(self.client, projects)
        except ServerError as err:
            pytest.skip(f"count_pv_by_project unavailable: {err}")
        assert isinstance(counts, dict)
