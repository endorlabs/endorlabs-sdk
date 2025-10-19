"""
Tag management utilities for Endor Labs resources.

This module provides helper functions for managing tags on Projects and Findings
using the update_mask field to perform partial updates.
"""

import logging
from typing import List, Optional, Union
from .projects import Project, get_project, update_project
from .findings import Finding, get_finding, update_finding
from ..api_client import APIClient

logger = logging.getLogger(__name__)


def add_project_tag(
    client: APIClient, 
    namespace: str, 
    project_uuid: str, 
    tag: str
) -> Optional[Project]:
    """
    Add a tag to a project using update_mask for partial updates.
    
    Args:
        client: APIClient instance
        namespace: Canonical namespace name
        project_uuid: UUID of the project to update
        tag: Tag to add
        
    Returns:
        Updated Project object if successful, None otherwise
    """
    try:
        # Get current project
        project = get_project(client, namespace, project_uuid)
        if not project:
            logger.error(f"Project {project_uuid} not found")
            return None
        
        # Get current tags
        current_tags = getattr(project.meta, 'tags', []) or []
        
        # Add new tag if not already present
        if tag not in current_tags:
            new_tags = current_tags + [tag]
        else:
            logger.info(f"Tag {tag} already exists on project {project_uuid}")
            return project
        
        # Update using update_mask
        headers = client.default_headers
        headers.update({
            "Accept": "application/json", 
            "Content-Type": "application/json"
        })
        
        request_data = {
            "request": {
                "update_mask": "meta.tags"
            },
            "object": {
                "uuid": project_uuid,
                "tenant_meta": {"namespace": namespace},
                "meta": {
                    "name": project.meta.name,
                    "description": project.meta.description,
                    "tags": new_tags
                }
            }
        }
        
        res = client.patch(
            f"v1/namespaces/{namespace}/projects",
            headers=headers,
            data=request_data,
        )
        
        if res.status_code == 200:
            return Project(**res.json())
        else:
            logger.error(f"Failed to update project {project_uuid}: {res.status_code} - {res.text}")
            return None
            
    except Exception as e:
        logger.error(f"Error adding tag to project {project_uuid}: {e}", exc_info=True)
        return None


def remove_project_tag(
    client: APIClient, 
    namespace: str, 
    project_uuid: str, 
    tag: str
) -> Optional[Project]:
    """
    Remove a tag from a project using update_mask for partial updates.
    
    Args:
        client: APIClient instance
        namespace: Canonical namespace name
        project_uuid: UUID of the project to update
        tag: Tag to remove
        
    Returns:
        Updated Project object if successful, None otherwise
    """
    try:
        # Get current project
        project = get_project(client, namespace, project_uuid)
        if not project:
            logger.error(f"Project {project_uuid} not found")
            return None
        
        # Get current tags
        current_tags = getattr(project.meta, 'tags', []) or []
        
        # Remove tag if present
        if tag in current_tags:
            new_tags = [t for t in current_tags if t != tag]
        else:
            logger.info(f"Tag {tag} not found on project {project_uuid}")
            return project
        
        # Update using update_mask
        headers = client.default_headers
        headers.update({
            "Accept": "application/json", 
            "Content-Type": "application/json"
        })
        
        request_data = {
            "request": {
                "update_mask": "meta.tags"
            },
            "object": {
                "uuid": project_uuid,
                "tenant_meta": {"namespace": namespace},
                "meta": {
                    "name": project.meta.name,
                    "description": project.meta.description,
                    "tags": new_tags
                }
            }
        }
        
        res = client.patch(
            f"v1/namespaces/{namespace}/projects",
            headers=headers,
            data=request_data,
        )
        
        if res.status_code == 200:
            return Project(**res.json())
        else:
            logger.error(f"Failed to update project {project_uuid}: {res.status_code} - {res.text}")
            return None
            
    except Exception as e:
        logger.error(f"Error removing tag from project {project_uuid}: {e}", exc_info=True)
        return None


