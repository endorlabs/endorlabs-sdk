"""
Base model classes for Endor Labs resources.

This module provides base classes that define the common patterns
used across all Endor Labs resource models.
"""

import logging
import sys
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Type, TypeVar

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator

from ..types import ListParameters
from ..utils import SchemaDriftDetector

# Import nested config models for better type safety
from .exception_config import ExceptionConfig
from .finding_config import FindingConfig
from .notification_config import NotificationConfig

T = TypeVar("T", bound=BaseModel)

logger = logging.getLogger(__name__)


class FlexibleEnum(str, Enum):
    """Base class for flexible enums that can handle unknown values."""

    @classmethod
    def _missing_(cls, value):
        """Handle unknown enum values gracefully."""
        logger.warning(
            f"Unknown {cls.__name__} value: {value}. Adding as dynamic enum."
        )
        # Create a dynamic enum member for unknown values
        obj = str.__new__(cls, value)
        # Use setattr to avoid type checker issues
        obj._name_ = value  # type: ignore
        obj._value_ = value  # type: ignore
        return obj


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

    model_config = ConfigDict(
        extra="allow"
    )  # Allow unknown fields for forward compatibility

    # Required universal fields
    name: str = Field(..., description="Resource name")  # IMMUTABLE: Set at creation
    kind: Optional[str] = Field(
        None, description="Resource type identifier"
    )  # IMMUTABLE: Set at creation, but may be None when masked
    version: Optional[str] = Field(
        None, description="Version identifier"
    )  # IMMUTABLE: System-managed, but may be None when masked

    # Lifecycle fields (auto-managed by API)
    create_time: Optional[str] = Field(
        None, description="Creation timestamp"
    )  # IMMUTABLE: System-managed
    created_by: Optional[str] = Field(
        None, description="Creator identifier"
    )  # IMMUTABLE: System-managed
    update_time: Optional[str] = Field(
        None, description="Last update timestamp"
    )  # IMMUTABLE: System-managed
    updated_by: Optional[str] = Field(
        None, description="Last updater identifier"
    )  # IMMUTABLE: System-managed
    upsert_time: Optional[str] = Field(
        None, description="Upsert timestamp"
    )  # IMMUTABLE: System-managed

    # User-defined fields
    description: Optional[str] = Field(
        None, description="Resource description"
    )  # MUTABLE: User can update
    tags: Optional[List[str]] = Field(
        None, description="Resource tags"
    )  # MUTABLE: User can update
    annotations: Optional[Dict[str, Any]] = Field(
        None,
        description="Key-value metadata pairs",  # MUTABLE: User can update
    )
    
    @field_validator("annotations", mode="before")
    @classmethod
    def validate_annotations(cls, v):
        """Validate annotations field - allow any keys including 'id'."""
        # Annotations is a flexible dict that can contain any keys
        # The 'id' field is a known annotation key used by the API
        return v

    # Hierarchical fields
    parent_uuid: Optional[str] = Field(
        None, description="Parent resource UUID"
    )  # IMMUTABLE: Set at creation
    parent_kind: Optional[str] = Field(
        None, description="Parent resource kind"
    )  # IMMUTABLE: Set at creation

    # System fields
    references: Optional[Dict[str, Any]] = Field(
        None,
        description="External references and links",  # IMMUTABLE: System-managed
    )
    index_data: Optional[Dict[str, Any]] = Field(
        None,
        description="Search and indexing metadata",  # IMMUTABLE: System-managed
    )

    @field_validator("*", mode="before")
    @classmethod
    def detect_schema_drift(cls, v, info):
        """Detect and log schema drift for unknown fields."""
        if info.field_name and isinstance(v, dict):
            # Skip drift detection for flexible dict fields
            flexible_dict_fields = {"annotations", "references", "index_data"}
            if info.field_name in flexible_dict_fields:
                return v  # These are flexible dicts that can contain any keys
            
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

    model_config = ConfigDict(
        extra="allow"
    )  # Allow unknown fields for forward compatibility

    # Schema drift fields - using typed models for better structure
    notification: Optional[NotificationConfig] = Field(
        None, description="Notification configuration"
    )
    finding: Optional[FindingConfig] = Field(
        None, description="Finding configuration"
    )
    exception: Optional[ExceptionConfig] = Field(
        None, description="Exception configuration"
    )

    @field_validator("*", mode="before")
    @classmethod
    def detect_schema_drift(cls, v, info):
        """Detect and log schema drift for unknown fields."""
        # Skip drift detection for typed nested models (they handle their own validation)
        # These fields are defined in subclasses as typed Pydantic models
        typed_model_fields = {
            "notification",  # NotificationConfig
            "finding",  # FindingConfig
            "exception",  # ExceptionConfig
            "git",  # GitInfo (in ProjectSpec)
        }
        if info.field_name and isinstance(v, dict) and info.field_name not in typed_model_fields:
            model_fields = {"notification", "finding", "exception", "git"}
            # Extract resource name from class name (e.g., FindingSpec -> Finding)
            resource_name = cls.__name__.replace("Spec", "")
            model_path = f"{resource_name}Spec"
            SchemaDriftDetector.extract_unknown_fields(
                v, model_fields, f"{model_path}.{info.field_name}", resource_name=resource_name
            )
        return v


