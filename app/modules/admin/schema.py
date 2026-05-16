"""
Admin module schemas.
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class AppConfigResponse(BaseModel):
    """Single config entry."""
    id: int
    key: str
    value: str
    description: Optional[str] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class AppConfigUpdateRequest(BaseModel):
    """Update a config value."""
    value: str = Field(..., description="New value for this config")

    model_config = {"json_schema_extra": {
        "example": {"value": "15"}
    }}


class AppConfigListResponse(BaseModel):
    """List of all configs."""
    items: List[AppConfigResponse] = []