def add_finding_tag(
    client: APIClient, 
    namespace: str, 
    finding_uuid: str, 
    tag: str,
    tag_type: str = 'meta'
) -> Optional[Finding]:
    """
    Add a tag to a finding using update_mask for partial updates.
    
    Args:
        client: APIClient instance
        namespace: Canonical namespace name
        finding_uuid: UUID of the finding to update
        tag: Tag to add
        tag_type: Type of tag ('meta', 'spec', 'context')
        
    Returns:
        Updated Finding object if successful, None otherwise
    """
    try:
        # Get current finding
        finding = get_finding(client, namespace, finding_uuid)
        if not finding:
            logger.error(f"Finding {finding_uuid} not found")
            return None
        
        # Determine field path and current tags
        if tag_type == 'meta':
            field_path = "meta.tags"
            current_tags = getattr(finding.meta, 'tags', []) or []
        elif tag_type == 'spec':
            field_path = "spec.finding_tags"
            current_tags = getattr(finding.spec, 'finding_tags', []) or []
        elif tag_type == 'context':
            field_path = "context.tags"
            current_tags = getattr(finding.context, 'tags', []) or []
        else:
            logger.error(f"Invalid tag_type: {tag_type}. Must be 'meta', 'spec', or 'context'")
            return None
        
        # Add new tag if not already present
        if tag not in current_tags:
            new_tags = current_tags + [tag]
        else:
            logger.info(f"Tag {tag} already exists on finding {finding_uuid}")
            return finding
        
        # Update using update_mask
        headers = client.default_headers
        headers.update({
            "Accept": "application/json", 
            "Content-Type": "application/json"
        })
        
        # Build request data based on tag type
        request_data = {
            "request": {
                "update_mask": field_path
            },
            "object": {
                "uuid": finding_uuid,
                "tenant_meta": {"namespace": namespace}
            }
        }
        
        if tag_type == 'meta':
            request_data["object"]["meta"] = {
                "name": finding.meta.name,
                "description": finding.meta.description,
                "tags": new_tags
            }
        elif tag_type == 'spec':
            request_data["object"]["spec"] = {
                "project_uuid": finding.spec.project_uuid,
                "level": str(finding.spec.level.value) if hasattr(finding.spec.level, 'value') else str(finding.spec.level),
                "finding_tags": new_tags
            }
        elif tag_type == 'context':
            request_data["object"]["context"] = {
                "id": finding.context.id,
                "type": finding.context.type,
                "tags": new_tags
            }
        
        res = client.patch(
            f"v1/namespaces/{namespace}/findings",
            headers=headers,
            data=request_data,
        )
        
        if res.status_code == 200:
            return Finding(**res.json())
        else:
            logger.error(f"Failed to update finding {finding_uuid}: {res.status_code} - {res.text}")
            return None
            
    except Exception as e:
        logger.error(f"Error adding tag to finding {finding_uuid}: {e}", exc_info=True)
        return None


def remove_finding_tag(
    client: APIClient, 
    namespace: str, 
    finding_uuid: str, 
    tag: str,
    tag_type: str = 'meta'
) -> Optional[Finding]:
    """
    Remove a tag from a finding using update_mask for partial updates.
    
    Args:
        client: APIClient instance
        namespace: Canonical namespace name
        finding_uuid: UUID of the finding to update
        tag: Tag to remove
        tag_type: Type of tag ('meta', 'spec', 'context')
        
    Returns:
        Updated Finding object if successful, None otherwise
    """
    try:
        # Get current finding
        finding = get_finding(client, namespace, finding_uuid)
        if not finding:
            logger.error(f"Finding {finding_uuid} not found")
            return None
        
        # Determine field path and current tags
        if tag_type == 'meta':
            field_path = "meta.tags"
            current_tags = getattr(finding.meta, 'tags', []) or []
        elif tag_type == 'spec':
            field_path = "spec.finding_tags"
            current_tags = getattr(finding.spec, 'finding_tags', []) or []
        elif tag_type == 'context':
            field_path = "context.tags"
            current_tags = getattr(finding.context, 'tags', []) or []
        else:
            logger.error(f"Invalid tag_type: {tag_type}. Must be 'meta', 'spec', or 'context'")
            return None
        
        # Remove tag if present
        if tag in current_tags:
            new_tags = [t for t in current_tags if t != tag]
        else:
            logger.info(f"Tag {tag} not found on finding {finding_uuid}")
            return finding
        
        # Update using update_mask
        headers = client.default_headers
        headers.update({
            "Accept": "application/json", 
            "Content-Type": "application/json"
        })
        
        # Build request data based on tag type
        request_data = {
            "request": {
                "update_mask": field_path
            },
            "object": {
                "uuid": finding_uuid,
                "tenant_meta": {"namespace": namespace}
            }
        }
        
        if tag_type == 'meta':
            request_data["object"]["meta"] = {
                "name": finding.meta.name,
                "description": finding.meta.description,
                "tags": new_tags
            }
        elif tag_type == 'spec':
            request_data["object"]["spec"] = {
                "project_uuid": finding.spec.project_uuid,
                "level": str(finding.spec.level.value) if hasattr(finding.spec.level, 'value') else str(finding.spec.level),
                "finding_tags": new_tags
            }
        elif tag_type == 'context':
            request_data["object"]["context"] = {
                "id": finding.context.id,
                "type": finding.context.type,
                "tags": new_tags
            }
        
        res = client.patch(
            f"v1/namespaces/{namespace}/findings",
            headers=headers,
            data=request_data,
        )
        
        if res.status_code == 200:
            return Finding(**res.json())
        else:
            logger.error(f"Failed to update finding {finding_uuid}: {res.status_code} - {res.text}")
            return None
            
    except Exception as e:
        logger.error(f"Error removing tag from finding {finding_uuid}: {e}", exc_info=True)
        return None


