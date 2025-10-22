"""
Base model classes for Endor Labs resources.

This module provides base classes that define the common patterns
used across all Endor Labs resource models.
"""

import logging
from typing import Any, Dict, List, Optional, Type, TypeVar

from pydantic import BaseModel, ConfigDict, Field, field_validator

from ..types import ListParameters
from ..utils import SchemaDriftDetector

T = TypeVar("T", bound=BaseModel)

logger = logging.getLogger(__name__)


class TenantMeta(BaseModel):
    """Base tenant metadata for all resources."""

    namespace: str = Field(..., description="Canonical namespace name")


class Context(BaseModel):
    """Contextual information for resources with context isolation."""

    id: str = Field(default="default", description="Context identifier")
    type: str = Field(..., description="Context type classification")


class ProcessingStatus(BaseModel):
    """Processing state for scannable resources."""

    disable_automated_scan: bool = Field(
        default=False, description="Disable automated scanning"
    )
    scan_state: Optional[str] = Field(None, description="Current scan state")
    scan_time: Optional[str] = Field(None, description="Last scan timestamp")
    analytic_time: Optional[str] = Field(None, description="Last analytics timestamp")


class IngestedObject(BaseModel):
    """Ingestion metadata for external data."""

    ingestion_time: str = Field(..., description="Ingestion timestamp")
    raw: Dict[str, Any] = Field(..., description="Raw object data")


class BaseMeta(BaseModel):
    """Base metadata for all resources with universal attributes."""

    # Required universal fields
    name: str = Field(..., description="Resource name")
    kind: str = Field(..., description="Resource type identifier")
    version: str = Field(default="v1", description="Version identifier")

    # Lifecycle fields (auto-managed by API)
    create_time: Optional[str] = Field(None, description="Creation timestamp")
    created_by: Optional[str] = Field(None, description="Creator identifier")
    update_time: Optional[str] = Field(None, description="Last update timestamp")
    updated_by: Optional[str] = Field(None, description="Last updater identifier")
    upsert_time: Optional[str] = Field(None, description="Upsert timestamp")

    # User-defined fields
    description: Optional[str] = Field(None, description="Resource description")
    tags: Optional[List[str]] = Field(None, description="Resource tags")
    annotations: Optional[Dict[str, Any]] = Field(
        None, description="Key-value metadata pairs"
    )

    # Hierarchical fields
    parent_uuid: Optional[str] = Field(None, description="Parent resource UUID")
    parent_kind: Optional[str] = Field(None, description="Parent resource kind")

    # System fields
    references: Optional[Dict[str, Any]] = Field(
        None, description="External references and links"
    )
    index_data: Optional[Dict[str, Any]] = Field(
        None, description="Search and indexing metadata"
    )

    @field_validator("*", mode="before")
    @classmethod
    def detect_schema_drift(cls, v, info):
        """Detect and log schema drift for unknown fields."""
        if info.field_name and isinstance(v, dict):
            model_fields = {
                "name",
                "kind",
                "version",
                "create_time",
                "update_time",
                "created_by",
                "updated_by",
                "upsert_time",
                "description",
                "tags",
                "annotations",
                "parent_uuid",
                "parent_kind",
                "references",
                "index_data",
            }

            if info.field_name in model_fields:
                SchemaDriftDetector.extract_unknown_fields(
                    v, model_fields, f"BaseMeta.{info.field_name}"
                )
        return v


class BaseSpec(BaseModel):
    """Base specification for all resources."""

    model_config = ConfigDict(extra="ignore")

    # Schema drift fields
    notification: Optional[Dict[str, Any]] = Field(
        None, description="Notification configuration"
    )

    @field_validator("*", mode="before")
    @classmethod
    def detect_schema_drift(cls, v, info):
        """Detect and log schema drift for unknown fields."""
        if info.field_name and isinstance(v, dict):
            model_fields = {"notification"}

            if info.field_name in model_fields:
                SchemaDriftDetector.extract_unknown_fields(
                    v, model_fields, f"BaseSpec.{info.field_name}"
                )
        return v


