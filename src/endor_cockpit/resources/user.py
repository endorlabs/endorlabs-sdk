"""
User resource module for Endor Labs API.

This module provides CRUD operations for User resources following the
established patterns from the base class implementation.

API OPERATIONS SUPPORTED:
- GET: List users, Get user by UUID

API LIMITATIONS:
- CREATE: Not supported by API (users managed by identity provider)
- UPDATE: Not supported by API (user data is read-only)
- DELETE: Not supported by API (users managed by identity provider)

Note: Users are automatically synchronized from identity providers and cannot
be manually created, updated, or deleted through the API.
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional

import requests
from pydantic import BaseModel, ConfigDict, Field, field_validator

from ..api_client import APIClient, RedactingFilter, redaction_pattern
from ..models.base import BaseMeta, BaseResource, BaseResourceOperations, BaseSpec
from ..types import ListParameters

# Set up logger with redaction filter
logger = logging.getLogger(__name__)
logger.addFilter(RedactingFilter([redaction_pattern]))


class Events(BaseModel):
    """User events for tracking."""

    event_type: str = Field(..., description="Event type")
    count: int = Field(..., description="Event count")
    last_occurrence: Optional[datetime] = Field(
        None, description="Last occurrence time"
    )


class UserMeta(BaseMeta):
    """User metadata extending BaseMeta."""

    # User-specific fields only (universal fields inherited from BaseMeta)
    pass


class UserSpec(BaseSpec):
    """User specification extending BaseSpec.

    Field Mutability Guide:
    ======================

    IMMUTABLE FIELDS (cannot be updated after creation):
    - user_name: Username (read-only, derived from token)
    - last_login_time: Last login time (read-only, system-managed)
    - token_hash: Token hash (system-managed)

    MUTABLE FIELDS (can be updated via API):
    - first_name: First name (user can change)
    - last_name: Last name (user can change)
    - email: Email (user can change)
    - event_tracking: Event tracking (system-managed)
    - groups: Groups (system-managed)
    """

    user_name: Optional[str] = Field(
        None,
        description="Username automatically derived from the token",
    )  # IMMUTABLE: Read-only
    first_name: Optional[str] = Field(
        None, description="First name of the user as identified. It can be changed"
    )  # MUTABLE: User can change
    last_name: Optional[str] = Field(
        None, description="Last name of the user. It can be changed"
    )  # MUTABLE: User can change
    email: Optional[str] = Field(
        None, description="Email of the user. It can be changed"
    )  # MUTABLE: User can change
    last_login_time: Optional[datetime] = Field(
        None,
        description="Record of the last time the user logged in",
    )  # IMMUTABLE: Read-only
    event_tracking: Optional[Dict[str, Events]] = Field(
        None, description="Lists of user events indexed by event type"
    )  # MUTABLE: System-managed
    token_hash: Optional[str] = Field(
        None, description="The hash of the last token issued to the user"
    )  # IMMUTABLE: System-managed
    groups: Optional[List[str]] = Field(
        None,
        description="Groups user is member of, from identity provider claims",
    )  # MUTABLE: System-managed

    @field_validator("event_tracking", mode="before")
    @classmethod
    def validate_event_tracking(cls, v):
        """Handle event tracking validation."""
        if isinstance(v, dict):
            validated_events = {}
            for key, value in v.items():
                if isinstance(value, dict):
                    validated_events[key] = Events(**value)
                else:
                    validated_events[key] = value
            return validated_events
        return v


class User(BaseResource):
    """
    User resource model extending BaseResource.

    OPERATION SUPPORT:
    ==================
    ✅ GET: List users, Get by UUID
    ❌ CREATE: Not supported (managed by identity provider)
    ❌ UPDATE: Not supported (user data is read-only)
    ❌ DELETE: Not supported (managed by identity provider)

    FIELD MUTABILITY:
    =================
    IMMUTABLE FIELDS (read-only, system-managed):
    - uuid: Unique identifier
    - meta.name: User name (derived from token)
    - spec.user_name: Username (derived from token)
    - spec.last_login_time: Last login time (system-managed)
    - spec.token_hash: Token hash (system-managed)
    - spec.groups: User groups (from identity provider)
    - tenant_meta.namespace: Namespace assignment
    - All spec fields: Identity provider-managed data

    Note: Users are automatically synchronized from identity providers and cannot
    be manually created, updated, or deleted through the API.
    """

    # User-specific fields (universal fields inherited from BaseResource)
    spec: UserSpec = Field(..., description="User specification")  # type: ignore

    model_config = ConfigDict(extra="ignore")

    def __init__(self, **data):
        # Convert spec to UserSpec if it's a dict
        if "spec" in data and isinstance(data["spec"], dict):
            data["spec"] = UserSpec(**data["spec"])
        super().__init__(**data)

    @field_validator("*", mode="before")
    @classmethod
    def detect_schema_drift(cls, v, info):
        """Detect and log schema drift for unknown fields."""
        if info.field_name == "spec" and isinstance(v, dict):
            # Log unknown fields for schema drift detection in spec
            known_fields = {
                "user_name",
                "first_name",
                "last_name",
                "email",
                "last_login_time",
                "event_tracking",
                "token_hash",
                "groups",
            }
            unknown_fields = set(v.keys()) - known_fields
            if unknown_fields:
                logger.warning(
                    f"Schema drift detected in {info.field_name}: "
                    f"unknown fields {unknown_fields}"
                )
        return v


def _get_user_ops(client: APIClient) -> BaseResourceOperations:
    """Get BaseResourceOperations instance for User."""
    return BaseResourceOperations(client, "users", User)


def list_users(
    client: APIClient,
    tenant_meta_namespace: str,
    list_params: Optional[ListParameters] = None,
    **kwargs,
) -> List[User]:
    """List users with advanced filtering and pagination.
    
    Note: Users are accessed via /v1/users (not namespaced), so the
    tenant_meta_namespace parameter is ignored but kept for API consistency.
    """
    # Users are accessed via /v1/users, not /v1/namespaces/{namespace}/users
    url = "v1/users"
    
    # Build query parameters
    params = {}
    if list_params:
        if list_params.filter:
            params["filter"] = list_params.filter
        if list_params.page_size:
            params["page_size"] = list_params.page_size
        if list_params.page_token:
            params["page_token"] = list_params.page_token
        if list_params.sort_field:
            params["sort_field"] = list_params.sort_field
        if list_params.sort_order:
            params["sort_order"] = list_params.sort_order
    
    all_items = []
    page_token = None
    
    while True:
        if page_token:
            params["page_token"] = page_token
        
        try:
            res = client.get(url, params=params)
            data = res.json()
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 403:
                logger.warning(
                    "Access denied to users endpoint (403 Forbidden). "
                    "This may be a permissions issue. Users may require "
                    "special permissions to access."
                )
                break
            else:
                raise
        
        # Extract items from response
        if "list" in data and "objects" in data["list"]:
            items = data["list"]["objects"]
        elif isinstance(data, list):
            items = data
        else:
            items = []
        
        all_items.extend(items)
        
        # Check for next page token
        if isinstance(data, dict) and "list" in data:
            list_data = data["list"]
            if isinstance(list_data, dict) and "response" in list_data:
                response_data = list_data["response"]
                if isinstance(response_data, dict):
                    page_token = response_data.get("next_page_token")
                else:
                    page_token = None
            else:
                page_token = None
        else:
            page_token = None
        
        if not page_token:
            break
    
    # Convert to User objects
    users = []
    for item in all_items:
        try:
            users.append(User(**item))
        except Exception as e:
            logger.warning(f"Failed to parse user: {e}")
            continue
    
    return users


def get_user(
    client: APIClient, tenant_meta_namespace: str, user_uuid: str
) -> Optional[User]:
    """Get specific user by UUID.
    
    Note: Users are accessed via /v1/users/{uuid} (not namespaced), so the
    tenant_meta_namespace parameter is ignored but kept for API consistency.
    """
    # Users are accessed via /v1/users/{uuid}, not /v1/namespaces/{namespace}/users/{uuid}
    url = f"v1/users/{user_uuid}"
    
    try:
        res = client.get(url)
        data = res.json()
        
        # Handle both direct object and wrapped response
        if "object" in data:
            user_data = data["object"]
        else:
            user_data = data
        
        return User(**user_data)
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 403:
            logger.warning(
                f"Access denied to users endpoint (403 Forbidden). "
                f"This may be a permissions issue."
            )
        elif e.response.status_code == 404:
            logger.debug(f"User {user_uuid} not found")
        else:
            logger.error(f"Failed to get user {user_uuid}: {e}")
        return None
    except Exception as e:
        logger.error(f"Failed to get user {user_uuid}: {e}")
        return None


def create_user(
    client: APIClient,
    tenant_meta_namespace: str,
    payload: "CreateUserPayload",
) -> Optional[User]:
    """Create a new user."""
    ops = _get_user_ops(client)
    return ops.create(tenant_meta_namespace, payload)  # type: ignore


def update_user(
    client: APIClient,
    tenant_meta_namespace: str,
    user_uuid: str,
    payload: "UpdateUserPayload",
    update_mask: Optional[List[str]] = None,
) -> Optional[User]:
    """Update an existing user with partial updates."""
    ops = _get_user_ops(client)
    return ops.update(tenant_meta_namespace, user_uuid, payload, update_mask)  # type: ignore


def delete_user(client: APIClient, tenant_meta_namespace: str, user_uuid: str) -> bool:
    """Delete a user by UUID."""
    ops = _get_user_ops(client)
    return ops.delete(tenant_meta_namespace, user_uuid)  # type: ignore


# Payload models for create and update operations
class CreateUserPayload(BaseModel):
    """Payload for creating a user."""

    meta: "UserMetaCreate" = Field(..., description="User metadata for creation")
    spec: UserSpec = Field(..., description="User specification")


class UpdateUserPayload(BaseModel):
    """Payload for updating a user."""

    meta: Optional["UserMetaUpdate"] = Field(
        None, description="User metadata for update"
    )
    spec: Optional[UserSpec] = Field(None, description="User specification for update")


class UserMetaCreate(BaseModel):
    """User metadata for creation."""

    name: str = Field(..., description="User name")
    description: Optional[str] = Field(None, description="User description")


class UserMetaUpdate(BaseModel):
    """User metadata for update."""

    description: Optional[str] = Field(None, description="User description")
