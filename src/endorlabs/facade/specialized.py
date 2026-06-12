# ruff: noqa: TC001
"""Resource-specific facade subclasses and custom facades."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

from ..core.exceptions import RouteNotApplicableError
from ..core.filter import FilterExpression
from ..operations.routes import RouteResult
from ..utils.namespace import resolve_namespace_for_resource
from .runtime import ResourceRuntimeFacade

if TYPE_CHECKING:
    from ..api_client import APIClient


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
    ) -> RouteResult[Any]:
        """List scan results for a project (route ``project.scan_results``)."""
        if namespace is not None:
            kwargs = {**kwargs, "namespace": namespace}
        if limit > 0 and "page_size" not in kwargs:
            kwargs = {**kwargs, "page_size": limit}
        if "sort_by" not in kwargs:
            kwargs = {**kwargs, "sort_by": "meta.create_time", "desc": True}
        if "max_pages" not in kwargs:
            kwargs = {**kwargs, "max_pages": 1}
        result = self._execute_route("project.scan_results", source=project, **kwargs)
        if status_filter and result.values:
            filtered: list[Any] = []
            for item in result.values:
                spec = getattr(item, "spec", None)
                status = getattr(spec, "status", None) if spec is not None else None
                if status is None and isinstance(item, dict):
                    spec_raw = cast("dict[str, Any]", item).get("spec")
                    if isinstance(spec_raw, dict):
                        status = cast("dict[str, Any]", spec_raw).get("status")
                if str(status) == status_filter:
                    filtered.append(item)
            return RouteResult(
                edge_used=result.edge_used,
                values=filtered[:limit] if limit > 0 else filtered,
                warnings=result.warnings,
            )
        if limit > 0 and result.values:
            return RouteResult(
                edge_used=result.edge_used,
                values=result.values[:limit],
                warnings=result.warnings,
            )
        return result


class ProjectFacade(ResourceRuntimeFacade[Any]):
    """Project facade with resolve sugar."""

    def resolve(
        self,
        name_or_uuid: str,
        *,
        namespace: str | None = None,
        warnings_out: list[str] | None = None,
    ) -> Any:
        """Resolve a project by UUID (with traverse fallback) or by name."""
        from ..core.exceptions import NotFoundError as EndorNotFoundError
        from ..core.filter import F
        from ..resources.project import is_hex_project_id

        ns = self._ns(namespace)

        if is_hex_project_id(name_or_uuid):
            try:
                return self.get(name_or_uuid, namespace=ns)
            except EndorNotFoundError:
                matches = self.list(
                    namespace=ns,
                    filter=F("uuid") == name_or_uuid,
                    traverse=True,
                    max_pages=1,
                    page_size=5,
                    concurrent=False,
                )
                if not matches:
                    raise
                if warnings_out is not None:
                    warnings_out.append(
                        f"Project {name_or_uuid!r} is not in namespace {ns!r}; "
                        "resolved the same UUID via list(traverse=True)."
                    )
                return matches[0]
        return self.lookup(name=name_or_uuid, namespace=ns, traverse=True)


class FindingFacade(ResourceRuntimeFacade[Any]):
    """Finding facade with contract-driven list and stitch routes."""

    def list_by_project(
        self,
        project: Any,
        *,
        filter: str | FilterExpression | None = None,
        **kwargs: Any,
    ) -> RouteResult[Any]:
        """List findings for a project via ``spec.project_uuid``."""
        if filter is not None:
            kwargs = {**kwargs, "filter": filter}
        return self._execute_route("project.findings", source=project, **kwargs)

    def list_by_scan(
        self,
        scan_result: Any,
        *,
        namespace: str | None = None,
        filter: str | FilterExpression | None = None,
        **kwargs: Any,
    ) -> RouteResult[Any]:
        """List findings scoped to a ScanResult via ``context.scan_uuid``."""
        if filter is not None:
            kwargs = {**kwargs, "filter": filter}
        if namespace is not None:
            kwargs = {**kwargs, "namespace": namespace}
        return self._execute_route("scan.findings", source=scan_result, **kwargs)

    def to_dependency_metadata(
        self,
        finding: Any,
        **kwargs: Any,
    ) -> RouteResult[Any]:
        """Finding → DependencyMetadata (GET ``target_uuid``, then package fallback)."""
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

    def to_semgrep_rule(
        self,
        finding: Any,
        **kwargs: Any,
    ) -> RouteResult[Any]:
        """Follow finding → SemgrepRule via LinterResult chain (SAST findings only)."""
        return self._execute_route(
            "finding.semgrep_rule.by_linter",
            source=finding,
            **kwargs,
        )


FACADE_CLASS_BY_ATTR: dict[str, type[ResourceRuntimeFacade[Any]]] = {
    "Project": ProjectFacade,
    "ScanResult": ScanResultFacade,
    "Finding": FindingFacade,
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