class BaseResource(BaseModel):
    """Base resource model for all Endor Labs resources."""

    model_config = ConfigDict(extra="ignore")

    # Universal fields (nearly universal)
    uuid: str = Field(..., description="Unique identifier for the resource")
    meta: BaseMeta = Field(..., description="Resource metadata")
    tenant_meta: TenantMeta = Field(..., description="Tenant metadata")

    # Common fields (88% present)
    spec: BaseSpec = Field(..., description="Resource specification")

    # Conditional fields (present when applicable)
    context: Optional[Context] = Field(None, description="Contextual information")
    processing_status: Optional[ProcessingStatus] = Field(
        None, description="Processing state"
    )
    ingested_object: Optional[IngestedObject] = Field(
        None, description="Ingestion metadata"
    )
    related_object: Optional[Dict[str, Any]] = Field(
        None, description="Related object information"
    )
    scan_object: Optional[Dict[str, Any]] = Field(
        None, description="Scan object information"
    )
    propagate: Optional[bool] = Field(
        None, description="Inheritance flag for hierarchical resources"
    )

    @field_validator("*", mode="before")
    @classmethod
    def detect_schema_drift(cls, v, info):
        """Detect and log schema drift for unknown fields."""
        if info.field_name and isinstance(v, dict):
            model_fields = {
                "uuid",
                "meta",
                "spec",
                "tenant_meta",
                "context",
                "processing_status",
                "ingested_object",
                "related_object",
                "scan_object",
                "propagate",
            }

            if info.field_name in model_fields:
                SchemaDriftDetector.extract_unknown_fields(
                    v, model_fields, f"BaseResource.{info.field_name}"
                )
        return v

    def get_mutable_fields(self) -> List[str]:
        """Get list of mutable fields for this resource."""
        return ["meta.description", "meta.tags"]

    def get_immutable_fields(self) -> List[str]:
        """Get list of immutable fields for this resource."""
        return [
            "uuid",
            "meta.name",
            "meta.create_time",
            "meta.created_by",
            "meta.update_time",
            "meta.updated_by",
            "tenant_meta.namespace",
        ]

    def validate_update_mask(self, update_mask: str) -> bool:
        """Validate that update_mask only contains mutable fields."""
        mutable_fields = self.get_mutable_fields()
        return update_mask in mutable_fields


