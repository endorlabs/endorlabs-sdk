"""
Finding configuration models for policy specifications.

These models define the structure of finding configurations while
maintaining flexibility for API evolution.
"""

from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class FindingConfig(BaseModel):
    """
    Finding configuration with known fields.

    This model documents the known structure of finding configurations
    while allowing additional fields via extra="allow" for API evolution.
    """

    model_config = ConfigDict(
        extra="allow"  # Allow unknown fields for forward compatibility
    )

    level: Optional[str] = Field(None, description="Finding severity level")
    tags: Optional[List[str]] = Field(None, description="Finding tags")
    categories: Optional[List[str]] = Field(None, description="Finding categories")
    summary: Optional[str] = Field(None, description="Finding summary")
    explanation: Optional[str] = Field(None, description="Finding explanation")
    remediation: Optional[str] = Field(None, description="Finding remediation guidance")
    external_name: Optional[str] = Field(None, description="External finding name")
    meta_tags: Optional[List[str]] = Field(None, description="Metadata tags")
    target_kind: Optional[str] = Field(None, description="Target resource kind")
