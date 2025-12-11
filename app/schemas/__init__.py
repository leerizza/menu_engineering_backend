from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from uuid import UUID


class BaseSchema(BaseModel):
    """Base schema with common fields"""
    class Config:
        from_attributes = True


class SuccessResponse(BaseModel):
    """Standard success response"""
    success: bool = True
    message: str
    data: Optional[dict] = None


class ErrorResponse(BaseModel):
    """Standard error response"""
    success: bool = False
    message: str
    detail: Optional[str] = None