class BaseResourceOperations:
    """Base class providing CRUD operations for all resources."""

    def __init__(self, client, resource_name: str, model_class: Type[T]):
        self.client = client
        self.resource_name = resource_name
        self.model_class = model_class
        self.logger = logging.getLogger(f"{__name__}.{resource_name}")

    def list(
        self,
        tenant_meta_namespace: str,
        list_params: Optional[ListParameters] = None,
        **kwargs,
    ) -> List[BaseModel]:
        """Universal list operation with filtering, masking, and pagination."""
        try:
            headers = self.client.default_headers
            url = f"v1/namespaces/{tenant_meta_namespace}/{self.resource_name}"

            # Build query parameters
            params = self._build_params(list_params, **kwargs)

            res = self.client.get(url, headers=headers, params=params)
            data = res.json()

            # Handle both list.objects and direct array responses
            if "list" in data and "objects" in data["list"]:
                items = data["list"]["objects"]
            elif isinstance(data, list):
                items = data
            else:
                items = []

            return [self.model_class(**item) for item in items]

        except Exception as e:
            self.logger.error(f"Failed to list {self.resource_name}: {e}")
            return []

    def get(
        self, tenant_meta_namespace: str, resource_uuid: str
    ) -> Optional[BaseModel]:
        """Universal get operation with fallback to list+filter."""
        try:
            # Method 1: Try direct UUID access first (fastest if it works)
            headers = self.client.default_headers
            res = self.client.get(
                f"v1/namespaces/{tenant_meta_namespace}/{self.resource_name}/{resource_uuid}",
                headers=headers,
            )
            data = res.json()
            return self.model_class(**data)
        except Exception as e:
            self.logger.debug(
                f"Direct {self.resource_name} access failed for {resource_uuid}: {e}"
            )

        # Method 2: Use list and filter approach (workaround)
        try:
            list_params = ListParameters(
                filter=f"uuid=={resource_uuid}",
                mask=None,
                page_size=None,
                page_token=None,
                sort_field=None,
                sort_order=None,
                count=None,
                include_child_namespaces=None,
                from_date=None,
                to_date=None,
            )
            resources = self.list(tenant_meta_namespace, list_params)
            return resources[0] if resources else None
        except Exception as e:
            self.logger.error(
                f"List and filter approach failed for {resource_uuid}: {e}"
            )
            return None

    def create(
        self, tenant_meta_namespace: str, payload: BaseModel
    ) -> Optional[BaseModel]:
        """Universal create operation."""
        try:
            headers = self.client.default_headers
            url = f"v1/namespaces/{tenant_meta_namespace}/{self.resource_name}"

            # Convert payload to dict and validate
            payload_dict = payload.model_dump(exclude_none=True)

            res = self.client.post(url, headers=headers, json=payload_dict)
            data = res.json()

            return self.model_class(**data)

        except Exception as e:
            self.logger.error(f"Failed to create {self.resource_name}: {e}")
            return None

    def update(
        self,
        tenant_meta_namespace: str,
        resource_uuid: str,
        payload: BaseModel,
        update_mask: List[str],
    ) -> Optional[BaseModel]:
        """Universal update operation with field masking."""
        try:
            headers = self.client.default_headers
            url = f"v1/namespaces/{tenant_meta_namespace}/{self.resource_name}/{resource_uuid}"

            # Convert payload to dict and validate
            payload_dict = payload.model_dump(exclude_none=True)

            # Add update_mask as query parameter
            params = {"update_mask": ",".join(update_mask)}

            res = self.client.patch(
                url, headers=headers, data=payload_dict, params=params
            )
            data = res.json()

            return self.model_class(**data)

        except Exception as e:
            self.logger.error(
                f"Failed to update {self.resource_name} {resource_uuid}: {e}"
            )
            return None

    def delete(self, tenant_meta_namespace: str, resource_uuid: str) -> bool:
        """Universal delete operation."""
        try:
            headers = self.client.default_headers
            url = f"v1/namespaces/{tenant_meta_namespace}/{self.resource_name}/{resource_uuid}"

            res = self.client.delete(url, headers=headers)

            # Check if deletion was successful (204 No Content or 200 OK)
            return res.status_code in [200, 204]

        except Exception as e:
            self.logger.error(
                f"Failed to delete {self.resource_name} {resource_uuid}: {e}"
            )
            return False

    def count(
        self, tenant_meta_namespace: str, list_params: Optional[ListParameters] = None
    ) -> int:
        """Count resources matching filter criteria."""
        try:
            # Create count-specific list parameters
            if list_params:
                count_params = list_params
                count_params.count = True
            else:
                count_params = ListParameters(
                    filter=None,
                    mask=None,
                    page_size=None,
                    page_token=None,
                    sort_field=None,
                    sort_order=None,
                    count=True,
                    include_child_namespaces=None,
                    from_date=None,
                    to_date=None,
                )

            headers = self.client.default_headers
            url = f"v1/namespaces/{tenant_meta_namespace}/{self.resource_name}"

            # Build query parameters
            params = self._build_params(count_params)

            res = self.client.get(url, headers=headers, params=params)
            data = res.json()

            # Handle count response
            if "list" in data and "response" in data["list"]:
                return data["list"]["response"].get("total", 0)
            elif "total" in data:
                return data["total"]
            else:
                return 0

        except Exception as e:
            self.logger.error(f"Failed to count {self.resource_name}: {e}")
            return 0

    def _build_params(
        self, list_params: Optional[ListParameters], **kwargs
    ) -> Dict[str, Any]:
        """Build query parameters from list_params and kwargs."""
        params = {}

        if list_params:
            if list_params.filter:
                params["list_parameters.filter"] = list_params.filter
            if list_params.mask:
                params["list_parameters.mask"] = list_params.mask
            if list_params.page_size:
                params["list_parameters.page_size"] = str(list_params.page_size)
            if list_params.page_token:
                params["list_parameters.page_token"] = list_params.page_token
            if list_params.sort_field:
                params["list_parameters.sort_field"] = list_params.sort_field
            if list_params.sort_order:
                params["list_parameters.sort_order"] = list_params.sort_order
            if list_params.count is not None:
                params["list_parameters.count"] = str(list_params.count).lower()
            if list_params.include_child_namespaces is not None:
                params["list_parameters.include_child_namespaces"] = str(
                    list_params.include_child_namespaces
                ).lower()
            if list_params.from_date:
                params["list_parameters.from_date"] = list_params.from_date
            if list_params.to_date:
                params["list_parameters.to_date"] = list_params.to_date

        # Add any additional kwargs
        params.update(kwargs)

        return params
