"""
Policy resource module for Endor Labs API.

This module provides comprehensive policy management capabilities including
listing, examining, creating, updating, and deleting policies.
"""

import logging
from datetime import datetime
from enum import Enum
from typing import List, Optional, Union, Dict, Any
from pydantic import BaseModel, Field, field_validator

from ..api_client import APIClient

logger = logging.getLogger(__name__)


class PolicyType(str, Enum):
    """Policy type enumeration."""
    SYSTEM_FINDING = "POLICY_TYPE_SYSTEM_FINDING"
    USER_FINDING = "POLICY_TYPE_USER_FINDING"
    ADMISSION = "POLICY_TYPE_ADMISSION"
    ML_FINDING = "POLICY_TYPE_ML_FINDING"
    NOTIFICATION = "POLICY_TYPE_NOTIFICATION"


class PolicyRule(BaseModel):
    """Policy rule configuration."""
    action: str = Field(..., description="Rule action (ALLOW, DENY, WARN)")
    condition: str = Field(..., description="Rule condition")
    effect: str = Field(..., description="Rule effect")
    priority: int = Field(..., description="Rule priority")
    description: str = Field(..., description="Rule description")


class PolicySpec(BaseModel):
    """Policy specification."""
    policy_type: PolicyType = Field(..., description="Policy type")
    rule: Optional[str] = Field(None, description="Policy rule in text format")
    project_selector: Optional[List[str]] = Field(None, description="Project selector tags")
    project_exceptions: Optional[List[str]] = Field(None, description="Project exception tags")
    resource_kinds: Optional[List[str]] = Field(None, description="Resource kinds")
    disable: Optional[bool] = Field(False, description="Whether policy is disabled")
    finding: Optional[Dict[str, Any]] = Field(None, description="Finding configuration")
    finding_level: Optional[str] = Field(None, description="Finding level")
    query_statements: Optional[List[str]] = Field(None, description="Query statements")
    template_uuid: Optional[str] = Field(None, description="Template UUID")
    template_version: Optional[str] = Field(None, description="Template version")
    template_parameters: Optional[List[Dict[str, Any]]] = Field(None, description="Template parameters")
    template_values: Optional[Dict[str, Any]] = Field(None, description="Template values")
    admission: Optional[Dict[str, Any]] = Field(None, description="Admission configuration")
    group_by_fields: Optional[List[str]] = Field(None, description="Group by fields")
    notification: Optional[Dict[str, Any]] = Field(None, description="Notification configuration")


class PolicyMeta(BaseModel):
    """Policy metadata."""
    name: str = Field(..., description="Policy name")
    description: str = Field(..., description="Policy description")
    kind: str = Field("Policy", description="Resource kind")
    tags: Optional[List[str]] = Field(None, description="Policy tags")
    create_time: Optional[str] = Field(None, description="Creation timestamp")
    update_time: Optional[str] = Field(None, description="Update timestamp")
    created_by: Optional[str] = Field(None, description="Created by")
    updated_by: Optional[str] = Field(None, description="Updated by")
    version: Optional[str] = Field("v1", description="Policy version")
    index_data: Optional[Dict[str, Any]] = Field(None, description="Index data")
    annotations: Optional[Dict[str, str]] = Field(None, description="Annotations")
    parent_uuid: Optional[str] = Field(None, description="Parent UUID")
    parent_kind: Optional[str] = Field(None, description="Parent kind")
    upsert_time: Optional[str] = Field(None, description="Upsert timestamp")
    references: Optional[Union[List[Dict[str, Any]], Dict[str, Any]]] = Field(None, description="References")


class TenantMeta(BaseModel):
    """Tenant metadata."""
    namespace: str = Field(..., description="Tenant namespace")


class Policy(BaseModel):
    """Policy resource model."""
    uuid: str = Field(..., description="Policy UUID")
    tenant_meta: TenantMeta = Field(..., description="Tenant metadata")
    meta: PolicyMeta = Field(..., description="Policy metadata")
    spec: PolicySpec = Field(..., description="Policy specification")
    propagate: Optional[bool] = Field(True, description="Propagate to child namespaces")

    @field_validator('*', mode='before')
    def detect_schema_drift(cls, v, info):
        """Detect and log schema drift in policy responses."""
        if info.field_name in ['meta', 'spec', 'tenant_meta'] and isinstance(v, dict):
            # Log unknown fields for schema drift detection
            known_fields = {
                'meta': {'name', 'description', 'kind', 'tags', 'create_time', 'update_time', 
                        'created_by', 'updated_by', 'version', 'index_data', 'annotations'},
                'spec': {'policy_type', 'rule', 'project_selector', 'project_exceptions', 
                        'resource_kinds', 'disable', 'finding', 'finding_level', 'query_statements',
                        'template_uuid', 'template_version', 'template_parameters', 'template_values',
                        'admission', 'group_by_fields'},
                'tenant_meta': {'namespace'}
            }
            
            if info.field_name in known_fields:
                unknown_fields = set(v.keys()) - known_fields[info.field_name]
                if unknown_fields:
                    logger.warning(f"Schema drift detected in {info.field_name}: unknown fields {unknown_fields}")
        
        return v


