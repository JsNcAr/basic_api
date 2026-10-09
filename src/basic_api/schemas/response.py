"""
The success envelope every JSON endpoint returns.

Errors are not wrapped: they are FastAPI's default {"detail": ...} body, with a
string for an HTTPException and a list of validation errors for a 422.
"""

from pydantic import BaseModel, ConfigDict, Field


class SuccessResponse[T](BaseModel):
    """
    Generic success response wrapper.

    `T` is the type of `data`; `SuccessResponse[UserResponseSchema]` as a
    response_model names it in the OpenAPI document. PEP 695 syntax (3.12+): the
    type parameter is declared in the class header, with no TypeVar or Generic.
    """

    success: bool = Field(default=True, description="Always true")
    data: T = Field(..., description="Response data")
    message: str | None = Field(default=None, description="Optional message")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": True,
                "data": {
                    "id": "0199c7a0-5f3e-7cc4-9a7b-4f1e2d3c5b6a",
                    "username": "example",
                },
                "message": "Operation completed successfully",
            }
        }
    )
