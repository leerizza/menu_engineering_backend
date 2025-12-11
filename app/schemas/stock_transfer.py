from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from uuid import UUID
from decimal import Decimal


class StockTransferItemBase(BaseModel):
    ingredient_id: UUID
    qty: Decimal
    unit_id: UUID
    unit_cost: Optional[Decimal] = None


class StockTransferItemCreate(StockTransferItemBase):
    pass


class StockTransferItemResponse(StockTransferItemBase):
    id: UUID
    stock_transfer_id: UUID
    total_cost: Optional[Decimal]
    ingredient_name: Optional[str]
    unit_symbol: Optional[str]
    
    class Config:
        from_attributes = True


class StockTransferBase(BaseModel):
    from_outlet_id: UUID
    to_outlet_id: UUID
    stock_request_id: Optional[UUID] = None
    notes: Optional[str] = None


class StockTransferCreate(StockTransferBase):
    items: List[StockTransferItemCreate]


class StockTransferResponse(StockTransferBase):
    id: UUID
    organization_id: UUID
    transfer_no: str
    status: str
    shipped_at: Optional[datetime]
    received_at: Optional[datetime]
    created_by: UUID
    received_by: Optional[UUID]
    created_at: datetime
    
    # Additional fields
    from_outlet_name: Optional[str]
    to_outlet_name: Optional[str]
    created_by_name: Optional[str]
    items: List[StockTransferItemResponse] = []
    
    class Config:
        from_attributes = True