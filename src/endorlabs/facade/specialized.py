"""Resource-specific facade subclasses and custom facades."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast, override

from ..core.exceptions import RouteNotApplicableError
from ..utils.namespace import resolve_namespace_for_resource
from .runtime import ResourceRuntimeFacade

if TYPE_CHECKING:
    from ..api_client import APIClient
    from ..core.filter import FilterExpression
    from ..operations.routes import RouteResult


class ScanResultFacade(ResourceRuntimeFacade[Any]):
    """ScanResult facade with log-line fetch sugar."""

    def get_logs(
        self,
        scan_result: Any,
        *,
        namespace: str | None = None,
        max_entries: int = 100,
        log_levels: list[Any] | None = None,
        start_time: str | None = None,
        end_time: str | None = None,
        newest_first: bool | None = None,
    ) -> list[Any]:
        """Fetch log messages for a scan (ScanLogRequest API under the hood).

        Args:
            scan_result: ``ScanResult`` model or scan UUID string.
            namespace: Target namespace; defaults to scan resource namespace
                or client tenant.
            max_entries: Max log entries (default 100).
            log_levels: Filter by level (``ScanLogLevel``); None = all.
            start_time: Logs after (ISO 8601).
            end_time: Logs before (ISO 8601).
            newest_first: True = newest first; False/None = chronological.

        Returns:
            ``ScanLogRequestLogMessage`` list; empty if none match.
        """
        from ..resources.scan_log_request import get_scan_result_logs

        scan_uuid = getattr(scan_result, "uuid", None) or scan_result
        if not isinstance(scan_uuid, str) or not scan_uuid:
            raise ValueError("scan_result must be a ScanResult model or UUID string")
        if namespace is not None:
            ns = self._ns(namespace)
        elif hasattr(scan_result, "tenant_meta"):
            ns = self._ns(
                resolve_namespace_for_resource(scan_result, self._default_namespace)
            )
        else:
            ns = self._ns(None)
        result = get_scan_result_logs(
            self._client,
            ns,
            scan_uuid,
            max_entries=max_entries,
            log_levels=log_levels,
            start_time=start_time,
            end_time=end_time,
            newest_first=newest_first,
        )
        return result if result is not None else []

    def list_by_project(
        self,
        project: Any,
        *,
        namespace: str | None = None,
        limit: int = 0,
        status_filter: str | None = None,
        **kwargs: Any,
    ) -> list[Any]:
        """List scan results for a project (accessor ``project.scan_results``).

        Preset for troubleshooting workflows: newest-first, ``max_pages=1`` by
        default, optional ``limit`` (maps to ``page_size``) and client-side
        ``status_filter``.
        """
        if namespace is not None:
            kwargs = {**kwargs, "namespace": namespace}
        if limit > 0 and "page_size" not in kwargs:
            kwargs = {**kwargs, "page_size": limit}
        if "sort_by" not in kwargs:
            kwargs = {**kwargs, "sort_by": "meta.create_time", "desc": True}
        if "max_pages" not in kwargs:
            kwargs = {**kwargs, "max_pages": 1}
        result = self._execute_route("project.scan_results", source=project, **kwargs)
        rows = result.values or []
        if status_filter:
            filtered: list[Any] = []
            for item in rows:
                spec = getattr(item, "spec", None)
                status = getattr(spec, "status", None) if spec is not None else None
                if status is None and isinstance(item, dict):
                    spec_raw = cast("dict[str, Any]", item).get("spec")
                    if isinstance(spec_raw, dict):
                        status = cast("dict[str, Any]", spec_raw).get("status")
                if str(status) == status_filter:
                    filtered.append(item)
            return filtered[:limit] if limit > 0 else filtered
        if limit > 0:
            return rows[:limit]
        return rows


class ProjectFacade(ResourceRuntimeFacade[Any]):
    """Project facade with search-by-name discovery."""

    def is_sbom(self, project: Any) -> bool:
        """Return whether *project* is an SBOM import row (``spec.sbom`` set)."""
        from ..resources.project import is_sbom_project_row

        return is_sbom_project_row(project)

    def is_app(self, project: Any) -> bool:
        """Return whether *project* was registered via an SCM app installation.

        Uses ``spec.git.external_installation_id``. For per-scan execution
        environment, see ScanResult ``spec.environment.config.RunBySystem``.
        """
        from ..resources.project import is_app_project_row

        return is_app_project_row(project)

    def is_cli(self, project: Any) -> bool:
        """Return whether *project* was registered for CLI scanning (no app id).

        Exclude SBOM rows with :meth:`is_sbom` before classifying inventory.
        """
        from ..resources.project import is_cli_project_row

        return is_cli_project_row(project)

    def search_by_name(
        self,
        query: str,
        *,
        namespace: str | None = None,
        traverse: bool = True,
        warnings_out: list[str] | None = None,
        **list_kwargs: Any,
    ) -> list[Any]:
        """Search projects by case-insensitive substring on ``meta.name`` or UUID.

        Returns a bounded ``list`` (not a single object). Use ``get(uuid)`` when
        the UUID is known; disambiguate when multiple rows match.
        """
        from .search import search_substring_on_fields

        return search_substring_on_fields(
            self,
            query=query,
            field_paths=("meta.name",),
            namespace=self._ns(namespace) if namespace is not None else None,
            traverse=traverse,
            warnings_out=warnings_out,
            uuid_also=True,
            **list_kwargs,
        )


class VectorStoreFacade(ResourceRuntimeFacade[Any]):
    """VectorStore facade with search-by-name discovery."""

    def search_by_name(
        self,
        query: str,
        *,
        namespace: str | None = None,
        traverse: bool = False,
        warnings_out: list[str] | None = None,
        **list_kwargs: Any,
    ) -> list[Any]:
        """Search vector stores by case-insensitive substring on ``meta.name``.

        Returns a bounded ``list`` (not a single object). Use ``get(uuid)`` when
        the UUID is known; disambiguate when multiple rows match.
        """
        from .search import search_substring_on_fields

        return search_substring_on_fields(
            self,
            query=query,
            field_paths=("meta.name",),
            namespace=self._ns(namespace) if namespace is not None else None,
            traverse=traverse,
            warnings_out=warnings_out,
            **list_kwargs,
        )


class AuthorizationPolicyFacade(ResourceRuntimeFacade[Any]):
    """AuthorizationPolicy facade with claim-aware search."""

    def search_by_claims(
        self,
        query: str,
        *,
        namespace: str | None = None,
        traverse: bool = True,
        warnings_out: list[str] | None = None,
        **list_kwargs: Any,
    ) -> list[Any]:
        """Search policies by name, clause text, and target namespace fields.

        Returns a bounded ``list`` (not a single object). Use ``get(uuid)`` when
        the UUID is known; disambiguate when multiple rows match.
        """
        from .search import search_policy_by_claims

        return search_policy_by_claims(
            self,
            query=query,
            namespace=self._ns(namespace) if namespace is not None else None,
            traverse=traverse,
            warnings_out=warnings_out,
            **list_kwargs,
        )


class VulnerabilityFacade(ResourceRuntimeFacade[Any]):
    """Vulnerability (OSS catalog) facade with alias search."""

    def search_by_vuln_alias(
        self,
        query: str,
        *,
        namespace: str | None = None,
        traverse: bool = False,
        warnings_out: list[str] | None = None,
        **list_kwargs: Any,
    ) -> list[Any]:
        """Search OSS vulnerabilities by alias or name substring.

        Returns a bounded ``list`` (not a single object). Use ``get(uuid)`` when
        the UUID is known; disambiguate when multiple rows match.
        """
        from .search import search_substring_on_fields

        return search_substring_on_fields(
            self,
            query=query,
            field_paths=("meta.name", "spec.aliases"),
            namespace=self._ns(namespace) if namespace is not None else None,
            traverse=traverse,
            warnings_out=warnings_out,
            uuid_also=True,
            **list_kwargs,
        )


class PackageVersionFacade(ResourceRuntimeFacade[Any]):
    """PackageVersion facade with generated relationship accessors."""

    def list_by_project(
        self,
        project: Any,
        *,
        filter: str | FilterExpression | None = None,
        **kwargs: Any,
    ) -> list[Any]:
        """List package versions for a project (``project.package_versions``)."""
        if filter is not None:
            kwargs = {**kwargs, "filter": filter}
        return self._execute_route_list(
            "project.package_versions", source=project, **kwargs
        )

    @override
    def list_for_context(
        self,
        source: Any,
        *,
        filter: str | FilterExpression | None = None,
        namespace: str | None = None,
        **kwargs: Any,
    ) -> list[Any]:
        """List package versions in the same scan plane as *source*."""
        if filter is not None:
            kwargs = {**kwargs, "filter": filter}
        if namespace is not None:
            kwargs = {**kwargs, "namespace": namespace}
        return self._execute_route_list(
            "scan.package_versions", source=source, **kwargs
        )


class FindingFacade(ResourceRuntimeFacade[Any]):
    """Finding facade with generated relationship accessors."""

    def list_by_project(
        self,
        project: Any,
        *,
        filter: str | FilterExpression | None = None,
        **kwargs: Any,
    ) -> list[Any]:
        """List findings for a project (generated accessor ``project.findings``)."""
        if filter is not None:
            kwargs = {**kwargs, "filter": filter}
        return self._execute_route_list("project.findings", source=project, **kwargs)

    @override
    def list_for_context(
        self,
        source: Any,
        *,
        filter: str | FilterExpression | None = None,
        namespace: str | None = None,
        **kwargs: Any,
    ) -> list[Any]:
        """List findings in the same scan plane as *source* (``scan.findings``)."""
        if filter is not None:
            kwargs = {**kwargs, "filter": filter}
        if namespace is not None:
            kwargs = {**kwargs, "namespace": namespace}
        return self._execute_route_list("scan.findings", source=source, **kwargs)

    def to_dependency_metadata(
        self,
        finding: Any,
        **kwargs: Any,
    ) -> RouteResult[Any]:
        """Resolve DependencyMetadata for a finding (accessors with fallback)."""
        spec = getattr(finding, "spec", None)
        target_uuid = getattr(spec, "target_uuid", None) if spec is not None else None
        if target_uuid:
            try:
                return self._execute_route(
                    "finding.dependency_metadata.get",
                    source=finding,
                    **kwargs,
                )
            except RouteNotApplicableError:
                pass
        return self._execute_route(
            "finding.dependency_metadata.by_package",
            source=finding,
            **kwargs,
        )


FACADE_CLASS_BY_ATTR: dict[str, type[ResourceRuntimeFacade[Any]]] = {
    "Project": ProjectFacade,
    "ScanResult": ScanResultFacade,
    "Finding": FindingFacade,
    "PackageVersion": PackageVersionFacade,
    "VectorStore": VectorStoreFacade,
    "AuthorizationPolicy": AuthorizationPolicyFacade,
    "Vulnerability": VulnerabilityFacade,
}


class CallGraphDataFacade:
    """Fetch and decode ``CallGraphData`` rows keyed by parent ``PackageVersion``.

    Supported decode sources: ``PackageVersion`` (``meta.parent_uuid``).
    Wire logic lives in ``resources.call_graph_data``; this facade names the
    API resource kind returned on the wire.
    """

    def __init__(self, client: APIClient, default_namespace: str | None) -> None:
        super().__init__()
        self._client = client
        self._default_namespace = default_namespace

    def decode(
        self,
        package_version: Any,
        *,
        namespace: str | None = None,
    ) -> Any:
        """Fetch and unpack call graph JSON for a ``PackageVersion``."""
        from ..resources.call_graph_data import get_call_graph_for_package_version

        return get_call_graph_for_package_version(
            self._client,
            package_version,
            namespace=namespace,
            decode=True,
        )

    def fetch(
        self,
        package_version: Any,
        *,
        namespace: str | None = None,
    ) -> Any:
        """Fetch raw ``CallGraphData`` wire JSON for a ``PackageVersion``."""
        from ..resources.call_graph_data import get_call_graph_for_package_version

        return get_call_graph_for_package_version(
            self._client,
            package_version,
            namespace=namespace,
            decode=False,
        )
