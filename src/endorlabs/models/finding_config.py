"""Finding configuration models for policy specifications.

These models define the structure of finding configurations while
maintaining flexibility for API evolution.
"""

from pydantic import BaseModel, ConfigDict, Field


class FindingConfig(BaseModel):
    """Finding configuration with known fields.

    This model documents the known structure of finding configurations
    while allowing additional fields via extra="allow" for API evolution.
    """

    model_config = ConfigDict(
        extra="allow"  # Allow unknown fields for forward compatibility
    )

    level: str | None = Field(None, description="Finding severity level")
    tags: list[str] | None = Field(None, description="Finding tags")
    categories: list[str] | None = Field(None, description="Finding categories")
    summary: str | None = Field(None, description="Finding summary")
    explanation: str | None = Field(None, description="Finding explanation")
    remediation: str | None = Field(None, description="Finding remediation guidance")
    external_name: str | None = Field(None, description="External finding name")
    meta_tags: list[str] | None = Field(None, description="Metadata tags")
    target_kind: str | None = Field(None, description="Target resource kind")
