"""
The success envelope every JSON endpoint returns.

Errors are not wrapped: they are FastAPI's default {"detail": ...} body, with a
string for an HTTPException and a list of validation errors for a 422.
"""

from typing import Generic, Optional, TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class SuccessResponse(BaseModel, Generic[T]):
    """Generic success response wrapper."""

    success: bool = Field(default=True, description="Always true")
    data: T = Field(..., description="Response data")
    message: Optional[str] = Field(default=None, description="Optional message")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": True,
                "data": {"id": 123, "username": "example"},
                "message": "Operation completed successfully",
            }
        }
    )
