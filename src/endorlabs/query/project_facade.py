"""Project-scoped Query facade: recipes, collect, validate, discover."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from endorlabs.filters import CATEGORY_QUERY_REFS

from .execute import QueryExecutor
from .normalize import normalize_reference_rows
from .parse import (
    parse_project_multi_reference_counts,
    parse_project_reference_counts,
)
from .recipes import (
    DM_REFERENCE_KEY,
    ECOSYSTEMS,
    PV_REFERENCE_KEY,
    dm_count_spec,
    estate_findings_list_spec,
    finding_category_count_spec,
    finding_severity_count_spec,
    prf_ecosystem_count_spec,
    prf_findings_list_spec,
    pv_count_spec,
)
from .routing import OutputShape
from .scope import scopes_from_projects
from .topology import TopologySnapshot, discover_topology
from .validate import RecipeKind, ValidationResult, validate_sample

if TYPE_CHECKING:
    from endorlabs.api_client import APIClient

    from .spec import QuerySpec


class ProjectQueryFacade:
    """Project-root Query recipes and scope derivation."""

    def __init__(self, client: APIClient, query_facade: Any) -> None:
        super().__init__()
        self._client = client
        self._query = query_facade
        self._discovery_client: Any | None = None
        self._facade_cache: dict[str, Any] = {}

    def _facade_resource(self, attr_name: str) -> Any:
        cached = self._facade_cache.get(attr_name)
        if cached is not None:
            return cached
        from endorlabs.facade import FACADE_CLASS_BY_ATTR, ResourceRuntimeFacade
        from endorlabs.registry import RESOURCE_REGISTRY

        entry = next(e for e in RESOURCE_REGISTRY if e.attr_name == attr_name)
        facade_cls = FACADE_CLASS_BY_ATTR.get(attr_name, ResourceRuntimeFacade)
        default_ns = getattr(self._query, "default_namespace", None)
        facade = facade_cls(self._client, default_ns, entry)
        self._facade_cache[attr_name] = facade
        return facade

    def _client_for_facade_ops(self) -> Any:
        """Return ``Client`` or a minimal shim with registry facades for list/count."""
        if hasattr(self._client, "Project"):
            return self._client

        class _FacadeClient:
            pass

        shim = _FacadeClient()
        for name in (
            "Project",
            "PackageVersion",
            "Finding",
            "DependencyMetadata",
        ):
            setattr(shim, name, self._facade_resource(name))
        return shim

    def _client_for_validate(self) -> Any:
        """Facade ops shim plus ``Query`` for validate_sample / QueryExecutor."""
        ops = self._client_for_facade_ops()
        if hasattr(ops, "Query"):
            return ops

        class _ValidateClient:
            Query = self._query

            def __getattr__(self, name: str) -> Any:
                return getattr(ops, name)

        return _ValidateClient()

    def _executor(
        self,
        *,
        name_prefix: str = "endor-query",
        max_root_pages: int | None = None,
        max_reference_pages: int | None = None,
    ) -> QueryExecutor:
        return QueryExecutor(
            self._query,
            name_prefix=name_prefix,
            max_root_pages=max_root_pages,
            max_reference_pages=max_reference_pages,
        )

    def discover(
        self,
        namespace: str,
        *,
        traverse: bool = True,
        max_pages: int | None = None,
        exclude_sbom: bool = False,
    ) -> TopologySnapshot:
        """Discover project geometry via bounded ``Project.list``.

        Live, non-archived projects only — see ``discover_topology`` for
        the full scope note, including the blind spot around deleted
        projects whose UUID other resources (e.g. ``Finding``) may still
        reference.
        """
        return discover_topology(
            self._client_for_facade_ops(),
            namespace,
            traverse=traverse,
            max_pages=max_pages,
            exclude_sbom=exclude_sbom,
        )

    def validate_sample(
        self,
        projects: list[Any],
        *,
        recipe: RecipeKind = "pv",
        sample_size: int = 5,
    ) -> ValidationResult:
        """Compare Query recipe output to facade ``count()`` on a sample."""
        return validate_sample(
            self._client_for_validate(),
            projects,
            recipe=recipe,
            sample_size=sample_size,
        )

    def preflight_count(
        self,
        projects: list[Any],
        shape: OutputShape,
    ) -> int | None:
        """Return a tenant-wide count total for dashboard-style Query recipes."""
        if not projects:
            return 0
        try:
            if shape == OutputShape.COUNT_BY_PROJECT:
                return sum(self.count_pv(projects).values())
            if shape == OutputShape.FINDING_CATEGORY_COUNTS:
                counts = self.count_findings_by_category(projects)
                return sum(sum(cats.values()) for cats in counts.values())
        except Exception:
            return None
        return None

    def count_pv(
        self,
        projects: list[Any],
        *,
        name_prefix: str = "query-pv-counts",
    ) -> dict[str, int]:
        """Return ``{project_uuid: main_context_pv_count}``."""
        return self._executor(name_prefix=name_prefix).execute(
            pv_count_spec(),
            scopes=scopes_from_projects(projects),
            parse_page=lambda result: parse_project_reference_counts(
                result, PV_REFERENCE_KEY
            ),
        )

    def count_dm(
        self,
        projects: list[Any],
        *,
        name_prefix: str = "query-dm-counts",
    ) -> dict[str, int]:
        """Return ``{project_uuid: main_context_dm_count}``."""
        return self._executor(name_prefix=name_prefix).execute(
            dm_count_spec(),
            scopes=scopes_from_projects(projects),
            parse_page=lambda result: parse_project_reference_counts(
                result, DM_REFERENCE_KEY
            ),
        )

    def count_findings_by_category(
        self,
        projects: list[Any],
        *,
        name_prefix: str = "query-finding-counts",
    ) -> dict[str, dict[str, int]]:
        """Return ``{project_uuid: {category_label: count}}``."""
        ref_keys = list(CATEGORY_QUERY_REFS.values())
        label_by_ref = {value: key for key, value in CATEGORY_QUERY_REFS.items()}

        def _parse(result: Any) -> dict[str, dict[str, int]]:
            raw = parse_project_multi_reference_counts(result, ref_keys)
            return {
                pid: {label_by_ref[key]: count for key, count in counts.items()}
                for pid, counts in raw.items()
            }

        return self._executor(name_prefix=name_prefix).execute(
            finding_category_count_spec(),
            scopes=scopes_from_projects(projects),
            parse_page=_parse,
        )

    def count_findings_by_severity(
        self,
        projects: list[Any],
        *,
        name_prefix: str = "query-finding-severity",
    ) -> dict[str, dict[str, int]]:
        """Return ``{project_uuid: {severity_label: count}}`` for vuln findings."""
        from endorlabs.filters.finding_categories import SEVERITY_QUERY_REFS

        ref_keys = list(SEVERITY_QUERY_REFS.values())
        label_by_ref = {value: key for key, value in SEVERITY_QUERY_REFS.items()}

        def _parse(result: Any) -> dict[str, dict[str, int]]:
            raw = parse_project_multi_reference_counts(result, ref_keys)
            return {
                pid: {label_by_ref[key]: count for key, count in counts.items()}
                for pid, counts in raw.items()
            }

        return self._executor(name_prefix=name_prefix).execute(
            finding_severity_count_spec(),
            scopes=scopes_from_projects(projects),
            parse_page=_parse,
        )

    def count_prf_by_ecosystem(
        self,
        projects: list[Any],
        *,
        name_prefix: str = "query-prf-ecosystem",
    ) -> dict[str, int]:
        """Return ecosystem label → total PRF vuln count across projects."""
        ref_keys = [f"Prf{eco}Count" for eco in ECOSYSTEMS]

        def _parse(result: Any) -> dict[str, int]:
            raw = parse_project_multi_reference_counts(result, ref_keys)
            totals = {eco: 0 for eco in ECOSYSTEMS}
            for counts in raw.values():
                for eco in ECOSYSTEMS:
                    totals[eco] += counts.get(f"Prf{eco}Count", 0)
            return totals

        return self._executor(name_prefix=name_prefix).execute(
            prf_ecosystem_count_spec(),
            scopes=scopes_from_projects(projects),
            parse_page=_parse,
        )

    def collect(
        self,
        spec: QuerySpec,
        projects: list[Any],
        *,
        ref_keys: str | tuple[str, ...],
        normalize: bool = False,
        name_prefix: str = "endor-query-collect",
        max_root_pages: int | None = None,
        max_reference_pages: int | None = None,
    ) -> list[dict[str, Any]]:
        """Return flattened rows from nested list reference(s) across projects.

        Nested reference lists paginate via reference ``next_page_token`` on
        follow-up ``Query.create`` calls (not root ``page_token``).
        """
        keys = (ref_keys,) if isinstance(ref_keys, str) else ref_keys
        scopes = scopes_from_projects(projects)
        merged = self._executor(
            name_prefix=name_prefix,
            max_root_pages=max_root_pages,
            max_reference_pages=max_reference_pages,
        ).collect_reference_rows(
            spec,
            scopes=scopes,
            ref_keys=keys,
            max_reference_pages=max_reference_pages,
        )
        rows: list[dict[str, Any]] = []
        for items in merged.values():
            rows.extend(items)
        if normalize:
            return normalize_reference_rows(rows)
        return rows

    def collect_estate_findings(
        self,
        projects: list[Any],
        *,
        mask: str | None = None,
        max_root_pages: int | None = None,
        max_reference_pages: int | None = None,
    ) -> list[dict[str, Any]]:
        """Collect main-context SCA/vulnerability finding rows via Query join."""
        return self.collect(
            estate_findings_list_spec(mask=mask),
            projects,
            ref_keys="Finding",
            max_root_pages=max_root_pages,
            max_reference_pages=max_reference_pages,
        )

    def collect_prf_findings(
        self,
        projects: list[Any],
        *,
        mask: str | None = None,
        max_root_pages: int | None = None,
        max_reference_pages: int | None = None,
    ) -> list[dict[str, Any]]:
        """Collect PRF vulnerability finding rows via Query join."""
        ref_keys = tuple(f"Prf{eco}Findings" for eco in ECOSYSTEMS)
        return self.collect(
            prf_findings_list_spec(mask=mask),
            projects,
            ref_keys=ref_keys,
            max_root_pages=max_root_pages,
            max_reference_pages=max_reference_pages,
        )
