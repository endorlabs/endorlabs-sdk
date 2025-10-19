"""
This module provides a resource-oriented interface for managing Endor Labs
findings. It implements CRUD operations following REST principles and
provides type-safe data models.
"""

import logging
import os
import sys
from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from ..api_client import APIClient, RedactingFilter, redaction_pattern

# Set up logger with redaction filter
logger = logging.getLogger(__name__)
logger.addFilter(RedactingFilter([redaction_pattern]))


# Enums for Finding types
class FindingType(str, Enum):
    """Types of security findings."""
    SCA = "SCA"  # Software Composition Analysis
    SAST = "SAST"  # Static Application Security Testing
    SECRET = "SECRET"  # Secrets detection
    COMPLIANCE = "COMPLIANCE"  # Compliance findings


class Severity(str, Enum):
    """Severity levels for findings."""
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class Status(str, Enum):
    """Status of findings."""
    OPEN = "OPEN"
    RESOLVED = "RESOLVED"
    IGNORED = "IGNORED"
    FALSE_POSITIVE = "FALSE_POSITIVE"


# Pydantic Models for Finding data with OpenAPI validation
class FindingDetails(BaseModel):
    """
    Detailed information about a finding.

    Attributes:
        title: The title of the finding
        description: Detailed description of the finding
        file_path: File where the finding was found
        line_number: Line number in the file
        code_snippet: Relevant code snippet
        remediation: Remediation guidance
    """

    title: str = Field(..., description="The title of the finding")
    description: str = Field("", description="Detailed description of the finding")
    file_path: str = Field("", description="File where the finding was found")
    line_number: Optional[int] = Field(None, description="Line number in the file")
    code_snippet: str = Field("", description="Relevant code snippet")
    remediation: str = Field("", description="Remediation guidance")


class FindingMeta(BaseModel):
    """
    Metadata for an Endor Labs finding.

    Attributes:
        type: The type of finding (SCA, SAST, SECRET, COMPLIANCE)
        severity: The severity level of the finding
        status: The current status of the finding
        details: Detailed information about the finding
        created_at: Timestamp when the finding was created
        updated_at: Timestamp when the finding was last updated
    """

    type: FindingType = Field(..., description="The type of finding")
    severity: Severity = Field(..., description="The severity level of the finding")
    status: Status = Field(..., description="The current status of the finding")
    details: FindingDetails = Field(..., description="Detailed information about the finding")
    created_at: Optional[datetime] = Field(
        None, description="Timestamp when the finding was created"
    )
    updated_at: Optional[datetime] = Field(
        None, description="Timestamp when the finding was last updated"
    )


class FindingMetaUpdate(BaseModel):
    """
    Metadata for updating an Endor Labs finding.
    """

    status: Optional[Status] = Field(
        None, description="Updated status of the finding"
    )
    details: Optional[FindingDetails] = Field(
        None, description="Updated details of the finding"
    )


class UpdateFindingPayload(BaseModel):
    """
    Payload for updating an Endor Labs finding.
    """

    meta: FindingMetaUpdate = Field(
        ..., description="Updated metadata for the finding"
    )
    comment: Optional[str] = Field(
        None, description="Comment explaining the update"
    )


class Finding(BaseModel):
    """
    An Endor Labs finding entity.

    Attributes:
        uuid: Unique identifier for the finding
        meta: Metadata associated with the finding
        project_uuid: UUID of the parent project
        namespace_uuid: UUID of the parent namespace
    """

    uuid: str = Field(..., description="Unique identifier for the finding")
    meta: FindingMeta = Field(
        ..., description="Metadata associated with the finding"
    )
    project_uuid: str = Field(
        ..., description="UUID of the parent project"
    )
    namespace_uuid: str = Field(
        ..., description="UUID of the parent namespace"
    )

    @field_validator("uuid")
    @classmethod
    def validate_uuid(cls, v: str) -> str:
        """Validate that the UUID is not empty or just whitespace."""
        if not v.strip():
            raise ValueError("uuid cannot be empty")
        return v


def list_findings(
    client: APIClient, 
    namespace_uuid: str,
    project_uuid: Optional[str] = None,
    severity: Optional[Severity] = None,
    status: Optional[Status] = None,
    finding_type: Optional[FindingType] = None
) -> List[Finding]:
    """
    List findings with optional filters.

    Args:
        client: The APIClient instance to use for the request
        namespace_uuid: The namespace UUID to list findings from
        project_uuid: Optional project UUID to filter findings
        severity: Optional severity level to filter findings
        status: Optional status to filter findings
        finding_type: Optional finding type to filter findings

    Returns:
        List[Finding]: A list of Finding objects. Empty list if error occurs.

    Raises:
        requests.exceptions.HTTPError: For API-level errors
        pydantic.ValidationError: If response data doesn't match expected schema
    """
    try:
        headers = client.default_headers
        
        # Build query parameters
        params = {}
        if project_uuid:
            params['project_uuid'] = project_uuid
        if severity:
            params['severity'] = severity.value
        if status:
            params['status'] = status.value
        if finding_type:
            params['type'] = finding_type.value
        
        res = client.get(
            f"v1/namespaces/{namespace_uuid}/findings", 
            headers=headers,
            params=params
        )
        data = res.json().get("findings", [])
        return [Finding(**item) for item in data]
    except Exception as e:
        logger.error(f"Error listing findings: {e}", exc_info=True)
        return []


