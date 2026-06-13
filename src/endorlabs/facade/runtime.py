# pyright: reportImportCycles=false
"""Resource runtime facade: get/create/update/delete."""

from __future__ import annotations

from typing import (
    TYPE_CHECKING,
    Any,
    Literal,
    TypeGuard,
    cast,
    override,
)

from pydantic import BaseModel

from ..core.exceptions import NotFoundError, ValidationError
from ..operations import BaseResourceOperations
from ..utils.namespace import resolve_namespace_for_resource

if TYPE_CHECKING:
    from collections.abc import Callable

    from ..api_client import APIClient
    from ..registry import ResourceEntry


from ..generated.route_contract import ROUTE_CONTRACT
from .base import ListableFacade
from .route_host import RouteHostMixin


class ResourceRuntimeFacade[T: BaseModel](ListableFacade[T], RouteHostMixin):
    """Facade for resources with get/create/update/delete where supported.

    id_or_resource / name_or_resource: Methods accept either a UUID string or a
    resource object. When a resource object is passed, UUID is taken from it and
    namespace is derived from the resource's tenant_meta unless overridden by
    the namespace= argument.

    Namespace resolution: From client default or explicit namespace=; for
    list/get/create/update/delete, explicit namespace= overrides resource-derived
    namespace when both could apply.

    Scope (set at facade construction):
        * ``None`` — tenant-scoped; namespace from client default or argument.
        * ``"oss"`` — OSS-scoped; namespace always ``"oss"``.
        * ``"system"`` — system-scoped; namespace always ``"system"``.
    """

    def __init__(
        self,
        client: APIClient,
        default_namespace: str | None,
        entry: ResourceEntry,
        *,
        tags_paths: list[str] | None = None,
    ) -> None:
        super().__init__(client, default_namespace, entry, tags_paths=tags_paths)
        self._init_route_host(
            client,
            default_namespace,
            route_contract=ROUTE_CONTRACT,
        )
        self._supported_ops = entry.supported_ops
        self._build_create_payload_fn: Callable[..., Any] | None = (
            entry.build_create_payload_fn
        )
        self._scope: Literal["system"] | Literal["oss"] | None = entry.scope
        self._create_mode = entry.create_mode
        self._update_requires_mask = entry.update_requires_mask

    @property
    def scope(self) -> Literal["system"] | Literal["oss"] | None:
        """The resource scope: ``"oss"``, ``"system"``, or ``None`` (tenant)."""
        return self._scope

    @override
    def _ns(self, namespace: str | None) -> str:
        if self._scope == "oss":
            return "oss"
        if self._scope == "system":
            return "system"
        return super()._ns(namespace)

    def _is_resource_like(self, value: Any) -> TypeGuard[T]:
        """Return True if value has uuid and tenant_meta (resource object)."""
        return (
            hasattr(value, "uuid")
            and hasattr(value, "tenant_meta")
            and value is not None
        )

    def get(self, id_or_resource: str | T, namespace: str | None = None) -> T:
        """Fetch a single resource by UUID or resource object.

        When ``id_or_resource`` is a resource object, the UUID is extracted
        from it and the namespace is derived from the resource's
        ``tenant_meta`` unless overridden by ``namespace=``.

        Args:
            id_or_resource: UUID string, or a resource object whose
                ``uuid`` and ``tenant_meta`` are used for resolution.
            namespace: Canonical namespace path (e.g. ``"tenant.child"``);
                defaults to the client tenant or the resource's namespace.

        Returns:
            The resource.

        Raises:
            NotImplementedError: No get support.
            ValueError: Namespace required but not set.

        Example:
            project = client.Project.get('uuid-here', namespace='tenant.team')
            updated = client.Project.get(project)

        """
        if "get" not in self._supported_ops:
            raise NotImplementedError(
                "This resource does not support get; use list() for system/tenant."
            ) from None
        if self._is_resource_like(id_or_resource):
            res = cast("Any", id_or_resource)
            uuid = res.uuid
            ns = (
                self._ns(namespace)
                if namespace is not None
                else self._ns(
                    resolve_namespace_for_resource(res, self._default_namespace)
                )
            )
        else:
            uuid = id_or_resource
            ns = self._ns(namespace)
        return self._ops.get(ns, cast("str", uuid))

    def parent(self, resource: T) -> BaseModel:
        """Fetch the parent resource declared by registry ``parent_kind``."""
        if self._parent_kind is None:
            raise ValidationError(
                f"{self._entry.attr_name} has no parent_kind; parent() unsupported."
            ) from None
        meta = getattr(resource, "meta", None)
        parent_uuid = getattr(meta, "parent_uuid", None) if meta is not None else None
        if not parent_uuid:
            raise NotFoundError(
                "Resource has no meta.parent_uuid.",
                operation="parent",
            )
        ns = self._ns(resolve_namespace_for_resource(resource, self._default_namespace))
        if self._parent_kind == "project":
            from ..resources.project import Project

            project_ops: BaseResourceOperations[Any] = BaseResourceOperations(
                self._client, "projects", Project
            )
            return project_ops.get(ns, str(parent_uuid))
        raise ValidationError(
            f"Unsupported parent_kind {self._parent_kind!r} for parent()."
        ) from None

    def create(
        self,
        payload: Any = None,
        *,
        name: str | None = None,
        description: str | None = None,
        namespace_uuid: str | None = None,
        namespace: str | None = None,
        **kwargs: Any,
    ) -> T:
        """Create a resource via ``payload=`` or kwargs (``build_create_payload``).

        Either pass a ``CreateXPayload`` in ``payload=`` or resource-specific
        kwargs; the two forms are mutually exclusive.

        Args:
            payload: A ``CreateXPayload`` model instance; mutually exclusive
                with keyword arguments.
            name: Convenience kwarg; merged into builder kwargs.
            description: Convenience kwarg; merged into builder kwargs.
            namespace_uuid: Convenience kwarg; merged into builder kwargs.
            namespace: Canonical namespace path (e.g. ``"tenant.child"``)
                where the resource will be created; defaults to the client
                tenant.
            **kwargs: Resource-specific keyword arguments passed to the
                resource's ``build_create_payload`` function.

        Returns:
            Created resource with server-assigned fields.

        Raises:
            NotImplementedError: Resource has no create.
            TypeError: Both payload and kwargs, or neither, or kwargs without builder.
            ValueError: Namespace required but not set.

        Example:
            ns = client.Namespace.create(name='my-namespace', namespace='tenant')

        """
        if "create" not in self._supported_ops:
            raise NotImplementedError(
                "This resource does not support create."
            ) from None
        # Merge explicit optional params into kwargs (explicit wins when not None)
        explicit = {
            k: v
            for k, v in (
                ("name", name),
                ("description", description),
                ("namespace_uuid", namespace_uuid),
            )
            if v is not None
        }
        merged: dict[str, Any] = {**kwargs, **explicit}
        if payload is not None and merged:
            raise TypeError("provide either payload= or kwargs for create(), not both.")
        if payload is None and not merged:
            raise TypeError("create() requires payload= or resource-specific kwargs.")
        if payload is None and merged and self._create_mode == "both":
            # namespace is consumed by _ns(); do not pass to builder
            create_kwargs: dict[str, Any] = {
                k: v for k, v in merged.items() if k != "namespace"
            }
            if self._build_create_payload_fn is None:
                raise TypeError(
                    "create() contract is inconsistent: "
                    "create_mode=both without builder."
                )
            payload = self._build_create_payload_fn(**create_kwargs)
        elif payload is None and merged and self._create_mode != "both":
            raise TypeError(
                "create() for this resource requires payload=; kwargs not supported."
            )
        if payload is None:
            raise TypeError("create() internal error: payload unresolved.")
        ns = self._ns(namespace)
        return self._ops.create(ns, payload)

    def update(
        self,
        id_or_resource: str | T,
        payload: Any | None = None,
        *,
        update_mask: str | None = None,
        meta_description: str | None = None,
        meta_tags: list[str] | None = None,
        namespace: str | None = None,
        **kwargs: Any,
    ) -> T:
        """Update a resource: ``update_mask`` + payload, or field kwargs (mask derived).

        When using field kwargs (e.g. ``meta_tags=[...]``), ``id_or_resource``
        must be a resource instance; the resource is used as the payload and
        the mask is derived automatically.

        Args:
            id_or_resource: UUID string, or a resource object whose
                ``uuid`` and ``tenant_meta`` are used for resolution.
            payload: Updated fields; optional when ``id_or_resource`` is a
                resource instance (the resource itself is used as payload).
            update_mask: Comma-separated field paths to update
                (e.g. ``"meta.tags"``).
            meta_description: Convenience kwarg; updates ``meta.description``.
            meta_tags: Convenience kwarg; updates ``meta.tags``.
            namespace: Canonical namespace path (e.g. ``"tenant.child"``);
                defaults to the client tenant or the resource's namespace.
            **kwargs: Mutable field kwargs; ``update_mask`` is derived
                automatically if omitted.

        Returns:
            Updated resource.

        Raises:
            NotImplementedError: No update support.
            TypeError: No mask nor kwargs; or kwargs with UUID id_or_resource.
            ValueError: Missing namespace or immutable in update_mask.

        Example:
            updated = client.Project.update(project, meta_tags=['reviewed'])

        """
        if "update" not in self._supported_ops:
            raise NotImplementedError(
                "This resource does not support update."
            ) from None
        # Merge explicit optional params into kwargs (explicit wins when not None)
        merged_kwargs = dict(kwargs)
        if meta_description is not None:
            merged_kwargs["meta_description"] = meta_description
        if meta_tags is not None:
            merged_kwargs["meta_tags"] = meta_tags
        if update_mask is None and not merged_kwargs:
            raise TypeError(
                "provide update_mask (e.g. 'meta.tags') or field kwargs "
                "(e.g. meta_tags=[...])."
            )
        if update_mask is None and merged_kwargs:
            if not self._is_resource_like(id_or_resource):
                raise TypeError(
                    "when using field kwargs, id_or_resource must be a "
                    "resource instance (not a UUID string)."
                )
            res = cast("Any", id_or_resource)
            return res.update(self, **merged_kwargs)
        if self._is_resource_like(id_or_resource):
            res = cast("Any", id_or_resource)
            uuid = res.uuid
            ns = (
                self._ns(namespace)
                if namespace is not None
                else self._ns(
                    resolve_namespace_for_resource(res, self._default_namespace)
                )
            )
            if payload is None:
                payload = res
        else:
            uuid = id_or_resource
            ns = self._ns(namespace)
            if payload is None:
                raise TypeError(
                    "payload is required when id_or_resource is a UUID string."
                )
        # Convert comma-separated mask string to list (strip empty segments)
        mask_list: list[str] = (
            [p.strip() for p in update_mask.split(",") if p.strip()]
            if isinstance(update_mask, str)
            else (update_mask or [])
        )
        assert payload is not None  # guaranteed by TypeError guard above
        return self._ops.update(ns, cast("str", uuid), payload, mask_list)

    def delete(
        self,
        name_or_resource: str | T,
        namespace: str | None = None,
        *,
        ignore_missing: bool = False,
    ) -> bool:
        """Remove a resource by UUID or resource object.

        When ``name_or_resource`` is a resource object, the UUID is extracted
        from it and the namespace is derived from the resource's
        ``tenant_meta`` unless overridden by ``namespace=``.

        Args:
            name_or_resource: UUID string, or a resource object whose
                ``uuid`` and ``tenant_meta`` are used for resolution.
            namespace: Canonical namespace path (e.g. ``"tenant.child"``);
                defaults to the client tenant or the resource's namespace.
            ignore_missing: If ``True``, return ``False`` on 404 instead of
                raising ``NotFoundError``.

        Returns:
            ``True`` if deleted; ``False`` if ``ignore_missing`` and not found.

        Raises:
            NotImplementedError: No delete support.
            NotFoundError: Not found and not ``ignore_missing``.
            ValueError: Namespace required but not set.

        Example:
            client.Project.delete(project)
            deleted = client.Project.delete(
                'uuid', namespace='tenant.team', ignore_missing=True
            )

        """
        if "delete" not in self._supported_ops:
            raise NotImplementedError(
                "This resource does not support delete."
            ) from None
        if self._is_resource_like(name_or_resource):
            res = cast("Any", name_or_resource)
            uuid = res.uuid
            ns = (
                self._ns(namespace)
                if namespace is not None
                else self._ns(
                    resolve_namespace_for_resource(res, self._default_namespace)
                )
            )
        else:
            uuid = name_or_resource
            ns = self._ns(namespace)
        try:
            return self._ops.delete(ns, cast("str", uuid))
        except NotFoundError:
            if ignore_missing:
                return False
            raise

    def tag(
        self,
        id_or_resource: str | T,
        tags: list[str],
        namespace: str | None = None,
    ) -> T:
        """Set ``meta.tags`` (replaces existing tags).

        Wraps ``update(update_mask='meta.tags')``.

        Only available for resources whose ``meta.tags`` is a mutable field.

        Args:
            id_or_resource: UUID string, or a resource object whose
                ``uuid`` and ``tenant_meta`` are used for resolution.
            tags: Tag list that replaces all existing tags. Use ``[]`` to
                clear.
            namespace: Canonical namespace path (e.g. ``"tenant.child"``);
                defaults to the client tenant or the resource's namespace.

        Returns:
            Updated resource.

        Raises:
            NotImplementedError: No tagging support.
            ValueError: Missing namespace or no meta.

        Example:
            updated = client.Project.tag(project, tags=['reviewed', 'production'])

        """
        resource, uuid, ns, meta = self._resolve_for_tag(
            id_or_resource, namespace, operation="tag"
        )
        model_copy = getattr(resource, "model_copy")  # noqa: B009
        payload = model_copy(update={"meta": meta.model_copy(update={"tags": tags})})
        return self._ops.update(ns, uuid, payload, ["meta.tags"])

    def untag(
        self,
        id_or_resource: str | T,
        keys: list[str],
        namespace: str | None = None,
    ) -> T:
        """Remove listed tags from ``meta.tags``; fetch, filter, then update.

        Tags in ``keys`` that are not present on the resource are silently
        ignored.

        Args:
            id_or_resource: UUID string, or a resource object whose
                ``uuid`` and ``tenant_meta`` are used for resolution.
            keys: Tag values to remove; all other tags are preserved.
            namespace: Canonical namespace path (e.g. ``"tenant.child"``);
                defaults to the client tenant or the resource's namespace.

        Returns:
            Updated resource.

        Raises:
            NotImplementedError: No tagging support.
            ValueError: Missing namespace or no meta.

        Example:
            updated = client.Project.untag(project, keys=['deprecated'])

        """
        resource, uuid, ns, meta = self._resolve_for_tag(
            id_or_resource, namespace, operation="untag"
        )
        current: list[str] = getattr(meta, "tags", None) or []
        new_tags: list[str] = [t for t in current if t not in keys]
        model_copy = getattr(resource, "model_copy")  # noqa: B009
        payload = model_copy(
            update={"meta": meta.model_copy(update={"tags": new_tags})}
        )
        return self._ops.update(ns, uuid, payload, ["meta.tags"])

    # -- Internal helpers for tag / untag ----------------------------------

    def _resolve_for_tag(
        self,
        id_or_resource: str | T,
        namespace: str | None,
        *,
        operation: str = "tag",
    ) -> tuple[T, str, str, Any]:
        """Resolve resource, uuid, namespace and meta for tag/untag.

        Returns:
            (resource, uuid, namespace, meta)

        Raises:
            NotImplementedError: When the resource does not support tagging.
            ValueError: When the resource has no ``meta``.
        """
        if (
            not self._tags_paths
            or "meta.tags" not in self._tags_paths
            or "update" not in self._supported_ops
        ):
            raise NotImplementedError(
                f"This resource does not support {operation}."
            ) from None
        resource: T = (
            id_or_resource
            if self._is_resource_like(id_or_resource)
            else self.get(id_or_resource, namespace=namespace)
        )
        uuid: str = getattr(resource, "uuid")  # noqa: B009
        ns = (
            self._ns(namespace)
            if namespace is not None
            else self._ns(
                resolve_namespace_for_resource(resource, self._default_namespace)
            )
        )
        meta = getattr(resource, "meta", None)
        if meta is None:
            raise ValidationError(
                f"Resource has no meta; cannot {operation} meta.tags."
            ) from None
        return resource, uuid, ns, meta
