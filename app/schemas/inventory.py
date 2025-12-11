from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from uuid import UUID
from decimal import Decimal


class InventoryStockResponse(BaseModel):
    id: UUID
    outlet_id: UUID
    ingredient_id: UUID
    qty_on_hand: Decimal
    min_qty: Decimal
    unit_id: UUID
    last_cost: Optional[Decimal]
    updated_at: datetime
    
    # Additional fields from joins
    outlet_name: Optional[str]
    ingredient_name: Optional[str]
    unit_symbol: Optional[str]
    is_low_stock: Optional[bool] = False
    
    class Config:
        from_attributes = True


class InventoryLedgerResponse(BaseModel):
    id: UUID
    outlet_id: UUID
    ingredient_id: UUID
    change_qty: Decimal
    source_type: str
    source_id: Optional[UUID]
    unit_id: UUID
    unit_cost: Optional[Decimal]
    total_cost: Optional[Decimal]
    remarks: Optional[str]
    created_at: datetime
    
    # Additional fields
    outlet_name: Optional[str]
    ingredient_name: Optional[str]
    unit_symbol: Optional[str]
    
    class Config:
        from_attributes = True


class InventoryAdjustmentCreate(BaseModel):
    ingredient_id: UUID
    outlet_id: UUID
    adjustment_qty: Decimal
    unit_id: UUID
    remarks: str