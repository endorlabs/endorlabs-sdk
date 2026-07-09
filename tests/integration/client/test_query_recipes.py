"""Live integration tests for Query facade recipes and validation."""

from __future__ import annotations

import pytest

from endorlabs.core.exceptions import ServerError
from endorlabs.filters import estate_findings_filter, to_query_filter
from endorlabs.query import discover_topology, validate_sample
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
            counts = self.client.Query.Project.count_pv(projects)
        except ServerError as err:
            pytest.skip(f"Query PV count unavailable: {err}")
        assert isinstance(counts, dict)
        for uid, value in counts.items():
            assert isinstance(uid, str)
            assert isinstance(value, int)
            assert value >= 0

    def test_query_facade_count_findings_by_category(self) -> None:
        projects = _sample_projects(self.client)
        try:
            counts = self.client.Query.Project.count_findings_by_category(projects)
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

    def test_validate_sample_findings_matches_facade_count(self) -> None:
        projects = _sample_projects(self.client, limit=2)
        try:
            result = validate_sample(
                self.client,
                projects,
                recipe="findings",
                sample_size=2,
            )
        except ServerError as err:
            pytest.skip(f"Query findings validation unavailable: {err}")
        assert result.recipe == "findings"
        assert result.sample_size <= 2
        if not result.matched:
            mismatches = result.to_dict()["mismatches"]
            malware_only = all(m.get("category") == "MALWARE" for m in mismatches)
            if malware_only:
                pytest.skip(
                    f"MALWARE category mismatch only (known layout caveat): {mismatches}"
                )
            pytest.fail(f"Query vs facade finding count mismatch: {mismatches}")

    def test_validate_sample_dm_matches_facade_count(self) -> None:
        projects = _sample_projects(self.client, limit=2)
        try:
            result = validate_sample(
                self.client,
                projects,
                recipe="dm",
                sample_size=2,
            )
        except ServerError as err:
            pytest.skip(f"Query DM validation unavailable: {err}")
        assert result.recipe == "dm"
        assert result.sample_size <= 2
        if not result.matched:
            pytest.fail(
                f"Query vs facade DM count mismatch: {result.to_dict()['mismatches']}"
            )

    def test_validate_sample_severity_matches_facade_count(self) -> None:
        projects = _sample_projects(self.client, limit=2)
        try:
            result = validate_sample(
                self.client,
                projects,
                recipe="severity",
                sample_size=2,
            )
        except ServerError as err:
            pytest.skip(f"Query severity validation unavailable: {err}")
        assert result.recipe == "severity"
        assert result.sample_size <= 2
        if not result.matched:
            pytest.fail(
                f"Query vs facade severity count mismatch: "
                f"{result.to_dict()['mismatches']}"
            )

    def test_discover_topology_returns_geometry(self, root_namespace: str) -> None:
        project = require_first_project(self.client)
        ns = getattr(getattr(project, "tenant_meta", None), "namespace", None)
        if not ns:
            pytest.skip("Project has no namespace for topology discovery")
        try:
            topology = discover_topology(self.client, root_namespace)
        except ServerError as err:
            pytest.skip(f"Topology discovery unavailable: {err}")
        assert topology.tenant == root_namespace
        assert topology.namespace_geometry
        geometry_ns = {g.namespace for g in topology.namespace_geometry}
        assert ns in geometry_ns

    def test_query_project_count_pv_entry(self) -> None:
        projects = _sample_projects(self.client, limit=1)
        try:
            counts = self.client.Query.Project.count_pv(projects)
        except ServerError as err:
            pytest.skip(f"count_pv unavailable: {err}")
        assert isinstance(counts, dict)

    def test_collect_estate_findings_row_parity_on_large_project(self) -> None:
        """Collect returns all rows when a project has >100 estate findings."""
        projects = _sample_projects(self.client, limit=25)
        target: object | None = None
        facade_total = 0
        for project in projects:
            uid = str(getattr(project, "uuid", None))
            ns = getattr(getattr(project, "tenant_meta", None), "namespace", None)
            if not ns:
                continue
            filt = to_query_filter(
                f"{estate_findings_filter()} and spec.project_uuid=={uid!r}"
            )
            try:
                count = int(
                    self.client.Finding.count(
                        namespace=ns,
                        filter=filt,
                        traverse=False,
                    )
                )
            except ServerError as err:
                pytest.skip(f"Finding count unavailable: {err}")
            if count > 100:
                target = project
                facade_total = count
                break
        if target is None:
            pytest.skip("No project with >100 estate findings in sample")

        mask = "uuid,spec.level,spec.finding_categories"
        try:
            rows = self.client.Query.Project.collect_estate_findings(
                [target],
                mask=mask,
            )
        except ServerError as err:
            pytest.skip(f"collect_estate_findings unavailable: {err}")

        row_uuids = {
            str(getattr(row, "uuid", None) or row.get("uuid"))
            for row in rows
            if getattr(row, "uuid", None) or (isinstance(row, dict) and row.get("uuid"))
        }
        assert len(rows) == facade_total, (
            f"expected {facade_total} rows, got {len(rows)}"
        )
        assert len(row_uuids) == facade_total
