from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from uuid import UUID


class IngredientBase(BaseModel):
    name: str
    category: Optional[str] = None
    sku: Optional[str] = None
    base_unit_id: UUID


class IngredientCreate(IngredientBase):
    pass


class IngredientUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    sku: Optional[str] = None
    base_unit_id: Optional[UUID] = None
    is_active: Optional[bool] = None


class IngredientResponse(IngredientBase):
    id: UUID
    organization_id: UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime
    base_unit_name: Optional[str] = None
    base_unit_symbol: Optional[str] = None
    
    class Config:
        from_attributes = True