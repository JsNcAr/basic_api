"""
Common Pydantic schemas for pagination, filters, and API responses.
"""

from typing import Optional, Generic, TypeVar, Any
from pydantic import BaseModel, Field, ConfigDict

# Generic type for response data
T = TypeVar("T")


class SuccessResponse(BaseModel, Generic[T]):
    """Generic success response wrapper."""

    success: bool = Field(default=True, description="Success status")
    data: T = Field(..., description="Response data")
    message: Optional[str] = Field(default=None, description="Optional message")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": True,
                "data": {"id": "123", "name": "Example"},
                "message": "Operation completed successfully",
            }
        }
    )


class ErrorResponse(BaseModel):
    """Error response schema."""

    success: bool = Field(default=False, description="Success status (always false)")
    error: str = Field(..., description="Error message")
    detail: Optional[str] = Field(
        default=None, description="Detailed error information"
    )
    code: Optional[str] = Field(default=None, description="Error code")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": False,
                "error": "Resource not found",
                "detail": "Lead with people_id 'abc123' does not exist",
                "code": "NOT_FOUND",
            }
        }
    )
