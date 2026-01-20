"""
Exception configuration models for policy specifications.

These models define the structure of exception configurations while
maintaining flexibility for API evolution.
"""

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class ExceptionConfig(BaseModel):
    """
    Exception configuration with known fields.

    This model documents the known structure of exception configurations
    while allowing additional fields via extra="allow" for API evolution.
    """

    model_config = ConfigDict(
        extra="allow"  # Allow unknown fields for forward compatibility
    )

    reason: Optional[str] = Field(
        None, description="Exception reason (e.g., 'EXCEPTION_REASON_FALSE_POSITIVE')"
    )
