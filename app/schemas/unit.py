from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from uuid import UUID


class UnitResponse(BaseModel):
    id: UUID
    name: str
    symbol: str
    is_base_unit: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


class UnitConversionResponse(BaseModel):
    id: UUID
    ingredient_id: Optional[UUID]
    from_unit_id: UUID
    to_unit_id: UUID
    multiplier: float
    from_unit_symbol: Optional[str]
    to_unit_symbol: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True