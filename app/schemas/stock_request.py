from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from uuid import UUID
from decimal import Decimal


class StockRequestItemBase(BaseModel):
    ingredient_id: UUID
    requested_qty: Decimal
    requested_unit_id: UUID
    notes: Optional[str] = None


class StockRequestItemCreate(StockRequestItemBase):
    pass


class StockRequestItemResponse(StockRequestItemBase):
    id: UUID
    stock_request_id: UUID
    approved_qty: Decimal
    ingredient_name: Optional[str]
    unit_symbol: Optional[str]
    
    class Config:
        from_attributes = True


class StockRequestBase(BaseModel):
    from_outlet_id: UUID
    to_outlet_id: UUID
    notes: Optional[str] = None


class StockRequestCreate(StockRequestBase):
    items: List[StockRequestItemCreate]


class StockRequestUpdate(BaseModel):
    notes: Optional[str] = None


class StockRequestResponse(StockRequestBase):
    id: UUID
    organization_id: UUID
    request_no: str
    status: str
    requested_by: UUID
    approved_by: Optional[UUID]
    approved_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    
    # Additional fields
    from_outlet_name: Optional[str]
    to_outlet_name: Optional[str]
    requested_by_name: Optional[str]
    approved_by_name: Optional[str]
    items: List[StockRequestItemResponse] = []
    
    class Config:
        from_attributes = True


class ApproveStockRequestItem(BaseModel):
    item_id: UUID
    approved_qty: Decimal


class ApproveStockRequest(BaseModel):
    items: List[ApproveStockRequestItem]