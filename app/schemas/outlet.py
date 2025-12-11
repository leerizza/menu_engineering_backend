from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from uuid import UUID


class OutletBase(BaseModel):
    name: str
    code: str
    type: str  # CENTRAL or OUTLET
    address: Optional[str] = None
    phone: Optional[str] = None


class OutletCreate(OutletBase):
    pass


class OutletUpdate(BaseModel):
    name: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    is_active: Optional[bool] = None


class OutletResponse(OutletBase):
    id: UUID
    organization_id: UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True