class CreatePolicyPayload(BaseModel):
    """Payload for creating a new policy."""
    meta: PolicyMeta = Field(..., description="Policy metadata")
    spec: PolicySpec = Field(..., description="Policy specification")
    propagate: Optional[bool] = Field(True, description="Propagate to child namespaces")


class UpdatePolicyPayload(BaseModel):
    """Payload for updating an existing policy."""
    meta: Optional[PolicyMeta] = Field(None, description="Updated policy metadata")
    spec: Optional[PolicySpec] = Field(None, description="Updated policy specification")
    propagate: Optional[bool] = Field(None, description="Propagate to child namespaces")


def list_policies(
    client: APIClient,
    tenant_meta_namespace: str,
    policy_type: Optional[PolicyType] = None
) -> List[Policy]:
    """
    List all policies in a namespace.
    
    Args:
        client: APIClient instance
        tenant_meta_namespace: Tenant namespace (canonical name)
        policy_type: Optional policy type filter
        
    Returns:
        List of Policy objects
    """
    try:
        headers = client.default_headers
        res = client.get(f"v1/namespaces/{tenant_meta_namespace}/policies", headers=headers)
        data = res.json()
        
        # Parse response structure: {"list": {"objects": [...]}}
        objects = data.get("list", {}).get("objects", [])
        
        policies = []
        for obj in objects:
            try:
                policy = Policy(**obj)
                # Apply policy type filter if specified
                if policy_type is None or policy.spec.policy_type == policy_type:
                    policies.append(policy)
            except Exception as e:
                logger.warning(f"Failed to parse policy object: {e}")
                continue
                
        return policies
        
    except Exception as e:
        logger.error(f"Error listing policies: {e}", exc_info=True)
        return []


def get_policy(
    client: APIClient,
    tenant_meta_namespace: str,
    policy_uuid: str
) -> Optional[Policy]:
    """
    Get a specific policy by UUID.
    
    Args:
        client: APIClient instance
        tenant_meta_namespace: Tenant namespace (canonical name)
        policy_uuid: Policy UUID
        
    Returns:
        Policy object or None if not found
    """
    try:
        headers = client.default_headers
        res = client.get(f"v1/namespaces/{tenant_meta_namespace}/policies/{policy_uuid}", headers=headers)
        data = res.json()
        return Policy(**data)
        
    except Exception as e:
        logger.error(f"Error getting policy {policy_uuid}: {e}", exc_info=True)
        return None


def create_policy(
    client: APIClient,
    tenant_meta_namespace: str,
    payload: CreatePolicyPayload
) -> Optional[Policy]:
    """
    Create a new policy in a namespace.
    
    Args:
        client: APIClient instance
        tenant_meta_namespace: Tenant namespace (canonical name)
        payload: Policy creation payload
        
    Returns:
        Created Policy object or None if creation failed
    """
    try:
        headers = client.default_headers
        headers.update({
            "Accept": "application/json",
            "Content-Type": "application/json"
        })
        
        request_data = {
            "meta": payload.meta.model_dump(),
            "spec": payload.spec.model_dump(),
            "propagate": payload.propagate
        }
        
        res = client.post(
            f"v1/namespaces/{tenant_meta_namespace}/policies",
            headers=headers,
            data=request_data
        )
        data = res.json()
        return Policy(**data)
        
    except Exception as e:
        logger.error(f"Error creating policy: {e}", exc_info=True)
        return None


def update_policy(
    client: APIClient,
    tenant_meta_namespace: str,
    policy_uuid: str,
    payload: UpdatePolicyPayload,
    update_mask: Optional[str] = None
) -> Optional[Policy]:
    """
    Update an existing policy.
    
    Args:
        client: APIClient instance
        tenant_meta_namespace: Tenant namespace (canonical name)
        policy_uuid: Policy UUID
        payload: Policy update payload
        update_mask: Optional update mask for partial updates
        
    Returns:
        Updated Policy object or None if update failed
    """
    try:
        headers = client.default_headers
        headers.update({
            "Accept": "application/json",
            "Content-Type": "application/json"
        })
        
        request_data = {
            "object": {
                "uuid": policy_uuid,
                "tenant_meta": {"namespace": tenant_meta_namespace},
                **payload.model_dump(exclude_unset=True)
            }
        }
        
        if update_mask:
            request_data["request"] = {"update_mask": update_mask}
        
        res = client.patch(
            f"v1/namespaces/{tenant_meta_namespace}/policies",
            headers=headers,
            data=request_data
        )
        data = res.json()
        return Policy(**data)
        
    except Exception as e:
        logger.error(f"Error updating policy {policy_uuid}: {e}", exc_info=True)
        return None


def delete_policy(
    client: APIClient,
    tenant_meta_namespace: str,
    policy_uuid: str
) -> bool:
    """
    Delete a policy.
    
    Args:
        client: APIClient instance
        tenant_meta_namespace: Tenant namespace (canonical name)
        policy_uuid: Policy UUID
        
    Returns:
        True if deletion successful, False otherwise
    """
    try:
        headers = client.default_headers
        res = client.delete(f"v1/namespaces/{tenant_meta_namespace}/policies/{policy_uuid}", headers=headers)
        return res.status_code == 200
        
    except Exception as e:
        logger.error(f"Error deleting policy {policy_uuid}: {e}", exc_info=True)
        return False
