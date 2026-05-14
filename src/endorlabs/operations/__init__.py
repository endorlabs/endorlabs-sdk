"""Resource operations engine for Endor Labs API.

Provides ``BaseResourceOperations[T]`` — the CRUD engine that builds URLs,
serializes payloads, handles pagination, and maps API errors to typed
exceptions.  Extracted from ``models.base`` so model definitions stay
separate from HTTP/transport logic.
"""

import builtins
import functools
import os
import re
from collections.abc import Iterator
from typing import TYPE_CHECKING, Any, Generic, TypeVar, cast

import httpx
from pydantic import BaseModel, ValidationError

from ..core.exceptions import EndorAPIError
from ..core.exceptions import ValidationError as EndorValidationError
from ..core.types import ListParameters, list_parameters_has_nonempty_field_mask
from ..utils.logging_config import get_resource_logger

if TYPE_CHECKING:
    from ..api_client import APIClient

T = TypeVar("T", bound=BaseModel)

_NAMESPACE_RE = re.compile(r"^[a-zA-Z0-9._-]+$")


def validate_namespace(ns: str) -> str:
    """Validate that *ns* matches the canonical namespace format.

    Namespace strings are interpolated into URL paths; a value containing
    ``/`` or ``..`` could alter the request target.  This check ensures
    only safe characters (alphanumeric, dots, hyphens, underscores) are
    present.

    Returns:
        The validated namespace string, unchanged.

    Raises:
        EndorValidationError: If *ns* does not match the allowed pattern.
    """
    if not _NAMESPACE_RE.match(ns):
        raise EndorValidationError(f"Invalid namespace format: {ns!r}")
    return ns


@functools.lru_cache(maxsize=1)
def _load_generated_mutability_by_resource_name() -> dict[str, dict[str, list[str]]]:
    resources: list[dict[str, Any]] = []
    try:
        from ..generated.registry_contract import RUNTIME_REGISTRY_CONTRACT
    except Exception as error:
        raise RuntimeError(
            "Missing generated runtime registry contract; run devtools/model_sync.py"
        ) from error
    candidate = RUNTIME_REGISTRY_CONTRACT.get("resources")
    if isinstance(candidate, list):
        candidate_resources = cast("list[object]", candidate)
        resources.extend(
            cast("dict[str, Any]", item)
            for item in candidate_resources
            if isinstance(item, dict)
        )

    mutability: dict[str, dict[str, list[str]]] = {}
    for resource in resources:
        resource_name = resource.get("resource_name")
        immutable_fields = resource.get("immutable_fields")
        mutable_fields = resource.get("mutable_fields")
        if (
            isinstance(resource_name, str)
            and isinstance(immutable_fields, list)
            and isinstance(mutable_fields, list)
        ):
            immutable_items = cast("list[object]", immutable_fields)
            immutable_values = [
                value for value in immutable_items if isinstance(value, str)
            ]
            mutable_items = cast("list[object]", mutable_fields)
            mutable_values = [
                value for value in mutable_items if isinstance(value, str)
            ]

            mutability[resource_name] = {
                "immutable_fields": sorted(immutable_values),
                "mutable_fields": sorted(mutable_values),
            }
    return mutability