def get_finding(client: APIClient, namespace_uuid: str, finding_uuid: str) -> Optional[Finding]:
    """
    Retrieve a specific finding by UUID.

    Args:
        client: The APIClient instance to use for the request
        namespace_uuid: The namespace UUID containing the finding
        finding_uuid: The UUID of the finding to retrieve

    Returns:
        Optional[Finding]: The requested Finding object, or None if not found

    Raises:
        requests.exceptions.HTTPError: For API-level errors
        pydantic.ValidationError: If response data doesn't match expected schema
    """
    try:
        headers = client.default_headers
        res = client.get(
            f"v1/namespaces/{namespace_uuid}/findings/{finding_uuid}",
            headers=headers,
        )
        data = res.json()
        return Finding(**data)
    except Exception as e:
        logger.error(f"Error retrieving finding {finding_uuid}: {e}", exc_info=True)
        return None


def update_finding_status(
    client: APIClient, 
    namespace_uuid: str,
    finding_uuid: str, 
    status: Status,
    comment: Optional[str] = None
) -> Optional[Finding]:
    """
    Update finding status.

    Args:
        client: The APIClient instance to use for the request
        namespace_uuid: The namespace UUID containing the finding
        finding_uuid: The UUID of the finding to update
        status: The new status for the finding
        comment: Optional comment explaining the status change

    Returns:
        Optional[Finding]: The updated Finding object, or None if update fails

    Raises:
        requests.exceptions.HTTPError: For API-level errors
        pydantic.ValidationError: If response data doesn't match expected schema
    """
    try:
        headers = client.default_headers
        headers.update(
            {"Accept": "application/json", "Content-Type": "application/json"}
        )
        
        payload = {
            "meta": {
                "status": status.value
            }
        }
        if comment:
            payload["comment"] = comment
        
        res = client.patch(
            f"v1/namespaces/{namespace_uuid}/findings/{finding_uuid}",
            headers=headers,
            data=payload,
        )
        data = res.json()
        return Finding(**data)
    except Exception as e:
        logger.error(f"Error updating finding {finding_uuid}: {e}", exc_info=True)
        return None


def bulk_update_findings(
    client: APIClient, 
    namespace_uuid: str,
    finding_uuids: List[str], 
    status: Status,
    comment: Optional[str] = None
) -> List[Finding]:
    """
    Bulk update multiple findings.

    Args:
        client: The APIClient instance to use for the request
        namespace_uuid: The namespace UUID containing the findings
        finding_uuids: List of finding UUIDs to update
        status: The new status for the findings
        comment: Optional comment explaining the status change

    Returns:
        List[Finding]: List of updated Finding objects

    Raises:
        requests.exceptions.HTTPError: For API-level errors
        pydantic.ValidationError: If response data doesn't match expected schema
    """
    updated_findings = []
    
    for finding_uuid in finding_uuids:
        try:
            updated_finding = update_finding_status(
                client, namespace_uuid, finding_uuid, status, comment
            )
            if updated_finding:
                updated_findings.append(updated_finding)
        except Exception as e:
            logger.error(f"Error updating finding {finding_uuid}: {e}", exc_info=True)
    
    return updated_findings


def search_findings_by_severity(
    client: APIClient, 
    namespace_uuid: str, 
    severity: Severity
) -> List[Finding]:
    """
    Search findings by severity level.

    Args:
        client: The APIClient instance to use for the request
        namespace_uuid: The namespace UUID to search in
        severity: The severity level to search for

    Returns:
        List[Finding]: List of findings with the specified severity
    """
    return list_findings(client, namespace_uuid, severity=severity)


def search_findings_by_status(
    client: APIClient, 
    namespace_uuid: str, 
    status: Status
) -> List[Finding]:
    """
    Search findings by status.

    Args:
        client: The APIClient instance to use for the request
        namespace_uuid: The namespace UUID to search in
        status: The status to search for

    Returns:
        List[Finding]: List of findings with the specified status
    """
    return list_findings(client, namespace_uuid, status=status)


def search_findings_by_type(
    client: APIClient, 
    namespace_uuid: str, 
    finding_type: FindingType
) -> List[Finding]:
    """
    Search findings by type.

    Args:
        client: The APIClient instance to use for the request
        namespace_uuid: The namespace UUID to search in
        finding_type: The finding type to search for

    Returns:
        List[Finding]: List of findings with the specified type
    """
    return list_findings(client, namespace_uuid, finding_type=finding_type)


if __name__ == "__main__":
    # Example usage
    client = APIClient()
    namespace_uuid = os.getenv("ENDOR_NAMESPACE", "endor-solutions-tgowan.cockpit")

    # List findings
    print("Listing findings...")
    findings = list_findings(client, namespace_uuid)
    print(f"Found {len(findings)} findings")
    
    for finding in findings[:3]:  # Show first 3
        print(f"  - {finding.meta.details.title} ({finding.meta.severity.value})")
    
    # Search by severity
    print("\nSearching for HIGH severity findings...")
    high_findings = search_findings_by_severity(client, namespace_uuid, Severity.HIGH)
    print(f"Found {len(high_findings)} HIGH severity findings")
    
    # Search by status
    print("\nSearching for OPEN status findings...")
    open_findings = search_findings_by_status(client, namespace_uuid, Status.OPEN)
    print(f"Found {len(open_findings)} OPEN status findings")