class BaseResource(BaseModel):
    """Base resource model for all Endor Labs resources.

    Field Mutability Guide:
    ======================

    IMMUTABLE FIELDS (cannot be updated after creation):
    - uuid: System-generated unique identifier
    - meta.name: Resource name set at creation
    - meta.kind: Resource type set at creation
    - meta.create_time: System-managed creation timestamp
    - meta.created_by: System-managed creator identifier
    - meta.update_time: System-managed update timestamp
    - meta.updated_by: System-managed updater identifier
    - meta.upsert_time: System-managed upsert timestamp
    - meta.parent_uuid: Parent relationship set at creation
    - meta.parent_kind: Parent type set at creation
    - meta.references: System-managed external references
    - meta.index_data: System-managed search metadata
    - tenant_meta.namespace: Tenant assignment (immutable)

    MUTABLE FIELDS (can be updated via API):
    - meta.description: User-defined description
    - meta.tags: User-defined tags list
    - meta.annotations: User-defined key-value metadata
    - spec.*: Most spec fields are mutable (resource-specific)
    """

    model_config = ConfigDict(
        extra="allow"
    )  # Allow unknown fields for forward compatibility

    # Universal fields (nearly universal)
    uuid: str = Field(
        ..., description="Unique identifier for the resource"
    )  # IMMUTABLE: System-generated
    meta: BaseMeta = Field(
        ..., description="Resource metadata"
    )  # Mixed: See BaseMeta field comments
    tenant_meta: TenantMeta = Field(
        ..., description="Tenant metadata"
    )  # IMMUTABLE: Set at creation

    # Common fields (88% present)
    spec: Optional[BaseSpec] = Field(
        None, description="Resource specification"
    )  # MUTABLE: Most spec fields can be updated, but may be None when masked

    # Conditional fields (present when applicable)
    context: Optional[Context] = Field(
        None, description="Contextual information"
    )  # MUTABLE: User can update
    processing_status: Optional[ProcessingStatus] = Field(
        None,
        # PARTIALLY MUTABLE: scan_state and disable_automated_scan are updatable
        description="Processing state",
    )
    ingested_object: Optional[IngestedObject] = Field(
        None,
        description="Ingestion metadata",  # IMMUTABLE: System-managed
    )
    related_object: Optional[Dict[str, Any]] = Field(
        None,
        description="Related object information",  # IMMUTABLE: System-managed
    )
    scan_object: Optional[Dict[str, Any]] = Field(
        None,
        description="Scan object information",  # IMMUTABLE: System-managed
    )
    propagate: Optional[bool] = Field(
        None,
        description="Inheritance flag for hierarchical resources",  # MUTABLE
    )

    @field_validator("*", mode="before")
    @classmethod
    def detect_schema_drift(cls, v, info):
        """Detect and log schema drift for unknown fields."""
        # Skip drift detection for typed nested models (they handle their own validation)
        typed_model_fields = {
            "meta",  # BaseMeta
            "tenant_meta",  # TenantMeta
            "context",  # Context
            "processing_status",  # ProcessingStatus
            "ingested_object",  # IngestedObject
        }
        if info.field_name and isinstance(v, dict):
            # Only check drift for non-typed-model fields
            if info.field_name not in typed_model_fields:
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
                    # Extract resource name from class name (e.g., Finding -> Finding)
                    resource_name = cls.__name__
                    SchemaDriftDetector.extract_unknown_fields(
                        v,
                        model_fields,
                        f"{resource_name}.{info.field_name}",
                        resource_name=resource_name,
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

    @field_serializer("*")
    def serialize_datetime(self, value):
        """Serialize datetime objects to ISO format strings."""
        if isinstance(value, datetime):
            return value.isoformat()
        return value


class BaseResourceOperations:
    """Base class providing CRUD operations for all resources."""

    def __init__(self, client, resource_name: str, model_class: Type[T]):
        self.client = client
        self.resource_name = resource_name
        self.model_class = model_class
        self.logger = logging.getLogger(f"{__name__}.{resource_name}")

    def _extract_items_from_page(self, data: Any) -> List[Any]:
        """Extract items from a paginated response page."""
        if "list" in data and "objects" in data["list"]:
            return data["list"]["objects"]
        elif isinstance(data, list):
            return data
        return []

    def _extract_page_token(self, data: Any) -> Optional[str]:
        """Extract next page token from paginated response."""
        if isinstance(data, dict) and "list" in data:
            list_data = data["list"]
            if isinstance(list_data, dict) and "response" in list_data:
                response_data = list_data["response"]
                if isinstance(response_data, dict):
                    return response_data.get("next_page_token")
        return None

    def list(
        self,
        tenant_meta_namespace: str,
        list_params: Optional[ListParameters] = None,
        max_pages: Optional[int] = None,
        **kwargs,
    ) -> List[BaseModel]:
        """Universal list operation with automatic pagination.

        Args:
            tenant_meta_namespace: Namespace to list resources from
            list_params: Optional list parameters (filter, page_size, etc.)
            max_pages: Optional maximum number of pages to fetch.
                If None and in test environment, defaults to 10 pages max.
                If None in production, fetches all pages.
            **kwargs: Additional keyword arguments

        Returns:
            List of resource objects
        """
        try:
            url = f"v1/namespaces/{tenant_meta_namespace}/{self.resource_name}"

            all_items = []
            page_token = None
            page_count = 0

            # Check if we're in a test environment and set default max_pages
            import os

            if max_pages is None and (
                "pytest" in sys.modules or os.getenv("PYTEST_CURRENT_TEST")
            ):
                # Default to 10 pages max in test environment for safety
                max_pages = 10
                self.logger.debug(
                    f"Test environment detected: limiting pagination to "
                    f"{max_pages} pages max"
                )

            while True:
                # Check max_pages limit
                if max_pages is not None and page_count >= max_pages:
                    self.logger.warning(
                        f"Reached max_pages limit ({max_pages}). "
                        f"Stopping pagination after {page_count} pages. "
                        f"Fetched {len(all_items)} items so far."
                    )
                    break

                # Build query parameters for this page
                params = self._build_params(list_params, **kwargs)

                # Add page_token to params if present
                if page_token is not None:
                    params["list_parameters.page_token"] = str(page_token)

                res = self.client.get(url, params=params)
                data = res.json()

                # Extract objects from this page
                items = self._extract_items_from_page(data)
                all_items.extend(items)
                page_count += 1

                # Check for next page token
                page_token = self._extract_page_token(data)

                # Break if no more pages
                if not page_token:
                    break

            self.logger.debug(
                f"Fetched {len(all_items)} {self.resource_name} items "
                f"across {page_count} pages from namespace '{tenant_meta_namespace}'"
            )

            return [self.model_class(**item) for item in all_items]

        except Exception as e:
            error_msg = str(e)
            if hasattr(e, "errors"):
                # Pydantic ValidationError - include detailed error info
                from pydantic import ValidationError

                if isinstance(e, ValidationError):
                    error_details = "\n".join(
                        f"  {err['loc']}: {err['msg']} (type: {err['type']})"
                        for err in e.errors()
                    )
                    error_msg = f"{error_msg}\nValidation details:\n{error_details}"
            self.logger.error(
                f"Failed to list {self.resource_name} in namespace "
                f"'{tenant_meta_namespace}': {error_msg}. "
                f"Check namespace permissions and API connectivity."
            )
            return []

    def get(
        self, tenant_meta_namespace: str, resource_uuid: str
    ) -> Optional[BaseModel]:
        """Universal get operation with fallback to list+filter."""
        try:
            # Method 1: Try direct UUID access first (fastest if it works)
            res = self.client.get(
                f"v1/namespaces/{tenant_meta_namespace}/{self.resource_name}/{resource_uuid}"
            )
            data = res.json()
            return self.model_class(**data)
        except Exception as e:
            self.logger.debug(
                f"Direct {self.resource_name} access failed for UUID '{resource_uuid}' "
                f"in namespace '{tenant_meta_namespace}': {e}. "
                f"Falling back to list+filter approach."
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
                f"List and filter approach failed for {self.resource_name} UUID "
                f"'{resource_uuid}' in namespace '{tenant_meta_namespace}': {e}. "
                f"Resource may not exist or namespace may be inaccessible."
            )
            return None

    def create(
        self, tenant_meta_namespace: str, payload: BaseModel
    ) -> Optional[BaseModel]:
        """Universal create operation."""
        try:
            url = f"v1/namespaces/{tenant_meta_namespace}/{self.resource_name}"

            # Convert payload to dict and validate
            payload_dict = payload.model_dump(exclude_none=True)

            res = self.client.post(url, json=payload_dict)
            data = res.json()

            return self.model_class(**data)

        except Exception as e:
            self.logger.error(
                f"Failed to create {self.resource_name} in namespace "
                f"'{tenant_meta_namespace}': {e}. "
                f"Check payload validity and namespace permissions."
            )
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
            url = (
                f"v1/namespaces/{tenant_meta_namespace}/{self.resource_name}/"
                f"{resource_uuid}"
            )

            # Convert payload to dict and validate
            payload_dict = payload.model_dump(exclude_none=True)

            # Add update_mask as query parameter
            params = {"update_mask": ",".join(update_mask)}

            res = self.client.patch(url, json=payload_dict, params=params)
            data = res.json()

            return self.model_class(**data)

        except Exception as e:
            self.logger.error(
                f"Failed to update {self.resource_name} UUID '{resource_uuid}' "
                f"in namespace '{tenant_meta_namespace}': {e}. "
                f"Check resource exists and update_mask is valid."
            )
            return None

    def delete(self, tenant_meta_namespace: str, resource_uuid: str) -> bool:
        """Universal delete operation."""
        try:
            url = (
                f"v1/namespaces/{tenant_meta_namespace}/{self.resource_name}/"
                f"{resource_uuid}"
            )

            res = self.client.delete(url)

            # Check if deletion was successful (204 No Content or 200 OK)
            return res.status_code in [200, 204]

        except Exception as e:
            self.logger.error(
                f"Failed to delete {self.resource_name} UUID '{resource_uuid}' "
                f"in namespace '{tenant_meta_namespace}': {e}. "
                f"Check resource exists and deletion permissions."
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

            url = f"v1/namespaces/{tenant_meta_namespace}/{self.resource_name}"

            # Build query parameters
            params = self._build_params(count_params)

            res = self.client.get(url, params=params)
            data = res.json()

            # Handle count response
            if "list" in data and "response" in data["list"]:
                return data["list"]["response"].get("total", 0)
            elif "total" in data:
                return data["total"]
            else:
                return 0

        except Exception as e:
            self.logger.error(
                f"Failed to count {self.resource_name} in namespace "
                f"'{tenant_meta_namespace}': {e}. "
                f"Check namespace permissions and filter syntax."
            )
            return 0

    def _build_params(
        self, list_params: Optional[ListParameters], **kwargs
    ) -> Dict[str, Any]:
        """Build query parameters from list_params and kwargs."""
        params = {}

        if list_params:
            self._add_basic_params(params, list_params)
            self._add_pagination_params(params, list_params)
            self._add_sorting_params(params, list_params)
            self._add_boolean_params(params, list_params)
            self._add_date_params(params, list_params)

        # Add any additional kwargs
        params.update(kwargs)

        return params

    def _add_basic_params(
        self, params: Dict[str, Any], list_params: ListParameters
    ) -> None:
        """Add basic filter and mask parameters."""
        if list_params.filter:
            params["list_parameters.filter"] = list_params.filter
        if list_params.mask:
            params["list_parameters.mask"] = list_params.mask

    def _add_pagination_params(
        self, params: Dict[str, Any], list_params: ListParameters
    ) -> None:
        """Add pagination-related parameters."""
        if list_params.page_size:
            params["list_parameters.page_size"] = str(list_params.page_size)
        if list_params.page_token:
            params["list_parameters.page_token"] = list_params.page_token

    def _add_sorting_params(
        self, params: Dict[str, Any], list_params: ListParameters
    ) -> None:
        """Add sorting-related parameters."""
        if list_params.sort_field:
            params["list_parameters.sort_field"] = list_params.sort_field
        if list_params.sort_order:
            params["list_parameters.sort_order"] = list_params.sort_order

    def _add_boolean_params(
        self, params: Dict[str, Any], list_params: ListParameters
    ) -> None:
        """Add boolean parameters."""
        if list_params.count is not None:
            params["list_parameters.count"] = str(list_params.count).lower()
        if list_params.include_child_namespaces is not None:
            params["list_parameters.include_child_namespaces"] = str(
                list_params.include_child_namespaces
            ).lower()

    def _add_date_params(
        self, params: Dict[str, Any], list_params: ListParameters
    ) -> None:
        """Add date-related parameters."""
        if list_params.from_date:
            params["list_parameters.from_date"] = list_params.from_date
        if list_params.to_date:
            params["list_parameters.to_date"] = list_params.to_date