class BaseResourceOperations(Generic[T]):
    """Base class providing CRUD operations for all resources."""

    def __init__(
        self,
        client: "APIClient",
        resource_name: str,
        model_class: type[T],
    ) -> None:
        super().__init__()
        self.client = client
        self.resource_name = resource_name
        self.model_class = model_class
        self.logger = get_resource_logger(f"{__name__}.{resource_name}")

    def _dump_for_api(
        self, model: BaseModel, exclude_none: bool = True
    ) -> dict[str, Any]:
        """Serialize model to dict for API request body.

        Single path for model-to-dict so all payloads use mode='json' and
        warnings=False, avoiding Pydantic serializer warnings for nested
        meta/spec/tenant_meta.
        """
        return model.model_dump(
            exclude_none=exclude_none, mode="json", warnings=False, by_alias=True
        )

    def dump_for_api(
        self, model: BaseModel, exclude_none: bool = True
    ) -> dict[str, Any]:
        """Public API to serialize a model to dict for request body (e.g. PATCH)."""
        return self._dump_for_api(model, exclude_none=exclude_none)

    def _to_request_body(
        self,
        resource: BaseModel,
        update_mask: builtins.list[str] | None,
        resource_uuid: str,
    ) -> dict[str, Any]:
        """Build the PATCH request 'object' dict from a resource model.

        Uses _dump_for_api then ensures uuid and applies sparse build when
        update_mask is present.
        """
        payload_dict = self._dump_for_api(resource)
        if "uuid" not in payload_dict:
            payload_dict["uuid"] = resource_uuid
        if update_mask:
            payload_dict = self._build_sparse_update_object(
                payload_dict, update_mask, resource_uuid
            )
        return payload_dict

    def _validate_payload(
        self, payload: BaseModel, operation: str, namespace: str
    ) -> BaseModel:
        """Pre-validate payload before API call.

        Validates the payload using Pydantic's model_validate to catch
        client-side validation errors before making API requests.

        Args:
            payload: Pydantic model instance to validate
            operation: Operation name (e.g., 'create', 'update')
            namespace: Namespace where operation will be performed

        Returns:
            Validated payload (same instance if valid)

        Raises:
            EndorValidationError: If payload validation fails

        """
        try:
            # Re-validate the payload to catch any issues
            # This ensures type safety and catches validation errors early
            validated = payload.model_validate(self._dump_for_api(payload))
            return validated
        except ValidationError as e:
            # Convert Pydantic ValidationError to our ValidationError
            raise EndorValidationError(
                message=f"Invalid payload for {operation} operation",
                operation=operation,
                namespace=namespace,
            ) from e

    @staticmethod
    def _build_sparse_update_object(
        payload_dict: dict[str, Any],
        update_mask: list[str],
        resource_uuid: str,
    ) -> dict[str, Any]:
        """Build a minimal request object containing only uuid and masked paths.

        Used when update_mask is present so the API receives only the fields
        being updated (sparse PATCH), not the full resource body.

        Args:
            payload_dict: Full payload as dict (nested).
            update_mask: List of field paths (e.g. ["meta.tags", "spec.finding_tags"]).
            resource_uuid: UUID to set in the result if not in payload.

        Returns:
            Dict with "uuid" and only the nested values for paths in update_mask.
            Paths missing in payload_dict are skipped (no KeyError).

        """
        result: dict[str, Any] = {
            "uuid": payload_dict.get("uuid", resource_uuid),
        }
        for path in update_mask:
            parts = path.strip().split(".")
            try:
                value: Any = payload_dict
                for key in parts:
                    value = value[key]
            except (KeyError, TypeError):
                continue
            target = result
            for key in parts[:-1]:
                if key not in target:
                    target[key] = {}
                target = target[key]
            target[parts[-1]] = value
        return result

    def list(
        self,
        tenant_meta_namespace: str,
        list_params: ListParameters | None = None,
        max_pages: int | None = None,
        **kwargs: Any,
    ) -> list[T] | list[dict[str, Any]]:
        """Universal list operation with automatic pagination.

        Args:
            tenant_meta_namespace: Namespace to list resources from
            list_params: Optional list parameters (filter, page_size, etc.)
            max_pages: Optional maximum number of pages to fetch.
                If None and in test environment, defaults to 10 pages max.
                If None in production, fetches all pages.
            **kwargs: Additional keyword arguments (e.g. filter, page_size).

        Returns:
            List of resource objects, or shallow-copied wire JSON dicts per row
            when ``list_parameters_has_nonempty_field_mask(list_params)`` is True.

        """
        kwargs.pop("logging_level", None)  # Session-level only; ignore if passed
        try:
            ns = validate_namespace(tenant_meta_namespace)
            url = f"v1/namespaces/{ns}/{self.resource_name}"

            traverse = getattr(list_params, "traverse", None) if list_params else None
            self.logger.info(
                "Listing %s in namespace %s (traverse=%s, max_pages=%s).",
                self.resource_name,
                tenant_meta_namespace,
                traverse,
                max_pages,
            )

            # Build query parameters once
            params = self._build_params(list_params, **kwargs)

            # Use get_all() for pagination instead of manual loop
            all_items = list(
                self.client.get_all(
                    url,
                    params=params,
                    max_pages=max_pages,
                )
            )

            self.logger.info(
                "Listed %s %s.",
                len(all_items),
                self.resource_name,
            )
            self.logger.debug(
                "Fetched %s %s items from namespace '%s'",
                len(all_items),
                self.resource_name,
                tenant_meta_namespace,
            )

        except EndorAPIError as e:
            # Re-raise our custom exceptions
            raise e from None
        except httpx.HTTPStatusError as e:
            # Map HTTP errors to typed exceptions
            raise self.client.map_http_error_to_exception(
                e, "list", tenant_meta_namespace
            ) from e
        except Exception as e:
            # Unexpected errors
            from ..core.exceptions import ServerError

            raise ServerError(
                message=(
                    f"Unexpected error listing {self.resource_name} "
                    f"in namespace '{tenant_meta_namespace}': {e!s}"
                ),
                operation="list",
                namespace=tenant_meta_namespace,
            ) from e

        if list_parameters_has_nonempty_field_mask(list_params):
            return [dict(item) for item in all_items]

        try:
            return [self.model_class(**item) for item in all_items]
        except ValidationError as e:
            # Pydantic validation error on response (full-model path only)
            from ..core.exceptions import ServerError

            error_details = "\n".join(
                f"  {err['loc']}: {err['msg']} (type: {err['type']})"
                for err in e.errors()
            )
            raise ServerError(
                message=(
                    f"Response validation failed for {self.resource_name} "
                    f"in namespace '{tenant_meta_namespace}'. "
                    f"Validation details:\n{error_details}"
                ),
                operation="list",
                namespace=tenant_meta_namespace,
                response_text=str(e.errors()),
            ) from e

    def list_iter(
        self,
        tenant_meta_namespace: str,
        list_params: ListParameters | None = None,
        max_pages: int | None = None,
        **kwargs: Any,
    ) -> Iterator[T | dict[str, Any]]:
        """Yield resources from a paginated list without materializing the full list.

        Same URL and params as list(). Yields one full model per item unless a
        non-empty field mask is in effect, in which case each item is a shallow
        copy of the wire JSON dict.
        """
        kwargs.pop("logging_level", None)  # Session-level only; ignore if passed
        ns = validate_namespace(tenant_meta_namespace)
        url = f"v1/namespaces/{ns}/{self.resource_name}"
        params = self._build_params(list_params, **kwargs)
        masked = list_parameters_has_nonempty_field_mask(list_params)
        for item in self.client.get_all(url, params=params, max_pages=max_pages):
            if masked:
                yield dict(item)
            else:
                yield self.model_class(**item)

    def get(self, tenant_meta_namespace: str, resource_uuid: str) -> T:
        """Universal get operation with fallback to list+filter.

        Raises:
            NotFoundError: If resource doesn't exist
            PermissionDeniedError: If user lacks permission
            ServerError: If server error occurs

        """
        ns = validate_namespace(tenant_meta_namespace)
        try:
            # Method 1: Try direct UUID access first (fastest if it works)
            res = self.client.get(
                f"v1/namespaces/{ns}/{self.resource_name}/{resource_uuid}"
            )
            data = res.json()
            return self.model_class(**data)
        except EndorAPIError as e:
            # Re-raise our custom exceptions
            raise e from None
        except httpx.HTTPStatusError as e:
            # For 404, try fallback method; for other errors, raise immediately
            if e.response.status_code == 404:
                # 404 is expected when falling back, use debug level
                self.logger.debug(
                    "Direct %s access returned an error for UUID "
                    "'%s' in namespace '%s'. Falling back to list+filter approach.",
                    self.resource_name,
                    resource_uuid,
                    tenant_meta_namespace,
                )
            else:
                # Other HTTP errors - raise immediately
                raise self.client.map_http_error_to_exception(
                    e, "get", tenant_meta_namespace, resource_uuid=resource_uuid
                ) from e
        except Exception as e:
            # For non-HTTP errors, try fallback
            self.logger.debug(
                "Direct %s access returned an error for UUID "
                "'%s' in namespace '%s': %s. Falling back to list+filter approach.",
                self.resource_name,
                resource_uuid,
                tenant_meta_namespace,
                e,
            )

        # Method 2: Use list and filter approach (workaround)
        try:
            list_params = ListParameters(  # pyright: ignore[reportCallIssue]
                filter=f"uuid=={resource_uuid}",
                traverse=True,  # Enable traversal to search child namespaces
            )
            resources = self.list(tenant_meta_namespace, list_params)
            if resources:
                return cast("T", resources[0])
            # No resources found - raise NotFoundError
            from ..core.exceptions import NotFoundError

            raise NotFoundError(
                message=(
                    f"{self.resource_name} with UUID '{resource_uuid}' "
                    f"not found in namespace '{tenant_meta_namespace}'"
                ),
                operation="get",
                namespace=tenant_meta_namespace,
                resource_uuid=resource_uuid,
            )
        except EndorAPIError as e:
            # Re-raise our custom exceptions
            raise e from None
        except httpx.HTTPStatusError as e:
            # Map HTTP errors to typed exceptions
            raise self.client.map_http_error_to_exception(
                e, "get", tenant_meta_namespace, resource_uuid=resource_uuid
            ) from e
        except Exception as e:
            # Unexpected errors
            from ..core.exceptions import ServerError

            raise ServerError(
                message=(
                    f"Unexpected error getting {self.resource_name} "
                    f"UUID '{resource_uuid}': {e!s}"
                ),
                operation="get",
                namespace=tenant_meta_namespace,
                resource_uuid=resource_uuid,
            ) from e

    def create(self, tenant_meta_namespace: str, payload: BaseModel) -> T:
        """Universal create operation with pre-validation and typed errors.

        Optional: set ENDOR_CREATE_TIMEOUT (seconds) in the environment to use
        a request timeout for create calls (e.g. 60 for slow endpoints like
        scan-log-requests).

        Raises:
            EndorValidationError: If payload validation fails
            NotFoundError: If namespace doesn't exist
            PermissionDeniedError: If user lacks permission
            ConflictError: If resource already exists
            ServerError: If server error occurs

        """
        # Pre-validate payload before API call
        validated_payload = self._validate_payload(
            payload, "create", tenant_meta_namespace
        )

        ns = validate_namespace(tenant_meta_namespace)
        try:
            url = f"v1/namespaces/{ns}/{self.resource_name}"

            # Convert payload to dict
            payload_dict = self._dump_for_api(validated_payload)

            # DEBUG: Log request payload
            self.logger.debug(
                "Creating %s in namespace '%s' with payload: %s",
                self.resource_name,
                tenant_meta_namespace,
                payload_dict,
            )

            # Optional create timeout (e.g. for slow endpoints like scan-log-requests)
            create_timeout: int | float | None = None
            env_timeout = os.environ.get("ENDOR_CREATE_TIMEOUT")
            if env_timeout is not None:
                try:
                    create_timeout = int(env_timeout)
                except ValueError:
                    create_timeout = None
            post_kwargs: dict[str, Any] = {}
            if create_timeout is not None:
                post_kwargs["timeout"] = create_timeout

            res = self.client.post(url, json=payload_dict, **post_kwargs)
            data = res.json()

            # Validate response structure
            if not isinstance(data, dict):
                from ..core.exceptions import ServerError

                raise ServerError(
                    message=(
                        f"Invalid response format for {self.resource_name}: "
                        f"expected dict, got {type(data)}"
                    ),
                    operation="create",
                    namespace=tenant_meta_namespace,
                    response_text=str(data),
                )

            data_obj = cast("dict[str, Any]", data)

            if "uuid" not in data_obj:
                self.logger.warning(
                    "Response missing UUID for %s: %s",
                    self.resource_name,
                    data_obj,
                )

            # DEBUG: Log successful response
            self.logger.debug(
                "Successfully created %s: %s",
                self.resource_name,
                data_obj.get("uuid", "unknown"),
            )

            return self.model_class(**data_obj)
        except EndorAPIError as e:
            # Re-raise our custom exceptions
            raise e from None
        except httpx.HTTPStatusError as e:
            # Map HTTP errors to typed exceptions
            raise self.client.map_http_error_to_exception(
                e, "create", tenant_meta_namespace
            ) from e
        except ValidationError as e:
            # Pydantic validation error on response
            from ..core.exceptions import ServerError

            raise ServerError(
                message=(
                    f"Response validation failed for {self.resource_name} "
                    f"in namespace '{tenant_meta_namespace}'"
                ),
                operation="create",
                namespace=tenant_meta_namespace,
                response_text=str(e.errors()),
            ) from e
        except Exception as e:
            # Unexpected errors
            from ..core.exceptions import ServerError

            raise ServerError(
                message=f"Unexpected error creating {self.resource_name}: {e!s}",
                operation="create",
                namespace=tenant_meta_namespace,
            ) from e

    def update(
        self,
        tenant_meta_namespace: str,
        resource_uuid: str,
        payload: BaseModel,
        update_mask: builtins.list[str],
    ) -> T:
        """Universal update operation with field masking and pre-validation.

        update_mask is required and must contain at least one field path; sparse
        PATCH is always used so the full object is never sent.

        Raises:
            EndorValidationError: If payload validation fails or update_mask is
                empty or contains immutable fields
            NotFoundError: If resource doesn't exist
            PermissionDeniedError: If user lacks permission
            ServerError: If server error occurs

        """
        if not update_mask:
            raise EndorValidationError(
                message=(
                    f"{self.resource_name} update requires a non-empty update_mask "
                    "(e.g. ['meta.description', 'meta.tags'])."
                ),
                operation="update",
                namespace=tenant_meta_namespace,
                resource_uuid=resource_uuid,
            )

        # Pre-validate payload before API call
        validated_payload = self._validate_payload(
            payload, "update", tenant_meta_namespace
        )

        # Block immutable fields in update_mask from generated contract metadata.
        mutability_by_resource = _load_generated_mutability_by_resource_name()
        immutable: list[str] = mutability_by_resource.get(self.resource_name, {}).get(
            "immutable_fields", []
        )
        if not immutable:
            raise EndorValidationError(
                message=(
                    "Resource mutability metadata missing from generated contract "
                    f"for '{self.resource_name}'."
                ),
                operation="update",
                namespace=tenant_meta_namespace,
                resource_uuid=resource_uuid,
            )
        for path in update_mask:
            if path.strip() in immutable:
                raise EndorValidationError(
                    message=f"Cannot update immutable field: {path.strip()}",
                    operation="update",
                    namespace=tenant_meta_namespace,
                    resource_uuid=resource_uuid,
                )

        ns = validate_namespace(tenant_meta_namespace)
        try:
            # Use collection endpoint (UUID goes in request body, not URL path)
            url = f"v1/namespaces/{ns}/{self.resource_name}"

            # Convert payload to dict (single path: _to_request_body)
            payload_dict = self._to_request_body(
                validated_payload, update_mask, resource_uuid
            )

            # Warn if payload has unmodeled (extra) attributes
            extra = getattr(validated_payload, "__pydantic_extra__", None)
            if extra:
                self.logger.warning(
                    "Unmodeled attributes in update payload: %s",
                    list(extra.keys()),
                )

            # Build request body with object and required update_mask
            request_data: dict[str, Any] = {
                "object": payload_dict,
                "request": {"update_mask": ",".join(update_mask)},
            }

            # DEBUG: Log update request
            self.logger.debug(
                "Updating %s UUID '%s' in namespace '%s' with update_mask: %s",
                self.resource_name,
                resource_uuid,
                tenant_meta_namespace,
                update_mask,
            )

            res = self.client.patch(url, json=request_data)
            data = res.json()

            # DEBUG: Log successful update
            self.logger.debug(
                "Successfully updated %s UUID '%s'",
                self.resource_name,
                resource_uuid,
            )

            return self.model_class(**data)

        except EndorAPIError as e:
            # Re-raise our custom exceptions
            raise e from None
        except httpx.HTTPStatusError as e:
            # Map HTTP errors to typed exceptions
            raise self.client.map_http_error_to_exception(
                e, "update", tenant_meta_namespace, resource_uuid=resource_uuid
            ) from e
        except ValidationError as e:
            # Pydantic validation error on response
            from ..core.exceptions import ServerError

            raise ServerError(
                message=(
                    f"Response validation failed for {self.resource_name} UUID "
                    f"'{resource_uuid}' in namespace '{tenant_meta_namespace}'"
                ),
                operation="update",
                namespace=tenant_meta_namespace,
                resource_uuid=resource_uuid,
                response_text=str(e.errors()),
            ) from e
        except Exception as e:
            # Unexpected errors
            from ..core.exceptions import ServerError

            raise ServerError(
                message=(
                    f"Unexpected error updating {self.resource_name} "
                    f"UUID '{resource_uuid}': {e!s}"
                ),
                operation="update",
                namespace=tenant_meta_namespace,
                resource_uuid=resource_uuid,
            ) from e

    def delete(self, tenant_meta_namespace: str, resource_uuid: str) -> bool:
        """Universal delete operation.

        Returns:
            True if deletion was successful (status 200 or 204)

        Raises:
            NotFoundError: If resource doesn't exist
            PermissionDeniedError: If user lacks permission
            ServerError: If server error occurs

        """
        ns = validate_namespace(tenant_meta_namespace)
        try:
            url = f"v1/namespaces/{ns}/{self.resource_name}/{resource_uuid}"

            res = self.client.delete(url)

            # Check if deletion was successful (204 No Content or 200 OK)
            if res.status_code in [200, 204]:
                return True
            # Unexpected status code - raise error
            from ..core.exceptions import ServerError

            raise ServerError(
                message=(
                    f"Unexpected status code {res.status_code} "
                    f"when deleting {self.resource_name} UUID '{resource_uuid}'"
                ),
                status_code=res.status_code,
                operation="delete",
                namespace=tenant_meta_namespace,
                resource_uuid=resource_uuid,
            )

        except EndorAPIError as e:
            # Re-raise our custom exceptions
            raise e from None
        except httpx.HTTPStatusError as e:
            # Map HTTP errors to typed exceptions
            raise self.client.map_http_error_to_exception(
                e, "delete", tenant_meta_namespace, resource_uuid=resource_uuid
            ) from e
        except Exception as e:
            # Unexpected errors
            from ..core.exceptions import ServerError

            raise ServerError(
                message=(
                    f"Unexpected error deleting {self.resource_name} "
                    f"UUID '{resource_uuid}': {e!s}"
                ),
                operation="delete",
                namespace=tenant_meta_namespace,
                resource_uuid=resource_uuid,
            ) from e

    def count(
        self, tenant_meta_namespace: str, list_params: ListParameters | None = None
    ) -> int:
        """Count resources matching filter criteria.

        Raises:
            EndorAPIError: On API errors (same hierarchy as list()).
        """
        ns = validate_namespace(tenant_meta_namespace)
        try:
            # Create count-specific list parameters
            if list_params:
                count_params = list_params.model_copy(update={"count": True})
            else:
                count_params = ListParameters(count=True)  # pyright: ignore[reportCallIssue]

            url = f"v1/namespaces/{ns}/{self.resource_name}"

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

        except EndorAPIError:
            raise
        except httpx.HTTPStatusError as e:
            raise self.client.map_http_error_to_exception(
                e, "count", tenant_meta_namespace
            ) from e
        except Exception as e:
            from ..core.exceptions import ServerError

            raise ServerError(
                message=(
                    f"Unexpected error counting {self.resource_name} "
                    f"in namespace '{tenant_meta_namespace}': {e!s}"
                ),
                operation="count",
                namespace=tenant_meta_namespace,
            ) from e

    def _build_params(
        self, list_params: ListParameters | None, **kwargs: Any
    ) -> dict[str, Any]:
        """Build query parameters from list_params and kwargs."""
        params: dict[str, Any] = {}

        if list_params:
            self._add_basic_params(params, list_params)
            self._add_pagination_params(params, list_params)
            self._add_sorting_params(params, list_params)
            self._add_boolean_params(params, list_params)
            self._add_date_params(params, list_params)
            self._add_extra_list_params(params, list_params)
            self._add_group_params(params, list_params)

        # Add any additional kwargs
        params.update(kwargs)

        return params

    def _add_basic_params(
        self, params: dict[str, Any], list_params: ListParameters
    ) -> None:
        """Add basic filter and mask parameters."""
        if list_params.filter:
            params["list_parameters.filter"] = list_params.filter
        if list_params.mask:
            params["list_parameters.mask"] = list_params.mask

    def _add_pagination_params(
        self, params: dict[str, Any], list_params: ListParameters
    ) -> None:
        """Add pagination-related parameters.

        Note: page_size is only added if explicitly set. If None, the API
        will use its default page size (typically 100). This is intentional
        to avoid performance issues with small page sizes.
        """
        # Only add page_size if explicitly set (don't override API default)
        if list_params.page_size is not None:
            params["list_parameters.page_size"] = str(list_params.page_size)
        if list_params.page_token:
            params["list_parameters.page_token"] = list_params.page_token
        if list_params.page_id:
            params["list_parameters.page_id"] = list_params.page_id

    def _add_sorting_params(
        self, params: dict[str, Any], list_params: ListParameters
    ) -> None:
        """Add sorting-related parameters.

        API expects list_parameters.sort.path and list_parameters.sort.order
        (enum: SORT_ENTRY_ORDER_ASC, SORT_ENTRY_ORDER_DESC).
        Prefer sort_by + desc; fall back to sort_field + sort_order with normalization.
        """
        path: str | None = None
        order: str | None = None
        if list_params.sort_by:
            path = list_params.sort_by
            order = (
                "SORT_ENTRY_ORDER_DESC" if list_params.desc else "SORT_ENTRY_ORDER_ASC"
            )
        elif list_params.sort_field:
            import warnings

            warnings.warn(
                "sort_field/sort_order are deprecated; use sort_by/desc instead.",
                DeprecationWarning,
                stacklevel=4,
            )
            path = list_params.sort_field
            raw = (list_params.sort_order or "asc").lower()
            order = (
                "SORT_ENTRY_ORDER_DESC"
                if raw in ("desc", "descending")
                else "SORT_ENTRY_ORDER_ASC"
            )
        if path:
            params["list_parameters.sort.path"] = path
        if order:
            params["list_parameters.sort.order"] = order

    def _add_boolean_params(
        self, params: dict[str, Any], list_params: ListParameters
    ) -> None:
        """Add boolean parameters."""
        if list_params.count is not None:
            params["list_parameters.count"] = str(list_params.count).lower()

        # Handle traverse parameter (canonical way to traverse namespaces)
        if list_params.traverse is not None:
            # API uses 'list_parameters.traverse' as the query parameter
            params["list_parameters.traverse"] = str(list_params.traverse).lower()
        if list_params.archive is not None:
            params["list_parameters.archive"] = str(list_params.archive).lower()
        if list_params.list_all is not None:
            params["list_parameters.list_all"] = str(list_params.list_all).lower()

    def _add_extra_list_params(
        self, params: dict[str, Any], list_params: ListParameters
    ) -> None:
        """Add PR / CI-run scoping (OpenAPI: list_parameters.ci_run_uuid)."""
        wire = list_params.ci_run_uuid or list_params.pr_uuid
        if wire:
            params["list_parameters.ci_run_uuid"] = wire

    def _add_group_params(
        self, params: dict[str, Any], list_params: ListParameters
    ) -> None:
        """Add grouping/aggregation list parameters."""
        if list_params.group_aggregation_paths:
            params["list_parameters.group_aggregation_paths"] = ",".join(
                list_params.group_aggregation_paths
            )
        if list_params.group_by_time is not None:
            params["list_parameters.group_by_time"] = str(
                list_params.group_by_time
            ).lower()
        if list_params.group_by_time_field_value:
            params["list_parameters.group_by_time_field_value"] = (
                list_params.group_by_time_field_value
            )
        if list_params.group_by_time_interval:
            params["list_parameters.group_by_time_interval"] = (
                list_params.group_by_time_interval
            )
        if list_params.group_by_time_mode:
            params["list_parameters.group_by_time_mode"] = (
                list_params.group_by_time_mode
            )
        if list_params.group_by_time_operator:
            params["list_parameters.group_by_time_operator"] = (
                list_params.group_by_time_operator
            )
        if list_params.group_show_aggregation_uuids is not None:
            params["list_parameters.group_show_aggregation_uuids"] = str(
                list_params.group_show_aggregation_uuids
            ).lower()
        if list_params.group_unique_count_paths:
            params["list_parameters.group_unique_count_paths"] = ",".join(
                list_params.group_unique_count_paths
            )
        if list_params.group_unique_value_paths:
            params["list_parameters.group_unique_value_paths"] = ",".join(
                list_params.group_unique_value_paths
            )

    def _add_date_params(
        self, params: dict[str, Any], list_params: ListParameters
    ) -> None:
        """Add date-related parameters."""
        if list_params.from_date:
            params["list_parameters.from_date"] = list_params.from_date
        if list_params.to_date:
            params["list_parameters.to_date"] = list_params.to_date
