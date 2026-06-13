"""Consumer resource mixin for V1-backed facade models.

Cutover resources inherit ``V1*`` wire types plus this mixin for
``.update()``, mutable/immutable field metadata, and namespace sugar.
Legacy ``BaseResource`` includes the same behavior via multiple inheritance.
"""

from __future__ import annotations

from datetime import datetime
from typing import (
    TYPE_CHECKING,
    Any,
    ClassVar,
    Literal,
    Self,
    Union,
    cast,
    get_args,
    get_origin,
    override,
)

from pydantic import field_serializer

from ...utils.logging_config import get_resource_logger

if TYPE_CHECKING:
    from ...core.types import SupportsResourceUpdate

logger = get_resource_logger(__name__)

_DEFAULT_MUTABLE: list[str] = ["meta.description", "meta.tags"]
_DEFAULT_IMMUTABLE: list[str] = [
    "uuid",
    "meta.create_time",
    "meta.created_by",
    "meta.update_time",
    "meta.updated_by",
    "meta.upsert_time",
    "meta.kind",
    "meta.version",
    "meta.references",
    "meta.index_data",
    "tenant_meta.namespace",
]


class ConsumerResourceMixin:
    """Shared consumer behavior for registry resource models (non-BaseModel mixin)."""

    _MUTABLE_FIELDS: ClassVar[list[str] | None] = None
    _IMMUTABLE_FIELDS: ClassVar[list[str] | None] = None

    @property
    def namespace(self) -> str | None:
        """Canonical namespace for this resource (tenant_meta.namespace or None)."""
        tenant_meta = getattr(self, "tenant_meta", None)
        if tenant_meta is None:
            return None
        if isinstance(tenant_meta, dict):
            ns = tenant_meta.get("namespace")
            return str(ns) if ns is not None else None
        return getattr(tenant_meta, "namespace", None)

    @classmethod
    def get_mutable_fields_cls(cls) -> list[str]:
        """Return mutable update_mask paths for this resource type."""
        if cls._MUTABLE_FIELDS is not None:
            return list(cls._MUTABLE_FIELDS)
        return list(_DEFAULT_MUTABLE)

    def get_mutable_fields(self) -> list[str]:
        """Return mutable update_mask paths for this resource instance."""
        return type(self).get_mutable_fields_cls()

    def _path_to_kwarg(self, path: str) -> str:
        """Convert update_mask path to Python kwarg name."""
        if path.startswith("processing_status."):
            return path.split(".", 1)[1]
        return path.replace(".", "_")

    def get_update_kwarg_to_path(self) -> dict[str, str]:
        """Map kwarg names to update_mask paths for generic update."""
        return {self._path_to_kwarg(p): p for p in self.get_mutable_fields()}

    def _build_update_payload(self, **kwargs: Any) -> Self:
        """Build a copy of this resource with kwargs applied at their paths."""
        kwarg_to_path = self.get_update_kwarg_to_path()
        invalid = [k for k in kwargs if k not in kwarg_to_path]
        if invalid:
            raise TypeError(
                f"Invalid update kwargs for {type(self).__name__}: {invalid}. "
                f"Allowed: {list(kwarg_to_path)}"
            )
        result: Any = self
        for kwarg, value in kwargs.items():
            path = kwarg_to_path[kwarg]
            if "." not in path:
                result = result.model_copy(update={path: value})
                continue
            parent_path, field = path.rsplit(".", 1)
            parent = getattr(result, parent_path, None)
            if parent is None and parent_path == "processing_status":
                field_info = type(result).model_fields.get(parent_path)
                if field_info:
                    ann = getattr(field_info, "annotation", None)
                    if ann is not None and get_origin(ann) is Union:
                        ann = next(
                            (a for a in get_args(ann) if a is not type(None)),
                            ann,
                        )
                    if ann is not None:
                        try:
                            parent = ann(disable_automated_scan=False, scan_state="")
                        except Exception as exc:
                            logger.debug(
                                "Unable to construct parent model for %s: %s", ann, exc
                            )
                            parent = None
            if parent is not None:
                dump = (
                    parent.model_dump()
                    if callable(getattr(parent, "model_dump", None))
                    else {}
                )
                merged = {**dump, field: value}
                new_parent = type(parent)(**merged)
                result = result.model_copy(update={parent_path: new_parent})
        return result

    def update(
        self,
        facade: SupportsResourceUpdate,
        **kwargs: Any,
    ) -> Self:
        """Update this resource with field kwargs; delegate to the facade."""
        if not kwargs:
            raise TypeError(
                "Provide at least one field kwarg (e.g. meta_description=...) "
                "or use facade.update(resource, update_mask=..., payload=...)."
            )
        kwarg_to_path = self.get_update_kwarg_to_path()
        invalid = [k for k in kwargs if k not in kwarg_to_path]
        if invalid:
            raise TypeError(
                f"Invalid update kwargs for {type(self).__name__}: {invalid}. "
                f"Allowed: {list(kwarg_to_path)}"
            )
        payload = self._build_update_payload(**kwargs)
        update_mask = ",".join(kwarg_to_path[k] for k in kwargs)
        return facade.update(self, payload=payload, update_mask=update_mask)

    @classmethod
    def get_immutable_fields_cls(cls) -> list[str]:
        """Return read-only field paths for this resource type."""
        if cls._IMMUTABLE_FIELDS is not None:
            return list(cls._IMMUTABLE_FIELDS)
        return list(_DEFAULT_IMMUTABLE)

    def get_immutable_fields(self) -> list[str]:
        """Return read-only field paths for this resource instance."""
        return type(self).get_immutable_fields_cls()

    def validate_update_mask(self, update_mask: str) -> bool:
        """Validate that update_mask only contains mutable fields."""
        mutable_fields = self.get_mutable_fields()
        return update_mask in mutable_fields


class ConsumerResourceSerializerMixin(ConsumerResourceMixin):
    """Mixin adding datetime serialization and quiet ``model_dump`` defaults."""

    @field_serializer("*")
    def serialize_datetime(self, value: datetime | str) -> str:
        """Serialize datetime objects to ISO format strings."""
        if isinstance(value, datetime):
            return value.isoformat()
        return value

    @override
    def model_dump(
        self,
        *,
        mode: Literal["json", "python"] = "json",
        warnings: bool = False,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Dump model; default ``warnings=False`` for nested wire types."""
        return cast("Any", super()).model_dump(mode=mode, warnings=warnings, **kwargs)

    @override
    def model_dump_json(  # pyright: ignore[reportIncompatibleMethodOverride]
        self,
        *,
        indent: int | None = None,
        include: set[str] | dict[str, Any] | None = None,
        exclude: set[str] | dict[str, Any] | None = None,
        by_alias: bool = False,
        exclude_unset: bool = False,
        exclude_defaults: bool = False,
        exclude_none: bool = False,
        round_trip: bool = False,
        warnings: bool = False,
        serialize_as_any: bool = False,
    ) -> str:
        """Serialize to JSON; default ``warnings=False``."""
        return cast("Any", super()).model_dump_json(
            indent=indent,
            include=include,
            exclude=exclude,
            by_alias=by_alias,
            exclude_unset=exclude_unset,
            exclude_defaults=exclude_defaults,
            exclude_none=exclude_none,
            round_trip=round_trip,
            warnings=warnings,
            serialize_as_any=serialize_as_any,
        )