def list_project_tags(
    client: APIClient, 
    namespace: str, 
    project_uuid: str
) -> List[str]:
    """
    List all tags for a project.
    
    Args:
        client: APIClient instance
        namespace: Canonical namespace name
        project_uuid: UUID of the project
        
    Returns:
        List of tags
    """
    try:
        project = get_project(client, namespace, project_uuid)
        if project:
            return getattr(project.meta, 'tags', []) or []
        return []
    except Exception as e:
        logger.error(f"Error listing tags for project {project_uuid}: {e}", exc_info=True)
        return []


def list_finding_tags(
    client: APIClient, 
    namespace: str, 
    finding_uuid: str,
    tag_type: str = 'all'
) -> Union[List[str], dict]:
    """
    List all tags for a finding.
    
    Args:
        client: APIClient instance
        namespace: Canonical namespace name
        finding_uuid: UUID of the finding
        tag_type: Type of tags to return ('all', 'meta', 'spec', 'context')
        
    Returns:
        List of tags or dict with all tag types
    """
    try:
        finding = get_finding(client, namespace, finding_uuid)
        if finding:
            if tag_type == 'all':
                return {
                    'meta': getattr(finding.meta, 'tags', []) or [],
                    'spec': getattr(finding.spec, 'finding_tags', []) or [],
                    'context': getattr(finding.context, 'tags', []) or []
                }
            elif tag_type == 'meta':
                return getattr(finding.meta, 'tags', []) or []
            elif tag_type == 'spec':
                return getattr(finding.spec, 'finding_tags', []) or []
            elif tag_type == 'context':
                return getattr(finding.context, 'tags', []) or []
            else:
                logger.error(f"Invalid tag_type: {tag_type}")
                return []
        return []
    except Exception as e:
        logger.error(f"Error listing tags for finding {finding_uuid}: {e}", exc_info=True)
        return []


def bulk_tag_projects(
    client: APIClient, 
    namespace: str, 
    project_uuids: List[str], 
    tag: str
) -> List[Optional[Project]]:
    """
    Add a tag to multiple projects.
    
    Args:
        client: APIClient instance
        namespace: Canonical namespace name
        project_uuids: List of project UUIDs
        tag: Tag to add
        
    Returns:
        List of updated Project objects (None for failed updates)
    """
    results = []
    for uuid in project_uuids:
        result = add_project_tag(client, namespace, uuid, tag)
        results.append(result)
    return results


def bulk_tag_findings(
    client: APIClient, 
    namespace: str, 
    finding_uuids: List[str], 
    tag: str,
    tag_type: str = 'meta'
) -> List[Optional[Finding]]:
    """
    Add a tag to multiple findings.
    
    Args:
        client: APIClient instance
        namespace: Canonical namespace name
        finding_uuids: List of finding UUIDs
        tag: Tag to add
        tag_type: Type of tag ('meta', 'spec', 'context')
        
    Returns:
        List of updated Finding objects (None for failed updates)
    """
    results = []
    for uuid in finding_uuids:
        result = add_finding_tag(client, namespace, uuid, tag, tag_type)
        results.append(result)
    return results
